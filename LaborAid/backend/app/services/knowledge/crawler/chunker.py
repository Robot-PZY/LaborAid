"""法规正文按「条」拆分，便于知识库检索与向量化。"""

from __future__ import annotations

import re

_ARTICLE_HEAD = re.compile(
    r"(?:^|\n)(第[一二三四五六七八九十百千万零〇\d]+条[^\n]*)",
    re.MULTILINE,
)


def split_law_articles(text: str, law_name: str, *, max_chars: int = 8000) -> list[tuple[str, str]]:
    """将法规正文拆分为 (标题, 内容) 列表。优先按「第X条」切分。"""
    text = re.sub(r"\r\n?", "\n", text.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)

    matches = list(_ARTICLE_HEAD.finditer(text))
    if len(matches) >= 2:
        chunks: list[tuple[str, str]] = []
        preamble = text[: matches[0].start()].strip()
        if preamble and len(preamble) > 80:
            chunks.append((f"{law_name}（序言）", preamble))

        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if not body:
                continue
            article_label = match.group(1).split("\n", 1)[0].strip()
            article_num = re.match(r"第[^条]+条", article_label)
            short = article_num.group(0) if article_num else article_label[:20]
            title = f"{law_name} {short}"
            if len(title) > 190:
                title = title[:190]
            chunks.append((title, body))
        return _merge_oversized(chunks, max_chars)

    return _split_paragraphs(text, law_name, max_chars)


def _merge_oversized(chunks: list[tuple[str, str]], max_chars: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for title, content in chunks:
        if len(content) <= max_chars:
            out.append((title, content))
            continue
        parts = _split_paragraphs(content, title, max_chars)
        out.extend(parts)
    return out


def _split_paragraphs(text: str, title_prefix: str, max_chars: int) -> list[tuple[str, str]]:
    if len(text) <= max_chars:
        return [(title_prefix, text)]
    paragraphs = text.split("\n\n")
    chunks: list[tuple[str, str]] = []
    current = ""
    part = 1
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) > max_chars and current:
            chunks.append((f"{title_prefix} (第{part}部分)", current.strip()))
            current = para
            part += 1
        else:
            current = candidate
    if current.strip():
        suffix = f" (第{part}部分)" if part > 1 else ""
        chunks.append((f"{title_prefix}{suffix}", current.strip()))
    return chunks if chunks else [(title_prefix, text[:max_chars])]
