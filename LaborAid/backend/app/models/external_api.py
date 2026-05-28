"""外部API数据源配置模型 — 用户可自由定义任意接口"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ExternalApiConfig(Base):
    __tablename__ = "external_api_configs"
    __table_args__ = (
        Index("ix_external_api_configs_owner_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # 认证配置
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    # none / bearer / api_key / basic / custom
    auth_token: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    auth_header_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    auth_username: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    auth_password: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    custom_headers: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # JSON格式自定义请求头

    # 端点配置
    search_law_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    search_law_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    search_case_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    search_case_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    get_provision_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    get_provision_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    health_check_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # 响应映射 — JSON格式，指定如何解析响应字段
    response_mapping: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # 自定义请求参数模板 — JSON格式
    request_template: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="custom")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", backref="external_api_configs")

    def __repr__(self) -> str:
        return f"<ExternalApiConfig id={self.id} name={self.name!r} base_url={self.base_url[:50]!r}>"
