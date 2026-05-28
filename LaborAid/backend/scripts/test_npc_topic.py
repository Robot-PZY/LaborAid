"""Test NPC topic search for labor-related laws."""
import httpx
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Content-Type": "application/json",
}
r = httpx.post(
    "https://flk.npc.gov.cn/law-search/search/list",
    json={"searchContent": "劳动", "searchRange": 1, "searchType": 2, "pageNum": 1, "pageSize": 10},
    headers=headers,
    timeout=30,
)
data = r.json()
for row in data.get("rows", []):
    title = re.sub(r"<[^>]+>", "", row.get("title", ""))
    print(title, row.get("bbbs"), row.get("flxz"))
