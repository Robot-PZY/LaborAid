"""认证路由 — 注册、登录、用户信息管理。"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.config import get_settings
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
    check_rate_limit_with_headers, validate_password_strength,
)
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserOut, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# Failed login tracking for account lockout
_FAILED_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION = 900  # 15 minutes


def _check_account_lockout(email: str) -> bool:
    """Return True if account is locked due to too many failed attempts."""
    import time
    attempts = _FAILED_LOGIN_ATTEMPTS.get(email, [])
    now = time.monotonic()
    # Remove expired attempts
    cutoff = now - _LOCKOUT_DURATION
    attempts = [t for t in attempts if t > cutoff]
    _FAILED_LOGIN_ATTEMPTS[email] = attempts
    return len(attempts) >= _MAX_FAILED_ATTEMPTS


def _record_failed_login(email: str) -> None:
    """Record a failed login attempt."""
    import time
    if email not in _FAILED_LOGIN_ATTEMPTS:
        _FAILED_LOGIN_ATTEMPTS[email] = []
    _FAILED_LOGIN_ATTEMPTS[email].append(time.monotonic())


def _clear_failed_logins(email: str) -> None:
    """Clear failed login attempts after successful login."""
    _FAILED_LOGIN_ATTEMPTS.pop(email, None)


def _promote_admin_if_configured(user: User) -> None:
    """Grant admin role when email is listed in ADMIN_EMAIL env."""
    settings = get_settings()
    if user.email.lower() in settings.admin_email_set:
        user.role = "admin"


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Rate limit registration per IP
    client_ip = request.client.host if request.client else "unknown"
    allowed, rl_headers = check_rate_limit_with_headers(
        f"register:{client_ip}", max_requests=5, window_seconds=300
    )
    if not allowed:
        raise HTTPException(
            429,
            "注册请求过于频繁，请5分钟后再试",
            headers=rl_headers,
        )

    # Password strength validation
    is_strong, pw_error = validate_password_strength(data.password)
    if not is_strong:
        raise HTTPException(400, pw_error)

    try:
        exists = await db.execute(select(User).where(User.email == data.email))
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已注册")
        user = User(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
        )
        _promote_admin_if_configured(user)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Rate limit login per IP
    client_ip = request.client.host if request.client else "unknown"
    allowed, rl_headers = check_rate_limit_with_headers(
        f"login:{client_ip}", max_requests=10, window_seconds=60
    )
    if not allowed:
        raise HTTPException(
            429,
            "登录请求过于频繁，请稍后再试",
            headers=rl_headers,
        )

    try:
        # Check account lockout
        if _check_account_lockout(data.email):
            raise HTTPException(
                429,
                "账户已锁定，请15分钟后再试",
                headers=rl_headers,
            )

        from app.services.bootstrap_admin import find_user_by_login

        user = await find_user_by_login(db, data.email)
        if not user or not verify_password(data.password, user.password_hash):
            _record_failed_login(data.email)
            raise HTTPException(status_code=401, detail="账号或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账户已被禁用")

        _clear_failed_logins(data.email)
        _promote_admin_if_configured(user)
        await db.flush()
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return Token(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed: %s", e)
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if data.name is not None:
            current_user.name = data.name
        # Only admins can change roles; non-admins silently ignore this field
        if data.role is not None and current_user.role == "admin":
            if data.role not in ("admin", "lawyer", "assistant"):
                raise HTTPException(400, "无效的用户角色")
            current_user.role = data.role
        await db.flush()
        await db.refresh(current_user)
        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update user failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail="更新失败，请稍后重试")
