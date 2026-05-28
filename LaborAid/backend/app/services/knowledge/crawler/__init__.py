"""官方法规爬虫 — 从全国人大法律法规库同步至平台知识库。"""

from app.services.knowledge.crawler.service import LawCrawlService

__all__ = ["LawCrawlService"]
