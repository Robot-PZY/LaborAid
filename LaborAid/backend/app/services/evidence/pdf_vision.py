"""PDF / image vision OCR helpers (百炼 qwen-vl-ocr 等)."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.llm_resolver import ResolvedLLM

logger = logging.getLogger(__name__)

SCANNED_PDF_MARKER = "[PDF为扫描件，需要OCR识别]"

OCR_PROMPT = (
    "请识别并提取文档图片中的所有文字内容，按原文格式输出。"
    "若内容为劳动维权证据（工资条、聊天截图、通知、合同扫描件等），请保持原文不变。"
)

MAX_PDF_OCR_PAGES = 10


async def ocr_image_bytes(
    image_bytes: bytes,
    client,
    model: str,
    *,
    media_type: str = "image/jpeg",
    prompt: str = OCR_PROMPT,
) -> str:
    if client is None:
        return "[图片文字识别不可用：请在管理端「模型配置」添加通义千问 OCR 等视觉模型并填写 API Key]"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.content[0].text if response.content else "[未能识别文字]"
    except Exception as e:
        logger.warning("Vision OCR failed: %s", e)
        return f"[图片文字提取失败: {e}]"


async def _render_pdf_pages_pymupdf(file_path: Path, max_pages: int) -> list[bytes]:
    def _sync() -> list[bytes]:
        import fitz  # pymupdf

        doc = fitz.open(str(file_path))
        images: list[bytes] = []
        try:
            for idx, page in enumerate(doc):
                if idx >= max_pages:
                    break
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(pix.tobytes("jpeg"))
        finally:
            doc.close()
        return images

    return await asyncio.to_thread(_sync)


async def _extract_embedded_pdf_images(file_path: Path, max_pages: int) -> list[bytes]:
    """Fallback: pull embedded JPEG/PNG objects from PDF pages."""
    def _sync() -> list[bytes]:
        import pypdf
        from PIL import Image

        reader = pypdf.PdfReader(str(file_path))
        images: list[bytes] = []
        for page_num, page in enumerate(reader.pages):
            if page_num >= max_pages:
                break
            if not hasattr(page, "images"):
                continue
            for img in page.images:
                try:
                    pil_img = Image.open(io.BytesIO(img.data))
                    if pil_img.mode == "RGBA":
                        pil_img = pil_img.convert("RGB")
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=85)
                    images.append(buf.getvalue())
                except Exception:
                    continue
        return images

    return await asyncio.to_thread(_sync)


async def ocr_pdf_with_vision(
    file_path: Path,
    vision_llm: ResolvedLLM | None,
    *,
    max_pages: int = MAX_PDF_OCR_PAGES,
) -> str:
    """OCR scanned PDF by rendering pages (or embedded images) through vision model."""
    if vision_llm is None or vision_llm.client is None:
        return "[PDF文字识别不可用：请在管理端「模型配置」添加通义千问 OCR 等视觉模型并填写 API Key]"

    client = vision_llm.client
    model = vision_llm.model

    page_images: list[bytes] = []
    try:
        page_images = await _render_pdf_pages_pymupdf(file_path, max_pages)
    except Exception as e:
        logger.debug("PyMuPDF render failed, trying embedded images: %s", e)

    if not page_images:
        page_images = await _extract_embedded_pdf_images(file_path, max_pages)

    if not page_images:
        return "[PDF扫描件未能渲染为图片，请尝试上传 JPG/PNG 或可选文字版 PDF]"

    parts: list[str] = []
    for idx, img in enumerate(page_images):
        text = await ocr_image_bytes(
            img,
            client,
            model,
            prompt=f"{OCR_PROMPT}\n（第 {idx + 1} 页，共 {len(page_images)} 页）",
        )
        if text and not text.startswith("["):
            parts.append(text)
        elif text and "提取失败" not in text:
            parts.append(text)

    if not parts:
        return "[PDF扫描件OCR未识别到有效文字]"
    return "\n\n".join(parts)
