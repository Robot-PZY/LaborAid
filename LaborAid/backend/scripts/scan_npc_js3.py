import httpx
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
js = httpx.get("https://flk.npc.gov.cn/assets/index-UYjjaqh-.js", headers=headers, timeout=30).text
paths = sorted(set(re.findall(r'url:"(/law-search/[^"]+)"', js)))
print("law-search paths:")
for p in paths:
    print(" ", p)

# Also find $r base URL
for m in re.finditer(r'baseURL[^,]{0,80}', js):
    print("base:", m.group(0)[:100])
