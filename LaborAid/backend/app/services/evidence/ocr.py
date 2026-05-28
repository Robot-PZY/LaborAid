"""证据OCR文字提取服务"""

import asyncio
import logging
from pathlib import Path

from app.services.evidence.pdf_vision import (
    SCANNED_PDF_MARKER,
    ocr_image_bytes,
    ocr_pdf_with_vision,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md",
    ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff",
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma",
}

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}


def validate_file_type(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


async def extract_text(
    file_path: Path,
    llm_client=None,
    model: str | None = None,
    vision_llm: "ResolvedLLM | None" = None,
) -> str:
    """从文件中提取文字内容。"""
    from app.config import get_settings
    if model is None:
        model = get_settings().LLM_MODEL
    if not file_path.exists():
        return "[文件不存在]"
    if file_path.stat().st_size == 0:
        return "[文件为空]"
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            text = await _extract_pdf(file_path)
            if text.strip() == SCANNED_PDF_MARKER:
                return await ocr_pdf_with_vision(file_path, vision_llm)
            return text
        elif suffix == ".docx":
            return await _extract_docx(file_path)
        elif suffix == ".doc":
            return await _extract_doc(file_path)
        elif suffix in (".xlsx", ".xls"):
            return await _extract_excel(file_path)
        elif suffix in (".txt", ".md"):
            return file_path.read_text(encoding="utf-8", errors="ignore")
        elif suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"):
            client = vision_llm.client if vision_llm else llm_client
            ocr_model = vision_llm.model if vision_llm else model
            suffix_l = file_path.suffix.lower()
            media_type = "image/png"
            if suffix_l in (".jpg", ".jpeg"):
                media_type = "image/jpeg"
            elif suffix_l == ".bmp":
                media_type = "image/bmp"
            elif suffix_l == ".tiff":
                media_type = "image/tiff"
            return await ocr_image_bytes(
                file_path.read_bytes(),
                client,
                ocr_model,
                media_type=media_type,
            )
        elif suffix in AUDIO_EXTENSIONS:
            return await _extract_audio(file_path, llm_client, model)
        return ""
    except Exception as e:
        logger.warning(f"OCR extraction failed for {file_path}: {e}")
        return f"[文字提取失败: {e}]"


async def _extract_pdf(file_path: Path) -> str:
    def _sync():
        import pypdf
        reader = pypdf.PdfReader(str(file_path))
        texts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texts.append(t.strip())
        return "\n\n".join(texts) if texts else SCANNED_PDF_MARKER
    return await asyncio.to_thread(_sync)


async def _extract_docx(file_path: Path) -> str:
    def _sync():
        from docx import Document
        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return await asyncio.to_thread(_sync)


async def _extract_doc(file_path: Path) -> str:
    """提取 .doc 文件文字（尝试用 python-docx 兼容读取，若失败则提示）。"""
    try:
        return await _extract_docx(file_path)
    except Exception:
        return "[.doc 格式暂不支持直接解析，请转换为 .docx 后上传]"


async def _extract_excel(file_path: Path) -> str:
    """提取 Excel 文件文字内容。"""
    def _sync():
        import openpyxl
        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        texts = []
        for sheet in wb.worksheets:
            texts.append(f"=== {sheet.title} ===")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    texts.append("\t".join(cells))
        wb.close()
        return "\n".join(texts)
    return await asyncio.to_thread(_sync)


async def _extract_image(file_path: Path, llm_client, model: str) -> str:
    """Deprecated wrapper — use ocr_image_bytes via extract_text."""
    suffix = file_path.suffix.lower()
    media_type = "image/png"
    if suffix in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif suffix == ".bmp":
        media_type = "image/bmp"
    elif suffix == ".tiff":
        media_type = "image/tiff"
    return await ocr_image_bytes(
        file_path.read_bytes(),
        llm_client,
        model,
        media_type=media_type,
    )


async def _extract_audio(file_path: Path, llm_client=None, model: str = "glm-5.1") -> str:
    """从音频文件中提取文字 — 优先使用Whisper，回退使用LLM。"""
    # 方案1: 尝试使用OpenAI Whisper API
    try:
        import openai
        from app.config import get_settings
        settings = get_settings()
        if settings.LLM_API_KEY and settings.LLM_BASE_URL:
            client = openai.AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )
            with open(str(file_path), "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh",
                    response_format="text",
                )
            return transcript if isinstance(transcript, str) else transcript.text
    except Exception as e:
        logger.info(f"Whisper API not available, falling back to LLM: {e}")

    # 方案2: 使用LLM处理（将音频文件大小信息告知LLM，提示用户手动转写）
    def _get_size():
        return file_path.stat().st_size / (1024 * 1024)
    file_size_mb = await asyncio.to_thread(_get_size)
    suffix = file_path.suffix.lower()
    return (
        f"[音频文件: {suffix}格式, {file_size_mb:.1f}MB]\n"
        f"提示：当前LLM不支持直接处理音频。请使用以下方式之一：\n"
        f"1. 配置支持Whisper API的LLM服务（如OpenAI）以启用自动语音转文字\n"
        f"2. 手动将音频转为文字后粘贴到文本框中\n"
        f"3. 使用第三方语音转文字工具处理后上传文本文件"
    )
