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

with httpx.Client(headers=headers, follow_redirects=True, timeout=60) as c:
    r = c.post(base + "/law-search/search/list", json={
        "searchContent": "中华人民共和国劳动合同法",
        "searchRange": 1,
        "searchType": 1,
        "pageNum": 1,
        "pageSize": 5,
    })
    data = r.json()
    print("total", data.get("total"), "rows", len(data.get("rows", [])))
    if not data.get("rows"):
        raise SystemExit("no rows")
    row = data["rows"][0]
    bbbs = row["bbbs"]
    title = re.sub(r"<[^>]+>", "", row["title"])
    print("pick", title, bbbs)

    for params in [{"bbbs": bbbs}, {"id": bbbs}]:
        r2 = c.get(base + "/law-search/search/flfgDetails", params=params)
        print("flfgDetails", params, r2.status_code)
        if r2.status_code == 200:
            d = r2.json()
            print(json.dumps(d, ensure_ascii=False)[:2000])

    r3 = c.get(base + "/law-search/download/pc", params={"bbbs": bbbs})
    print("download/pc", r3.status_code, r3.headers.get("content-type"), len(r3.content))
