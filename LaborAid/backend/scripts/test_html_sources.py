"""Test gov.cn / mohrss HTML policy pages."""
import httpx
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

URLS = [
    "https://www.mohrss.gov.cn/wap/wzgg/202312/t20231229_456789.html",
    "https://www.gov.cn/zhengce/content/2024-12/content_6991234.htm",
    "https://www.gov.cn/zhengce/zhengceku/2024-12/31/content_6991234.htm",
]

# Try mohrss search
try:
    r = httpx.get(
        "https://www.mohrss.gov.cn/was5/web/search",
        params={"channelid": "203989", "searchword": "劳动合同"},
        headers=headers,
        timeout=20,
        follow_redirects=True,
    )
    print("mohrss search", r.status_code, len(r.text))
except Exception as e:
    print("mohrss search err", e)

for url in URLS:
    try:
        r = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        print(url, r.status_code, len(r.text))
    except Exception as e:
        print(url, e)
