"""用户个人材料库 — 维权周期内跨模块文件归档"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserMaterial(Base):
    __tablename__ = "user_materials"
    __table_args__ = (
        Index("ix_user_materials_user_id", "user_id"),
        Index("ix_user_materials_user_stage", "user_id", "stage"),
        Index("ix_user_materials_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32), default="manual")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    stage: Mapped[str] = mapped_column(String(32), default="preparation")
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
