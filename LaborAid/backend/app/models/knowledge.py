from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    __table_args__ = (
        Index("ix_knowledge_items_owner_id", "owner_id"),
        # Composite: team-based visibility queries
        Index("ix_knowledge_items_team_id", "team_id"),
        # Composite: duplicate detection by owner + title
        Index("ix_knowledge_items_owner_title", "owner_id", "title"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[str | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_platform: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:
        return f"<KnowledgeItem id={self.id} title={self.title!r}>"
