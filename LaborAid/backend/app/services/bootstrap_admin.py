"""启动时确保存在初始平台管理员账号。"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def ensure_initial_admin(db: AsyncSession) -> None:
    """若尚无该初始管理员，则创建（仅首次）。"""
    settings = get_settings()
    email = settings.INITIAL_ADMIN_EMAIL.strip().lower()
    name = settings.INITIAL_ADMIN_NAME.strip()
    password = settings.INITIAL_ADMIN_PASSWORD

    if not email or not name or not password:
        return

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        changed = False
        if user.role != "admin":
            user.role = "admin"
            changed = True
        if user.name != name:
            user.name = name
            changed = True
        if changed:
            await db.commit()
            logger.info("Initial admin account updated: %s", email)
        return

    result = await db.execute(select(User).where(User.name == name))
    by_name = result.scalar_one_or_none()
    if by_name:
        by_name.email = email
        by_name.role = "admin"
        by_name.password_hash = hash_password(password)
        by_name.is_active = True
        await db.commit()
        logger.info("Promoted existing user '%s' to initial admin", name)
        return

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    logger.info("Initial admin created: name=%s email=%s", name, email)


async def find_user_by_login(db: AsyncSession, account: str) -> User | None:
    """按邮箱或显示名（如 Admin）查找用户；账号名区分大小写，邮箱不区分。"""
    account = (account or "").strip()
    if not account:
        return None
    if "@" in account:
        result = await db.execute(
            select(User).where(User.email == account.lower())
        )
    else:
        result = await db.execute(select(User).where(User.name == account))
    return result.scalar_one_or_none()
