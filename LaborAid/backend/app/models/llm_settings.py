"""LLM配置模型"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class LLMSettings(Base):
    __tablename__ = "llm_settings"
    __table_args__ = (
        Index("ix_llm_settings_owner_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, default="deepseek-v4-pro")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", backref="llm_settings")

    def __repr__(self) -> str:
        return f"<LLMSettings id={self.id} name={self.name!r} model={self.model_name!r}>"
