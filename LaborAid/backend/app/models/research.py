"""法律研究报告模型"""

from datetime import datetime, timezone
from sqlalchemy import Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ResearchReport(Base):
    __tablename__ = "research_reports"
    __table_args__ = (
        Index("ix_research_reports_owner_id", "owner_id"),
        # Composite: list research by owner + case
        Index("ix_research_reports_owner_case", "owner_id", "case_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    report: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[str] = mapped_column(JSON, nullable=False, default=list)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner = relationship("User", backref="research_reports")
