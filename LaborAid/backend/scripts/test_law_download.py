import httpx
import asyncio
from pathlib import Path
import tempfile

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Content-Type": "application/json",
}
base = "https://flk.npc.gov.cn"
bbbs = "2c909fdd678bf17901678bf74d7106b3"

with httpx.Client(headers=headers, timeout=120) as c:
    r = c.get(base + "/law-search/download/pc", params={"bbbs": bbbs, "format": "docx"})
    url = r.json()["data"]["url"]
    print("url", url[:120])
    doc = c.get(url)
    print("download", doc.status_code, len(doc.content))
    tmp = Path(tempfile.gettempdir()) / "test_law.docx"
    tmp.write_bytes(doc.content)

async def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.evidence.ocr import extract_text
    text = await extract_text(tmp)
    print("text len", len(text))
    print(text[:500])

asyncio.run(main())
