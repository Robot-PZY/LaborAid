import re
import threading
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
settings = get_settings()

# Maximum input lengths to prevent abuse
MAX_TEXT_INPUT_LENGTH = 50000
MAX_TITLE_LENGTH = 200
MAX_QUERY_LENGTH = 2000

# ---------------------------------------------------------------------------
# In-memory rate limiter (simple sliding-window per key)
# ---------------------------------------------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_MAX_KEYS = 10000
_rate_limit_last_cleanup = time.monotonic()
_RATE_LIMIT_CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes


def _cleanup_rate_limit_store() -> None:
    """Remove stale keys and expired entries to prevent unbounded memory growth."""
    global _rate_limit_last_cleanup
    now = time.monotonic()
    if now - _rate_limit_last_cleanup < _RATE_LIMIT_CLEANUP_INTERVAL:
        return
    _rate_limit_last_cleanup = now
    stale_keys = []
    for key, timestamps in _rate_limit_store.items():
        # Remove entries older than the longest standard window (3600s)
        cutoff = now - 3600
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if not timestamps:
            stale_keys.append(key)
    for key in stale_keys:
        del _rate_limit_store[key]
    if stale_keys:
        logger.debug("Rate limit cleanup: removed %d stale keys", len(stale_keys))


def check_rate_limit(key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """Return True if the request is within rate limits, False if exceeded.

    Uses a simple in-memory sliding-window counter. Suitable for single-process
    deployments; for multi-process production, replace with Redis.
    """
    with _rate_limit_lock:
        _cleanup_rate_limit_store()
        now = time.monotonic()
        cutoff = now - window_seconds
        timestamps = _rate_limit_store[key]
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if len(_rate_limit_store) > _RATE_LIMIT_MAX_KEYS:
            return False
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        return True


def check_rate_limit_with_headers(
    key: str, max_requests: int = 60, window_seconds: int = 60
) -> tuple[bool, dict[str, str]]:
    """Check rate limit and return response headers.

    Returns (is_allowed, headers_dict) where headers include:
    - X-RateLimit-Remaining: remaining requests in the window
    - Retry-After: seconds until the window resets (only when rate limited)
    """
    with _rate_limit_lock:
        _cleanup_rate_limit_store()
        now = time.monotonic()
        cutoff = now - window_seconds
        timestamps = _rate_limit_store[key]

        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        remaining = max(0, max_requests - len(timestamps))
        headers = {
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Limit": str(max_requests),
        }

        if len(_rate_limit_store) > _RATE_LIMIT_MAX_KEYS or len(timestamps) >= max_requests:
            oldest = timestamps[0] if timestamps else now
            retry_after = max(1, int(oldest + window_seconds - now) + 1)
            headers["Retry-After"] = str(retry_after)
            headers["X-RateLimit-Remaining"] = "0"
            return False, headers

        timestamps.append(now)
        headers["X-RateLimit-Remaining"] = str(remaining - 1)
        return True, headers


# ---------------------------------------------------------------------------
# Password strength validation
# ---------------------------------------------------------------------------
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets minimum strength requirements.

    Returns (is_valid, error_message). Minimum requirements:
    - At least 8 characters
    - Contains at least one letter and one digit
    """
    if len(password) < 8:
        return False, "密码长度不能少于8位"
    if not re.search(r'[A-Za-z]', password):
        return False, "密码必须包含至少一个字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    return True, ""


# ---------------------------------------------------------------------------
# Text / path helpers
# ---------------------------------------------------------------------------
def sanitize_text(text: str | None, max_length: int = MAX_TEXT_INPUT_LENGTH) -> str:
    """Sanitize user text input: strip whitespace, limit length."""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text


def validate_file_path(path: str) -> bool:
    """Validate file path doesn't contain path traversal attacks."""
    if not path:
        return False
    # Block path traversal patterns
    if ".." in path or "~" in path:
        return False
    # Block absolute paths that escape expected dirs
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized.split("/")[0]:
        return False
    return True


# ---------------------------------------------------------------------------
# Password hashing (bcrypt with automatic salt)
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash password using bcrypt with auto-generated salt (cost factor 12)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def is_token_expired(token: str) -> bool:
    """Check whether a JWT token has expired without raising.

    Returns True if expired or invalid, False if still valid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        exp = payload.get("exp")
        if exp is None:
            return True
        return datetime.now(timezone.utc).timestamp() > exp
    except JWTError:
        return True


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Explicit expiration check for clarity
        exp = payload.get("exp")
        if exp is not None and datetime.now(timezone.utc).timestamp() > exp:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )
    return user


# ---------------------------------------------------------------------------
# File upload security helpers
# ---------------------------------------------------------------------------

# Strict extension-to-MIME mapping for upload allowlisting
ALLOWED_MIME_MAP: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    ".doc": {"application/msword"},
    ".txt": {"text/plain"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    ".xls": {"application/vnd.ms-excel"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
    ".bmp": {"image/bmp", "image/x-ms-bmp"},
    ".tiff": {"image/tiff"},
    ".mp3": {"audio/mpeg"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".ogg": {"audio/ogg"},
    ".flac": {"audio/flac"},
    ".aac": {"audio/aac"},
    ".wma": {"audio/x-ms-wma"},
}

# Characters dangerous in filenames
_UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Patterns that may indicate injection in text content
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on(?:error|load|click|mouseover)\s*=", re.IGNORECASE),
    re.compile(r"<\s*(?:iframe|object|embed|form|input|svg)\b", re.IGNORECASE),
]


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitize a user-supplied filename.

    - Remove path components (no directory traversal)
    - Replace unsafe characters with underscore
    - Limit total length
    """
    # Strip directory components
    name = Path(filename).name
    # Remove unsafe characters
    name = _UNSAFE_FILENAME_RE.sub("_", name)
    # Collapse consecutive underscores/spaces
    name = re.sub(r"[_\s]+", "_", name).strip("_ ")
    # Truncate but preserve extension
    if len(name) > max_length:
        stem = Path(name).stem[: max_length - 10]
        ext = Path(name).suffix
        name = f"{stem}{ext}"
    return name or "upload"


def validate_file_extension(filename: str, allowed_extensions: set[str] | None = None) -> str:
    """Validate file extension against a strict allowlist.

    Returns the normalized lowercase extension (with dot) on success.
    Raises HTTPException 400 on failure.
    """
    ext = Path(filename).suffix.lower()
    if not ext:
        raise HTTPException(400, "文件缺少扩展名")
    allowed = allowed_extensions or set(ALLOWED_MIME_MAP.keys())
    if ext not in allowed:
        raise HTTPException(
            400,
            f"不支持的文件扩展名 '{ext}'，允许: {', '.join(sorted(allowed))}",
        )
    return ext


def validate_mime_type(filename: str, content_type: str | None) -> None:
    """Verify the declared MIME type matches the file extension.

    Accepts ``None`` content_type (FastAPI may not always provide it).
    Raises HTTPException 400 on mismatch.
    """
    if not content_type:
        return
    ext = Path(filename).suffix.lower()
    expected = ALLOWED_MIME_MAP.get(ext)
    if expected is None:
        return  # extension not in our map, skip MIME check
    # Normalize content_type (strip parameters like charset)
    ct_normalized = content_type.split(";")[0].strip().lower()
    if ct_normalized not in expected:
        raise HTTPException(
            400,
            f"文件类型不匹配: 扩展名 '{ext}' 对应 MIME {expected}，但收到 '{ct_normalized}'",
        )


async def validate_upload(
    file: UploadFile,
    max_size_mb: int | None = None,
    allowed_extensions: set[str] | None = None,
    scan_content: bool = True,
) -> bytes:
    """Full upload validation pipeline.

    1. Validate extension against allowlist
    2. Validate MIME type matches extension
    3. Read content and enforce size limit
    4. Optionally scan text content for injection patterns

    Returns the raw file bytes on success.
    """
    fname = file.filename or ""
    settings = get_settings()
    max_bytes = (max_size_mb or settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024

    # 1. Extension allowlist
    validate_file_extension(fname, allowed_extensions)

    # 2. MIME type validation
    validate_mime_type(fname, file.content_type)

    # 3. Size enforcement
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            400,
            f"文件大小超过{(max_bytes // 1024 // 1024)}MB限制",
        )

    # 4. Injection scan for text-based files
    if scan_content and content:
        _scan_content_for_injections(fname, content)

    return content


def _scan_content_for_injections(filename: str, content: bytes) -> None:
    """Check uploaded content for common injection patterns in text files."""
    ext = Path(filename).suffix.lower()
    # Only scan text-based files
    if ext not in {".txt", ".html", ".htm", ".md", ".csv", ".json", ".xml"}:
        return
    try:
        text = content.decode("utf-8", errors="ignore")[:100_000]
    except Exception as e:
        logger.warning("Failed to decode content for injection scan '%s': %s", filename, e)
        return
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Injection pattern detected in upload '%s': %s",
                filename, pattern.pattern,
            )
            raise HTTPException(
                400,
                "文件内容包含不安全的内容，请检查后重新上传",
            )


def require_admin(user: User) -> None:
    """Raise 403 if the user is not an admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: authenticated admin only."""
    require_admin(current_user)
    return current_user
