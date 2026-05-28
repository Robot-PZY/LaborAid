"""Tests for /api/v1/enterprise endpoints (Qichacha 736)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.services.enterprise.qichacha import QichachaClient


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_qichacha_token_generation():
    token = QichachaClient.build_token("AppKey", "1690000000", "SecretKey")
    assert token == "70A858214386EFFE1D1D340AAEAB3B09"


@pytest.mark.asyncio
async def test_enterprise_status_unconfigured(client, auth_headers, monkeypatch):
    monkeypatch.setenv("QICHACHA_API_KEY", "")
    monkeypatch.setenv("QICHACHA_SECRET_KEY", "")
    get_settings.cache_clear()
    response = await client.get("/api/v1/enterprise/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["provider"] == "qichacha"
    assert data["api_code"] == "736"


@pytest.mark.asyncio
async def test_enterprise_status_configured(client, auth_headers):
    with patch("app.api.routers.enterprise.get_qichacha_client") as mock_factory:
        mock_client = mock_factory.return_value
        mock_client.configured = True
        response = await client.get("/api/v1/enterprise/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["configured"] is True


@pytest.mark.asyncio
async def test_enterprise_scan_unconfigured(client, auth_headers, monkeypatch):
    monkeypatch.setenv("QICHACHA_API_KEY", "")
    monkeypatch.setenv("QICHACHA_SECRET_KEY", "")
    get_settings.cache_clear()
    response = await client.get(
        "/api/v1/enterprise/scan",
        params={"search_key": "测试公司"},
        headers=auth_headers,
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_enterprise_scan_success(client, auth_headers):
    mock_result = {
        "KeyNo": "abc123",
        "Name": "测试科技有限公司",
        "CreditCode": "91110000MA01234567",
        "Status": "存续",
        "OperName": "张三",
        "RegistCapi": "1000万元",
        "StartDate": "2018-01-01",
        "Address": "北京市朝阳区",
        "Scope": "软件开发",
        "EconKind": "有限责任公司",
        "ContactInfo": {"PhoneNumber": "010-12345678", "Email": "test@example.com"},
        "Penalty": [{"PenaltyDate": "2023-01-01", "OfficeName": "市场监管局", "PenaltyType": "违法", "Content": "罚款"}],
        "Exceptions": [],
        "ShiXinItems": [],
        "ZhiXingItems": [],
    }

    with patch("app.api.routers.enterprise.get_qichacha_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client.configured = True
        mock_client.risk_scan = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_client

        response = await client.get(
            "/api/v1/enterprise/scan",
            params={"search_key": "测试科技有限公司"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["search_key"] == "测试科技有限公司"
    assert data["company"]["name"] == "测试科技有限公司"
    assert data["company"]["credit_code"] == "91110000MA01234567"
    assert data["risk_summary"]["penalty_count"] == 1
    assert data["risk_summary"]["has_risk"] is True
    assert "qcc.com" in (data["external_search_url"] or "")


@pytest.mark.asyncio
async def test_enterprise_requires_auth(client):
    response = await client.get("/api/v1/enterprise/status")
    assert response.status_code == 401
