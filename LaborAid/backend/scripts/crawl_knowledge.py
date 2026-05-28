"""CLI: 同步官方法规到知识库

用法:
  python scripts/crawl_knowledge.py --dry-run --keyword "中华人民共和国劳动法"
  python scripts/crawl_knowledge.py --all
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.knowledge.crawler import LawCrawlService
from sqlalchemy import select


async def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl official laws into knowledge base")
    parser.add_argument("--all", action="store_true", help="Sync all labor seeds")
    parser.add_argument("--seed", action="append", dest="seeds", help="Seed id (repeatable)")
    parser.add_argument("--keyword", action="append", dest="keywords", help="Custom keyword")
    parser.add_argument("--discover", action="store_true", help="Include topic discovery")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        admin = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
        if not admin:
            print("No admin user found")
            sys.exit(1)

        svc = LawCrawlService()
        seed_ids = None
        if args.seeds:
            seed_ids = args.seeds
        elif args.all:
            seed_ids = [s.id for s in svc.load_seeds()]

        result = await svc.run(
            db,
            admin,
            seed_ids=seed_ids,
            keywords=args.keywords,
            include_statutes=True,
            include_topic_discovery=args.discover or args.all,
            dry_run=args.dry_run,
        )
        for item in result.items:
            print(f"[{item.status}] {item.title}: {item.message}")
        print(f"Done: success={result.success} failed={result.failed}")


if __name__ == "__main__":
    asyncio.run(main())
