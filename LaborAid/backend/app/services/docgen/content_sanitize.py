"""生成文书正文清洗 — 去除对话式前言、统一 Markdown 结构入口。"""

from __future__ import annotations

import re

# 对话式/助手式开场（整段或行首）
_PREAMBLE_LINE_PATTERNS = [
    r"^好的[，,。.!！\s]",
    r"^您好[，,。.!！\s]",
    r"^你好[，,。.!！\s]",
    r"^我是\s*(劳权智助|LaborAid|AI|人工智能)",
    r"很高兴为您服务",
    r"根据您提供的信息",
    r"我已为您(梳理|草拟|撰写|生成)",
    r"请注意[，,]",
    r"此文书为?您",
    r"以下(为|是)文书正文",
    r"供您参考",
    r"在正式提交前",
    r"建议您携带",
    r"咨询.*(法律援助|律师)",
    r"不构成正式法律意见",
    r"仅供参考",
]

_PREAMBLE_BLOCK_RE = re.compile(
    r"^(?:"
    + "|".join(_PREAMBLE_LINE_PATTERNS)
    + r").*$",
    re.MULTILINE | re.IGNORECASE,
)

# 常见正式文书起始锚点
_FORMAL_START_RE = re.compile(
    r"^(\#\s+|##\s+|申请人|被申请人|投诉人|被投诉人|答辩人|上诉人|被上诉人|"
    r"原告|被告|致[：:]|此致|劳动仲裁申请书|民事起诉状|劳动监察)",
    re.MULTILINE | re.IGNORECASE,
)


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:markdown|md)?\s*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t)
    return t.strip()


def _find_formal_start(text: str) -> int:
    match = _FORMAL_START_RE.search(text)
    return match.start() if match else -1


def sanitize_legal_document_content(content: str, doc_type_name: str = "") -> str:
    """
    清洗 LLM 输出：删除 AI 对话前言，保留 Markdown 正式正文。
    若缺少一级标题，在文首补文书类型标题。
    """
    if not content or not content.strip():
        return content

    text = _strip_code_fences(content)

    # 删除明确的前言段落（连续匹配行）
    lines = text.split("\n")
    cleaned: list[str] = []
    formal_started = False
    for line in lines:
        stripped = line.strip()
        if not formal_started:
            if not stripped:
                continue
            if _PREAMBLE_BLOCK_RE.match(stripped):
                continue
            if _find_formal_start(stripped) >= 0 or stripped.startswith("#"):
                formal_started = True
                cleaned.append(line)
            elif re.match(r"^[\-\*]\s", stripped):
                # 列表可能在正式内容前，若已有标题则保留
                if cleaned:
                    cleaned.append(line)
            else:
                # 非前言模式：可能是无标题直接写「申请人」
                if re.match(r"^(申请人|被申请人|投诉人|答辩人)", stripped):
                    formal_started = True
                    cleaned.append(line)
                elif len(cleaned) == 0 and len(stripped) > 80:
                    # 长段叙述性开场，跳过
                    if any(k in stripped for k in ("劳权智助", "LaborAid", "为您服务", "草拟")):
                        continue
                    formal_started = True
                    cleaned.append(line)
                elif len(cleaned) > 0:
                    cleaned.append(line)
        else:
            cleaned.append(line)

    text = "\n".join(cleaned).strip()

    # 若正文从中间才开始，截断前言
    start = _find_formal_start(text)
    if start > 0:
        text = text[start:].lstrip()

    # 再次按行清理残留前言
    text = _PREAMBLE_BLOCK_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # 过滤 LLM 生成的"分页符"标记文字（不应出现在正文中）
    text = re.sub(r"^[—\-]+\s*分页符\s*[—\-]+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*分页符\s*$", "", text, flags=re.MULTILINE)

    # 确保有居中标题（Word 导出与预览用 #）
    if doc_type_name and not re.search(r"^#\s+", text, re.MULTILINE):
        if not text.startswith(f"# {doc_type_name}"):
            text = f"# {doc_type_name}\n\n{text}"

    return text
