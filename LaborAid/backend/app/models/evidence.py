from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Evidence(Base):
    __tablename__ = "evidences"
    __table_args__ = (
        Index("ix_evidences_case_id", "case_id"),
        # Composite: evidence chain analysis queries by case + sort order
        Index("ix_evidences_case_sort", "case_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # documentary / physical / electronic / testimony / audio_visual / expert
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    case = relationship("Case", back_populates="evidences")

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} title={self.title!r} type={self.type!r}>"
