"""用户维权咨询方案（前台 intake 结果）持久化。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserIntakePlan(Base):
    __tablename__ = "user_intake_plans"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_intake_plans_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
