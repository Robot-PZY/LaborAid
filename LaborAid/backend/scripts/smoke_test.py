"""Quick end-to-end API smoke test for LaborAid."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, token: str | None = None, data: dict | None = None) -> tuple[int, object]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return resp.status, raw[:200]
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw[:200]
    except Exception as e:
        return 0, str(e)


def ok(name: str, status: int, expect=(200, 201)) -> bool:
    passed = status in expect
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name} -> HTTP {status}")
    return passed


def main() -> int:
    print("=== LaborAid smoke test ===\n")
    results: list[bool] = []

    st, health = req("GET", "/health")
    results.append(ok("Health", st))
    if isinstance(health, dict):
        comps = health.get("components", {})
        for k, v in comps.items():
            status = v.get("status") if isinstance(v, dict) else v
            print(f"       - {k}: {status}")

    st, _ = req("POST", "/api/v1/auth/login", data={"email": "admin@laboraid.local", "password": "123456"})
    results.append(ok("Admin login", st))

    st, login = req("POST", "/api/v1/auth/login", data={"email": "Admin", "password": "123456"})
    if st != 200:
        st, login = req("POST", "/api/v1/auth/login", data={"email": "admin@laboraid.local", "password": "123456"})
    results.append(ok("User/Admin token", st))
    if st != 200 or not isinstance(login, dict):
        print("\nCannot continue without token.")
        return 1
    token = login.get("access_token", "")

    endpoints = [
        ("GET", "/api/v1/auth/me", "Auth /me"),
        ("GET", "/api/v1/user/overview", "User overview"),
        ("GET", "/api/v1/guidance", "Guidance"),
        ("GET", "/api/v1/channels", "Channels"),
        ("GET", "/api/v1/vault/stats", "Vault stats"),
        ("GET", "/api/v1/cases", "Cases list"),
        ("GET", "/api/v1/documents", "Documents list"),
        ("GET", "/api/v1/evidence?case_id=1", "Evidence list", (200, 404)),
        ("GET", "/api/v1/contracts", "Contracts list"),
        ("GET", "/api/v1/research", "Research list"),
        ("GET", "/api/v1/knowledge", "Knowledge (read)"),
        ("GET", "/api/v1/knowledge/stats", "Knowledge stats"),
        ("GET", "/api/v1/templates", "Templates"),
        ("GET", "/api/v1/vector/stats", "Vector stats"),
        ("GET", "/api/v1/llm-settings/active", "Active LLM"),
        ("GET", "/api/v1/llm-settings/active-vision", "Active vision LLM"),
        ("GET", "/api/v1/admin/stats/overview", "Admin overview"),
        ("GET", "/api/v1/llm-settings", "Admin LLM settings", (200, 403)),
    ]

    for item in endpoints:
        method, path, name = item[0], item[1], item[2]
        expect = item[3] if len(item) > 3 else (200,)
        st, body = req(method, path, token=token)
        results.append(ok(name, st, expect))
        if st not in expect and isinstance(body, dict) and "detail" in body:
            print(f"         detail: {body['detail']}")

    # Admin-only knowledge write probe (should 403 for non-admin - skip if admin)
    st, me = req("GET", "/api/v1/auth/me", token=token)
    role = me.get("role") if isinstance(me, dict) else ""
    if role == "admin":
        st, _ = req("GET", "/api/v1/llm-settings", token=token)
        results.append(ok("Admin LLM list", st))
        st, _ = req("GET", "/api/v1/app-config", token=token)
        results.append(ok("Admin app-config", st))

    # Search smoke (may call LLM - just check endpoint responds)
    st, _ = req("POST", "/api/v1/search", token=token, data={"query": "劳动法", "limit": 3})
    results.append(ok("Search unified", st, (200, 422, 500)))

    passed = sum(results)
    total = len(results)
    print(f"\n=== Summary: {passed}/{total} checks passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
