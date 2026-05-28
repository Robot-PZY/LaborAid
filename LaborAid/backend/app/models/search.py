from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class SearchRecord(Base):
    __tablename__ = "search_records"
    __table_args__ = (
        Index("ix_search_records_user_id", "user_id"),
        Index("ix_search_records_case_id", "case_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)

    query: Mapped[str] = mapped_column(String(2000), nullable=False)
    result_type: Mapped[str] = mapped_column(String(20), default="all")
    # law / case / all
    results: Mapped[str | None] = mapped_column(JSON, nullable=True)
    sources_used: Mapped[str | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:
        return f"<SearchRecord id={self.id} query={self.query[:50]!r}>"
