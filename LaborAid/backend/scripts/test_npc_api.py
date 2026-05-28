"""Quick probe for NPC law database API."""
import httpx
import time
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://flk.npc.gov.cn/fl.html",
}

params = {
    "type": "flfg",
    "searchType": "title;vague",
    "sortTr": "f_bbrq_s;desc",
    "gbrqStart": "",
    "gbrqEnd": "",
    "sxrqStart": "",
    "sxrqEnd": "",
    "sort": "true",
    "page": "1",
    "size": "5",
    "_": str(int(time.time() * 1000)),
    "searchParam": "劳动法",
}

with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as c:
    for url in [
        "https://flk.npc.gov.cn/api/",
        "https://flk.npc.gov.cn/api",
        "https://flk.npc.gov.cn/api/search",
    ]:
        r = c.get(url, params=params)
        ct = r.headers.get("content-type", "")
        print(url, r.status_code, ct, len(r.content))
        if "json" in ct:
            print(json.dumps(r.json(), ensure_ascii=False)[:800])
            break
        if r.text.strip().startswith("{"):
            print(r.text[:800])
            break

    js = c.get("https://flk.npc.gov.cn/assets/index-UYjjaqh-.js")
    apis = set(re.findall(r'["\'](/api[^"\']*)["\']', js.text))
    print("api paths in bundle:", sorted(apis)[:20])
