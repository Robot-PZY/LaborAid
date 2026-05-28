from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_owner_id", "owner_id"),
        Index("ix_contracts_case_id", "case_id"),
        Index("ix_contracts_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    clauses: Mapped[str | None] = mapped_column(JSON, nullable=True)  # [{type, text, position}]
    review_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_items: Mapped[str | None] = mapped_column(JSON, nullable=True)  # [{dimension, level, clause, issue, suggestion}]
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100, higher = riskier

    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending / parsing / reviewing / completed / failed

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    case = relationship("Case", backref="contracts")
    owner = relationship("User", backref="contracts")

    def __repr__(self) -> str:
        return f"<Contract id={self.id} title={self.title!r} status={self.status!r}>"
