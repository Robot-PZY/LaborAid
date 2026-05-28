from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_owner_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    members: Mapped[list["User"]] = relationship("User", back_populates="team", foreign_keys="User.team_id")

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name!r}>"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="lawyer")  # admin / lawyer / assistant
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    team: Mapped[Team | None] = relationship("Team", back_populates="members", foreign_keys=[team_id])
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="owner")  # noqa: F821
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner")  # noqa: F821

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} email={self.email!r} role={self.role!r}>"
