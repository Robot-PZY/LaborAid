"""Probe gov.cn and NPC sources for law crawling."""
import httpx
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# Known gov.cn labor law pages (public policy library)
TEST_URLS = [
    "https://www.gov.cn/gongbao/content/2008/content_1104.htm",  # Labor Contract Law
    "https://www.gov.cn/gongbao/content/1995/content_1000.htm",  # Labor Law (try)
    "https://www.gov.cn/zhengce/zhengceku/2021-01/5980/content_5592680.htm",
]

with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as c:
  for url in TEST_URLS:
    try:
      r = c.get(url)
      print(url, "->", r.status_code, len(r.text))
      if r.status_code == 200:
        title = re.search(r"<title>([^<]+)</title>", r.text)
        print("  title:", title.group(1)[:80] if title else "?")
        # gov.cn content div
        m = re.search(r'class="pages_content"[^>]*>(.*?)</motionless>', r.text, re.S)
        if not m:
          m = re.search(r'class="pages_content"[^>]*>(.*?)</div>', r.text, re.S)
        if m:
          text = re.sub(r"<[^>]+>", "", m.group(1))
          text = re.sub(r"\s+", " ", text).strip()
          print("  content preview:", text[:200])
    except Exception as e:
      print(url, "ERR", e)

  # Try wb.flk subdomain
  for base in ["https://wb.flk.npc.gov.cn", "https://flk.npc.gov.cn"]:
    try:
      r = c.get(f"{base}/")
      print(base, r.status_code, r.headers.get("content-type"))
    except Exception as e:
      print(base, "ERR", e)
