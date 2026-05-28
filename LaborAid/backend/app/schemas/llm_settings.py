"""LLM配置管理 Schema"""

from datetime import datetime
from pydantic import BaseModel, field_validator


class LLMSettingsCreate(BaseModel):
    name: str
    base_url: str
    api_key: str
    model_name: str = "deepseek-v4-pro"
    max_tokens: int = 4096
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("配置名称不能为空")
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("API地址不能为空")
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("API地址必须以 http:// 或 https:// 开头")
        return v

    @field_validator("model_name")
    @classmethod
    def model_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()

    @field_validator("max_tokens")
    @classmethod
    def max_tokens_range(cls, v):
        if v < 1 or v > 128000:
            raise ValueError("max_tokens 必须在 1-128000 之间")
        return v


class LLMSettingsUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    max_tokens: int | None = None
    is_default: bool | None = None


class LLMSettingsOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key_masked: str
    model_name: str
    max_tokens: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    profile_role: str | None = None  # text_primary | vision_ocr | vision | other

    model_config = {"from_attributes": True}


class ConnectivityTestRequest(BaseModel):
    base_url: str
    api_key: str
    model_name: str
    setting_id: int | None = None


class ConnectivityTestResult(BaseModel):
    success: bool
    message: str
    model: str = ""
    latency_ms: int = 0


class ActiveLLMOut(BaseModel):
    """Currently active LLM for the signed-in user (no secrets)."""

    config_id: int | None = None
    config_name: str
    model_name: str
    max_tokens: int
    base_url: str
    source: str  # "database" | "env"
    has_api_key: bool
