import httpx
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
js = httpx.get("https://flk.npc.gov.cn/assets/index-UYjjaqh-.js", headers=headers, timeout=30).text
for kw in ["/api/", "api/detail", "searchType", "wb.flk", "download"]:
    idx = js.find(kw)
    while idx != -1:
        print("---", kw, idx, "---")
        print(js[max(0, idx - 80): idx + 120])
        idx = js.find(kw, idx + 1)
        if idx > 0 and js.find(kw, idx) - idx > 50000:
            break
