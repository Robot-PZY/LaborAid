import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}

base = "https://flk.npc.gov.cn"

with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as c:
    # Try search list
    payloads = [
        {"searchContent": "劳动合同法", "searchRange": 1, "searchType": 2, "pageNum": 1, "pageSize": 5},
        {"searchContent": "劳动合同法", "page": 1, "size": 5},
    ]
    for path in ["/law-search/search/list", "/law-search/search/xgzl", "/law-search/prompts/search"]:
        for payload in payloads[:1]:
            r = c.post(base + path, json=payload)
            print(path, r.status_code, r.headers.get("content-type"))
            if r.status_code == 200 and r.text.strip().startswith("{"):
                data = r.json()
                print(json.dumps(data, ensure_ascii=False)[:1500])
                break
            else:
                print("  ", r.text[:200])
