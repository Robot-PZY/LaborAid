"""Quick connectivity test for text LLM (DeepSeek) and vision OCR (Qwen/DashScope)."""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.llm_client import create_llm_client
from app.services.evidence.pdf_vision import ocr_image_bytes


def _make_test_image_bytes() -> bytes:
    """Generate a small PNG with Chinese text for OCR smoke test."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise SystemExit("Pillow not installed; pip install Pillow")

    img = Image.new("RGB", (480, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text = "LaborAid OCR测试：试用期解除通知"
    # Default font works on Windows for basic Chinese in many setups
    try:
        font = ImageFont.truetype("msyh.ttc", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 40), text, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def test_text_llm(settings) -> dict:
    key = (settings.LLM_API_KEY or "").strip()
    if not key:
        return {"ok": False, "error": "LLM_API_KEY 未配置"}
    client = create_llm_client(settings.LLM_BASE_URL, key)
    model = settings.LLM_MODEL
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=64,
                messages=[{"role": "user", "content": "只回复两个字：成功"}],
            ),
            timeout=45,
        )
        text = resp.content[0].text if resp.content else ""
        return {"ok": True, "model": model, "base_url": settings.LLM_BASE_URL, "reply": text.strip()[:80]}
    except Exception as e:
        return {"ok": False, "model": model, "base_url": settings.LLM_BASE_URL, "error": str(e)[:300]}


async def test_vision_ocr(settings) -> dict:
    key = (settings.VISION_LLM_API_KEY or "").strip()
    if not key:
        return {"ok": False, "error": "VISION_LLM_API_KEY 未配置"}
    client = create_llm_client(settings.VISION_LLM_BASE_URL, key)
    model = settings.VISION_LLM_MODEL
    img = _make_test_image_bytes()
    try:
        text = await asyncio.wait_for(
            ocr_image_bytes(img, client, model, media_type="image/png"),
            timeout=60,
        )
        failed = text.startswith("[") and ("失败" in text or "不可用" in text)
        return {
            "ok": not failed,
            "model": model,
            "base_url": settings.VISION_LLM_BASE_URL,
            "ocr_preview": text.strip()[:200],
            "error": text if failed else None,
        }
    except Exception as e:
        return {"ok": False, "model": model, "base_url": settings.VISION_LLM_BASE_URL, "error": str(e)[:300]}


async def main() -> None:
    settings = get_settings()
    print("=== LaborAid 模型连通性测试 ===\n")

    print("[1/2] 文本 LLM（文书/解读/对话）")
    text = await test_text_llm(settings)
    if text.get("ok"):
        print(f"  OK  model={text['model']}")
        print(f"      url={text['base_url']}")
        print(f"      reply={text['reply']!r}")
    else:
        print(f"  FAIL model={text.get('model', '?')}")
        print(f"       {text.get('error')}")

    print("\n[2/2] 视觉 OCR（证据图片/扫描 PDF）")
    vision = await test_vision_ocr(settings)
    if vision.get("ok"):
        print(f"  OK  model={vision['model']}")
        print(f"      url={vision['base_url']}")
        print(f"      ocr={vision['ocr_preview']!r}")
    else:
        print(f"  FAIL model={vision.get('model', '?')}")
        print(f"       {vision.get('error') or vision.get('ocr_preview')}")

    print("\n=== 完成 ===")
    if not text.get("ok") and not vision.get("ok"):
        sys.exit(2)
    if not text.get("ok") or not vision.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
