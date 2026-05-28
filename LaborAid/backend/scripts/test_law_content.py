import httpx
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}
base = "https://flk.npc.gov.cn"
bbbs = "2c909fdd678bf17901678bf74d7106b3"  # Labor Contract Law

with httpx.Client(headers=headers, timeout=60) as c:
    # hitDisplay might return article text
    for path, method, payload in [
        ("/law-search/search/hitDisplay", "post", {"bbbs": bbbs, "searchContent": ""}),
        ("/law-search/highSearch/hitDisplay", "post", {"bbbs": bbbs}),
        ("/law-search/amazonFile/previewLink", "get", {"bbbs": bbbs}),
        ("/law-search/download/pc", "get", {"bbbs": bbbs, "format": "pdf"}),
    ]:
        if method == "post":
            r = c.post(base + path, json=payload)
        else:
            r = c.get(base + path, params=payload)
        print(path, r.status_code, r.text[:400])

    # Try download with different params from JS
    r = c.get(base + "/law-search/download/pc", params={"bbbs": bbbs, "format": "docx"})
    print("download docx", r.status_code, r.text[:300])

    # Search JS for previewLink usage
    js = c.get(base + "/assets/index-UYjjaqh-.js").text
    idx = js.find("previewLink")
    print("previewLink ctx:", js[idx:idx+300])
