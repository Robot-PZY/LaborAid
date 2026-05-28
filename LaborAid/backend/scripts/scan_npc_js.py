import httpx
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
html = httpx.get("https://flk.npc.gov.cn/fl.html", headers=headers, timeout=30).text
scripts = re.findall(r'src="(/assets/[^"]+\.js)"', html)
print("scripts:", scripts)
for s in scripts:
    js = httpx.get("https://flk.npc.gov.cn" + s, headers=headers, timeout=30).text
    for pat in ["api", "search", "detail", "flfg", "wb.flk"]:
        if pat in js:
            print(s, "contains", pat)
    urls = re.findall(r"https?://[a-zA-Z0-9./_-]+", js)
    api_urls = [u for u in urls if "api" in u or "flk" in u or "npc" in u]
    print(s, "urls sample:", sorted(set(api_urls))[:15])
