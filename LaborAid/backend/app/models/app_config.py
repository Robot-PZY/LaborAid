"""应用配置模型 — 向量数据库路径、系统参数等"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AppConfig(Base):
    __tablename__ = "app_configs"
    __table_args__ = (
        Index("ix_app_configs_owner_id", "owner_id"),
        Index("ix_app_configs_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    config_key: Mapped[str] = mapped_column(String(200), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", backref="app_configs")

    def __repr__(self) -> str:
        return f"<AppConfig id={self.id} key={self.config_key!r}>"
