"""外部API配置 Schema"""

import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class ExternalApiCreate(BaseModel):
    name: str
    description: str = ""
    base_url: str
    auth_type: str = "none"
    auth_token: str = ""
    auth_header_name: str = "Authorization"
    auth_username: str = ""
    auth_password: str = ""
    custom_headers: str = "{}"
    search_law_path: str = ""
    search_law_method: str = "GET"
    search_case_path: str = ""
    search_case_method: str = "GET"
    get_provision_path: str = ""
    get_provision_method: str = "GET"
    health_check_path: str = ""
    response_mapping: str = "{}"
    request_template: str = "{}"
    is_enabled: bool = True
    category: str = "custom"

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("API名称不能为空")
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def base_url_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("API地址不能为空")
        return v.strip().rstrip("/")

    @field_validator("auth_type")
    @classmethod
    def auth_type_must_be_valid(cls, v):
        valid = ("none", "bearer", "api_key", "basic")
        if v not in valid:
            raise ValueError(f"认证类型必须是: {', '.join(valid)}")
        return v

    @field_validator("custom_headers", "response_mapping", "request_template")
    @classmethod
    def must_be_valid_json(cls, v):
        if v:
            try:
                json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("必须是有效的JSON格式")
        return v


class ExternalApiUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_token: Optional[str] = None
    auth_header_name: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    custom_headers: Optional[str] = None
    search_law_path: Optional[str] = None
    search_law_method: Optional[str] = None
    search_case_path: Optional[str] = None
    search_case_method: Optional[str] = None
    get_provision_path: Optional[str] = None
    get_provision_method: Optional[str] = None
    health_check_path: Optional[str] = None
    response_mapping: Optional[str] = None
    request_template: Optional[str] = None
    is_enabled: Optional[bool] = None
    category: Optional[str] = None


class ExternalApiOut(BaseModel):
    id: int
    name: str
    description: str
    base_url: str
    auth_type: str
    auth_token_masked: str = ""
    auth_header_name: str
    auth_username: str
    auth_password_masked: str = ""
    custom_headers: str
    search_law_path: str
    search_law_method: str
    search_case_path: str
    search_case_method: str
    get_provision_path: str
    get_provision_method: str
    health_check_path: str
    response_mapping: str
    request_template: str
    is_enabled: bool
    category: str
    created_at: datetime
    updated_at: datetime


class ExternalApiTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int = 0


class ExternalApiPreset(BaseModel):
    key: str
    name: str
    category: str
    description: str
    base_url: str
    auth_type: str = "bearer"
    search_law_path: str = ""
    search_law_method: str = "GET"
    search_case_path: str = ""
    search_case_method: str = "GET"
    get_provision_path: str = ""
    get_provision_method: str = "GET"
    health_check_path: str = ""
    response_mapping: str = "{}"
    request_template: str = "{}"
