"""系统级配置归属的虚拟用户（全局 LLM / 应用配置）。"""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User

SYSTEM_USER_EMAIL = "system@laboraid.internal"
SYSTEM_USER_NAME = "劳权智助 系统"


async def get_system_user(db: AsyncSession) -> User:
    """获取或创建用于存放全局配置的系统用户。"""
    result = await db.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        name=SYSTEM_USER_NAME,
        email=SYSTEM_USER_EMAIL,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
