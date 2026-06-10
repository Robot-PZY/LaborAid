"""自由 Markdown 文书的后处理：补标题层级、规范列表与落款。"""

from __future__ import annotations

import re

from app.services.docgen.prompts import DOC_TYPE_NAMES
from app.services.docgen.legal_citation_normalize import normalize_markdown_citations

# doc_type -> [(pattern, replacement_section_header), ...]
_SECTION_ALIASES: dict[str, list[tuple[str, str]]] = {
    "application": [
        (r"^仲裁请求[：:]\s*$", "## 仲裁请求"),
        (r"^事实与理由[：:]\s*$", "## 事实与理由"),
        (r"^申请人[：:]\s*$", "## 申请人"),
        (r"^被申请人[：:]\s*$", "## 被申请人"),
        (r"^证据[目录]*[：:]\s*$", "## 证据目录"),
    ],
    "complaint": [
        (r"^诉讼请求[：:]\s*$", "## 诉讼请求"),
        (r"^事实与理由[：:]\s*$", "## 事实与理由"),
        (r"^原告[：:]\s*$", "## 原告"),
        (r"^被告[：:]\s*$", "## 被告"),
    ],
}


def normalize_freeform_markdown(content: str, doc_type: str) -> str:
    if not content or not content.strip():
        return content

    lines = content.split("\n")
    out: list[str] = []
    aliases = _SECTION_ALIASES.get(doc_type, [])
    title = DOC_TYPE_NAMES.get(doc_type, "")

    for line in lines:
        stripped = line.strip()
        replaced = False
        for pat, header in aliases:
            if re.match(pat, stripped, re.IGNORECASE):
                out.append(header)
                replaced = True
                break
        if not replaced:
            # 行内「仲裁请求：」→ 拆成标题+正文
            m = re.match(r"^(仲裁请求|诉讼请求|事实与理由|申请人|被申请人)[：:]\s*(.+)$", stripped)
            if m and not stripped.startswith("#"):
                out.append(f"## {m.group(1)}")
                out.append("")
                out.append(m.group(2))
            else:
                out.append(line)

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if title and not re.search(r"^#\s+", text, re.MULTILINE):
        text = f"# {title}\n\n{text}"

    # 确保仲裁类有「此致」
    if doc_type == "application" and "此致" not in text:
        text = text.rstrip() + "\n\n## 落款\n\n此致\n××劳动人事争议仲裁委员会\n\n申请人：[签名]\n"

    # 法条引用规范化：统一法律名称、条文号格式
    text = normalize_markdown_citations(text)

    return text.strip() + "\n"
