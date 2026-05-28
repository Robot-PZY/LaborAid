"""Probe NPC with SSL verify disabled (dev only)."""
import httpx
import time
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Accept": "application/json, text/plain, */*",
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
    "size": "3",
    "_": str(int(time.time() * 1000)),
    "searchParam": "劳动法",
}

with httpx.Client(headers=headers, follow_redirects=True, timeout=30, verify=False) as c:
    for host in ["https://flk.npc.gov.cn", "https://wb.flk.npc.gov.cn"]:
        url = f"{host}/api/"
        r = c.get(url, params=params)
        ct = r.headers.get("content-type", "")
        print(host, r.status_code, ct)
        if "json" in ct or r.text.strip().startswith("{"):
            data = r.json()
            print(json.dumps(data, ensure_ascii=False)[:1200])
            items = data.get("result", {}).get("data", [])
            if items:
                id_ = items[0]["id"]
                title = items[0]["title"]
                print("detail for", title)
                r2 = c.post(f"{host}/api/detail", data={"id": id_})
                print("detail status", r2.status_code, r2.headers.get("content-type"))
                if r2.status_code == 200 and "json" in r2.headers.get("content-type", ""):
                    d = r2.json()
                    body = d.get("result", {}).get("body", [])
                    print(json.dumps(body[:1], ensure_ascii=False)[:500])
            break
        else:
            print("  body:", r.text[:120])
