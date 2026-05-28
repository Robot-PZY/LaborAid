from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_owner_id", "owner_id"),
        Index("ix_cases_status", "status"),
        # Composite: list/filter by owner + status (most common query pattern)
        Index("ix_cases_owner_status", "owner_id", "status"),
        # Composite: list/filter by owner + type
        Index("ix_cases_owner_type", "owner_id", "case_type"),
        # Composite: team-based visibility queries
        Index("ix_cases_team_id", "team_id"),
        # Composite: team-based listing filtered by status
        Index("ix_cases_team_status", "team_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # civil_litigation / criminal_defense / non_litigation / administrative_labor
    court: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    # active / closed / archived

    plaintiff: Mapped[str | None] = mapped_column(Text, nullable=True)
    defendant: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    filing_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hearing_dates: Mapped[str | None] = mapped_column(JSON, nullable=True)
    deadline_dates: Mapped[str | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")  # noqa: F821
    evidences = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Case id={self.id} title={self.title!r} status={self.status!r}>"
