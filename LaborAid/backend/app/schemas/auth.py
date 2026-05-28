from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "张律师",
                    "email": "lawyer@example.com",
                    "password": "SecurePass123",
                }
            ]
        }
    }

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("姓名不能为空")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度不能少于6位")
        if len(v) > 128:
            raise ValueError("密码长度不能超过128位")
        return v


class UserLogin(BaseModel):
    email: str  # 邮箱或管理员账号名（如 Admin）
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "Admin",
                    "password": "123456",
                }
            ]
        }
    }


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class TokenData(BaseModel):
    user_id: int
    email: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    team_id: int | None = None
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "张律师",
                    "email": "lawyer@example.com",
                    "role": "lawyer",
                    "team_id": None,
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    }


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"name": "李律师"},
            ]
        }
    }
