"""Shared LLM client factory -- supports Anthropic and OpenAI protocols.

Includes retry with exponential backoff, rate-limit / token-limit handling,
request timing, and malformed-response resilience.
"""

import asyncio
import json
import logging
import time

import anthropic
import openai

logger = logging.getLogger(__name__)

# Retry constants
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds
_BACKOFF_MAX = 30.0  # seconds


def _is_openai_compatible(base_url: str) -> bool:
    """Return True when *base_url* should use the OpenAI-compatible SDK."""
    url = base_url.lower().rstrip("/")
    if "anthropic.com" in url or "/api/anthropic" in url:
        return False
    return True


def create_llm_client(base_url: str, api_key: str):
    """Auto-select Anthropic or OpenAI client based on *base_url*."""
    if not base_url or _is_openai_compatible(base_url):
        return OpenAICompatClient(base_url, api_key)
    return anthropic.AsyncAnthropic(
        base_url=base_url,
        api_key=api_key,
        timeout=120.0,
        max_retries=2,
    )


def create_llm_client_from_settings(settings):
    """Create a client from a Settings object."""
    return create_llm_client(settings.LLM_BASE_URL, settings.LLM_API_KEY)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _classify_error(exc: Exception) -> str | None:
    """Return a tag describing the error category, or None for unknown."""
    msg = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )

    # Rate limit
    if status == 429 or "rate" in msg or "429" in msg:
        return "rate_limit"

    # Token limit / context window
    if (
        "token" in msg and ("limit" in msg or "exceed" in msg)
    ) or "context_length_exceeded" in msg or "max_tokens" in msg:
        return "token_limit"

    # Timeout (read / connect)
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in msg:
        return "timeout"

    # Connection error
    if "connection" in msg or "connect" in msg:
        return "connection"

    return None


async def _retry_with_backoff(coro_factory, *, max_retries=_MAX_RETRIES):
    """Execute *coro_factory* with exponential backoff on retryable errors.

    *coro_factory* must be a callable returning an awaitable.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            category = _classify_error(exc)

            # Non-retryable errors — fail immediately
            if category in ("token_limit",):
                logger.warning("Non-retryable LLM error (%s): %s", category, exc)
                raise

            if category == "rate_limit":
                # Respect Retry-After if available
                retry_after = getattr(exc, "headers", {}).get("retry-after", None)
                if retry_after:
                    wait = min(float(retry_after), _BACKOFF_MAX)
                else:
                    wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)
            elif category in ("timeout", "connection"):
                wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)
            else:
                wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)

            if attempt < max_retries:
                logger.warning(
                    "LLM request failed (%s), retrying in %.1fs (attempt %d/%d): %s",
                    category or "unknown",
                    wait,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "LLM request failed after %d retries (%s): %s",
                    max_retries,
                    category or "unknown",
                    exc,
                )
                raise
    # Should not reach here, but just in case
    raise last_exc  # type: ignore[misc]


# ── OpenAI-compatible client ────────────────────────────────────────────────

class OpenAICompatClient:
    """Wraps the OpenAI SDK to provide a ``messages.create`` interface
    consistent with the Anthropic SDK, with retry and timing built in.
    """

    def __init__(self, base_url: str, api_key: str):
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=120.0,
            max_retries=2,
        )
        self.messages = _MessagesShim(self._client)


class _MessagesShim:
    def __init__(self, client: openai.AsyncOpenAI):
        self._client = client

    async def create(
        self, model: str, max_tokens: int, messages: list[dict], **kwargs
    ) -> "_MessageResponse":
        start = time.monotonic()
        request_id = f"{model}-{int(start * 1000)}"

        logger.debug("LLM request start: id=%s model=%s", request_id, model)

        # Extract system message
        system = kwargs.get("system") or kwargs.get("system_message")
        chat_msgs: list[dict] = []
        for m in messages:
            if m.get("role") == "system":
                system = m["content"]
            else:
                chat_msgs.append(m)

        # Format multimodal content
        formatted = []
        for m in chat_msgs:
            content = m.get("content", "")
            if isinstance(content, list):
                parts: list[dict] = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append({"type": "text", "text": block["text"]})
                    elif block.get("type") == "image":
                        img = block.get("image", block.get("source", {}))
                        url = img.get("url")
                        if not url:
                            b64 = img.get("data")
                            mt = img.get("media_type", "image/png")
                            url = f"data:{mt};base64,{b64}"
                        parts.append({"type": "image_url", "image_url": {"url": url}})
                formatted.append({"role": m["role"], "content": parts})
            else:
                formatted.append({"role": m["role"], "content": content})

        call_kwargs: dict = {
            "model": model,
            "messages": formatted,
            "max_tokens": max_tokens,
        }
        if system:
            call_kwargs["messages"] = [
                {"role": "system", "content": system}
            ] + call_kwargs["messages"]

        # ── Execute with retry + backoff ─────────────────────────────────
        async def _do_call():
            try:
                resp = await self._client.chat.completions.create(**call_kwargs)
            except openai.RateLimitError as exc:
                # Map to a plain exception with a recognisable message
                raise RuntimeError(f"rate_limit: {exc}") from exc
            except openai.APITimeoutError as exc:
                raise TimeoutError(f"LLM request timed out: {exc}") from exc
            except openai.APIConnectionError as exc:
                raise ConnectionError(f"LLM connection failed: {exc}") from exc
            except openai.BadRequestError as exc:
                msg = str(exc).lower()
                if "token" in msg or "context" in msg or "max" in msg:
                    raise RuntimeError(f"token_limit: {exc}") from exc
                raise

            # ── Parse response with malformed-JSON protection ────────────
            try:
                text = resp.choices[0].message.content or ""
            except (AttributeError, IndexError, TypeError) as exc:
                logger.error("Malformed LLM response: %s  resp=%s", exc, resp)
                text = ""

            return _MessageResponse(text)

        try:
            result = await _retry_with_backoff(_do_call)
        except Exception:
            elapsed = time.monotonic() - start
            logger.error(
                "LLM request failed: id=%s elapsed=%.2fs", request_id, elapsed
            )
            raise

        elapsed = time.monotonic() - start
        logger.debug(
            "LLM request done: id=%s elapsed=%.2fs response_len=%d",
            request_id,
            elapsed,
            len(result.content[0].text) if result.content else 0,
        )
        return result


class _MessageResponse:
    def __init__(self, text: str):
        self.content = [_ContentBlock(text)]


class _ContentBlock:
    def __init__(self, text: str):
        self.text = text
