"""Check existing documents and test export."""
from app.core.database import AsyncSessionLocal
from app.models.document import Document
from sqlalchemy import select


def check():
    with AsyncSessionLocal() as session:
        result = session.execute(select(Document).order_by(Document.id.desc()).limit(3))
        docs = result.scalars().all()
        for d in docs:
            print(f"ID={d.id} title={d.title} type={d.type} status={d.status} content_len={len(d.content or '')} exported_path={d.exported_path}")


check()
