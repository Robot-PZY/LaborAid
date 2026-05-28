"""Verify login/register and optionally purge non-admin users."""
from __future__ import annotations

import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, update

from app.core.database import AsyncSessionLocal
from app.models.document import Template
from app.models.user import Team, User

BASE = "http://127.0.0.1:8000"
TEST_EMAIL = "test_verify@example.com"
TEST_PASSWORD = "TestPass123"


def req(method: str, path: str, data: dict | None = None, token: str | None = None) -> tuple[int, object]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def check(name: str, status: int, expect: tuple[int, ...]) -> bool:
    ok = status in expect
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name} -> HTTP {status}")
    return ok


async def purge_non_admin() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).order_by(User.id))
        users = result.scalars().all()
        print("=== Users before cleanup ===")
        for user in users:
            print(f"  id={user.id} role={user.role} name={user.name!r} email={user.email}")

        to_delete = [user for user in users if user.role != "admin"]
        if not to_delete:
            print("  (no non-admin users to delete)\n")
            return 0

        ids = [user.id for user in to_delete]
        print(f"  deleting {len(ids)} non-admin user(s): {ids}\n")
        await db.execute(delete(Team).where(Team.owner_id.in_(ids)))
        await db.execute(update(Template).where(Template.owner_id.in_(ids)).values(owner_id=None))
        await db.execute(update(User).where(User.id.in_(ids)).values(team_id=None))
        for user in to_delete:
            await db.delete(user)
        await db.commit()
        return len(ids)


async def delete_test_user() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalar_one_or_none()
        if not user:
            return
        await db.execute(delete(Team).where(Team.owner_id == user.id))
        await db.execute(update(Template).where(Template.owner_id == user.id).values(owner_id=None))
        await db.delete(user)
        await db.commit()
        print(f"  cleaned up test user: {TEST_EMAIL}")


def verify_auth() -> list[bool]:
    print("=== Auth verification ===")
    results: list[bool] = []

    status, login = req(
        "POST",
        "/api/v1/auth/login",
        {"email": "admin@laboraid.local", "password": "123456"},
    )
    results.append(check("Admin login (email)", status, (200,)))
    admin_token = login.get("access_token") if isinstance(login, dict) else None

    status, _ = req(
        "POST",
        "/api/v1/auth/login",
        {"email": "Admin", "password": "123456"},
    )
    results.append(check("Admin login (name)", status, (200,)))

    status, me = req("GET", "/api/v1/auth/me", token=admin_token)
    results.append(check("Admin /me", status, (200,)))
    if isinstance(me, dict):
        print(f"       admin role={me.get('role')} email={me.get('email')}")

    status, _ = req(
        "POST",
        "/api/v1/auth/login",
        {"email": "admin@laboraid.local", "password": "wrongpass"},
    )
    results.append(check("Wrong password rejected", status, (401,)))

    test_user = {"name": "测试用户", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    status, reg = req("POST", "/api/v1/auth/register", test_user)
    results.append(check("Register new user", status, (201,)))
    if isinstance(reg, dict):
        print(f"       registered id={reg.get('id')} role={reg.get('role')}")

    status, _ = req("POST", "/api/v1/auth/register", test_user)
    results.append(check("Duplicate email rejected", status, (400,)))

    status, _ = req(
        "POST",
        "/api/v1/auth/register",
        {"name": "弱密码", "email": "weak@laboraid.local", "password": "12345678"},
    )
    results.append(check("Weak password rejected (no letter)", status, (400,)))

    status, login = req(
        "POST",
        "/api/v1/auth/login",
        {"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    results.append(check("New user login", status, (200,)))
    user_token = login.get("access_token") if isinstance(login, dict) else None

    status, user_me = req("GET", "/api/v1/auth/me", token=user_token)
    results.append(check("New user /me", status, (200,)))
    if isinstance(user_me, dict):
        print(f"       user role={user_me.get('role')} name={user_me.get('name')}")

    return results


async def main() -> int:
    deleted = await purge_non_admin()
    results = verify_auth()
    await delete_test_user()

    async with AsyncSessionLocal() as db:
        remaining = (await db.execute(select(User.id, User.email, User.role).order_by(User.id))).all()
        print("\n=== Remaining users ===")
        for row in remaining:
            print(f"  id={row.id} role={row.role} email={row.email}")

    passed = sum(results)
    total = len(results)
    print(f"\nAuth checks: {passed}/{total} passed | removed {deleted} non-admin user(s)")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
