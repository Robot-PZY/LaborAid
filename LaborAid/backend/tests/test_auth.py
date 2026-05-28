"""Tests for /api/v1/auth endpoints: register, login, me."""

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """Registering a new user should return 201 with user data."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "新用户",
            "email": "newuser@example.com",
            "password": "Password1",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "新用户"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with an existing email should fail with 400."""
    payload = {
        "name": "用户A",
        "email": "dup@example.com",
        "password": "Password1",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_weak_password(client):
    """Registration with a weak password should fail validation."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "弱密码用户",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Logging in with correct credentials should return a JWT token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test1234",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    """Logging in with an incorrect password should return 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword1",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Logging in with a non-existent email should return 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "Password1",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client, auth_headers, test_user):
    """GET /me with a valid token should return the current user."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    """GET /me without a token should return 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_me(client, auth_headers):
    """PUT /me should update the user's name."""
    response = await client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"name": "更新后的名字"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "更新后的名字"
