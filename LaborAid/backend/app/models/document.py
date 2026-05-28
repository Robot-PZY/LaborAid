from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_templates_owner_id", "owner_id"),
        Index("ix_templates_type", "type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # complaint / answer / appeal / counterclaim / agency_opinion / defense_opinion
    # evidence_list / cross_examination / legal_opinion / lawyer_letter / contract
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    structure: Mapped[str] = mapped_column(JSON, nullable=False)
    # 模板结构定义：{ sections: [{name, required, fields: [...]}] }

    ai_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # AI生成该类文书的提示词模板

    format_rules: Mapped[str] = mapped_column(JSON, nullable=True)
    # 排版规则：{ font: "仿宋", size: 14, line_spacing: 28, margins: [37, 28, 35, 26] }

    variables: Mapped[str] = mapped_column(JSON, default="[]")
    # 模板变量定义：[{name, label, type, required, default}]

    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<Template id={self.id} name={self.name!r} type={self.type!r}>"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_id", "owner_id"),
        Index("ix_documents_case_id", "case_id"),
        Index("ix_documents_status", "status"),
        # Composite: list documents by owner + case (filtered listing)
        Index("ix_documents_owner_case", "owner_id", "case_id"),
        # Composite: list documents by owner + type
        Index("ix_documents_owner_type", "owner_id", "type"),
        # Composite: list documents by case + status
        Index("ix_documents_case_status", "case_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    template_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ai_metadata: Mapped[str | None] = mapped_column(JSON, nullable=True)
    # AI生成元数据：{ cited_laws: [...], cited_cases: [...], case_parsing: {...} }

    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft / generated / reviewed / exported

    version: Mapped[int] = mapped_column(Integer, default=1)
    exported_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="documents")
    case = relationship("Case", back_populates="documents")
    template = relationship("Template")

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r} type={self.type!r} status={self.status!r}>"
