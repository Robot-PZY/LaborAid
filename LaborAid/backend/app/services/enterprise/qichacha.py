"""企查查开放平台 — 企业风险扫描（API 736）。"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

RISK_SCAN_PATH = "/ECIInfoOverview/GetInfo"


class EnterpriseServiceError(Exception):
    """企业查询业务错误（可展示给用户）。"""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QichachaClient:
    """企查查 api.qichacha.com 客户端（736 企业风险扫描）。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (settings.QICHACHA_API_KEY or "").strip()
        self.secret_key = (settings.QICHACHA_SECRET_KEY or "").strip()
        self.base_url = (settings.QICHACHA_API_URL or "https://api.qichacha.com").rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    @staticmethod
    def build_token(api_key: str, timespan: str, secret_key: str) -> str:
        raw = f"{api_key}{timespan}{secret_key}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()

    async def risk_scan(self, search_key: str) -> dict[str, Any]:
        if not self.configured:
            raise EnterpriseServiceError(
                "企业查询服务尚未配置，请在 .env 中设置 QICHACHA_API_KEY 与 QICHACHA_SECRET_KEY",
                status_code=503,
            )

        timespan = str(int(time.time()))
        token = self.build_token(self.api_key, timespan, self.secret_key)
        url = f"{self.base_url}{RISK_SCAN_PATH}"
        params = {"key": self.api_key, "searchKey": search_key.strip()}
        headers = {"Token": token, "Timespan": timespan}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            logger.warning("Qichacha timeout: searchKey=%s", search_key)
            raise EnterpriseServiceError("企业信息查询超时，请稍后重试", status_code=504) from exc
        except httpx.HTTPError as exc:
            logger.warning("Qichacha HTTP error: %s", exc)
            raise EnterpriseServiceError("无法连接企查查服务，请稍后重试", status_code=502) from exc
        except ValueError as exc:
            raise EnterpriseServiceError("企查查返回数据格式异常", status_code=502) from exc

        status = str(payload.get("Status") or payload.get("status") or "")
        message = str(payload.get("Message") or payload.get("message") or "查询失败")

        if status == "200":
            result = payload.get("Result")
            if not isinstance(result, dict):
                raise EnterpriseServiceError("企查查返回数据格式异常", status_code=502)
            return result

        logger.info("Qichacha API Status=%s Message=%s", status, message)
        if status in ("201", "202"):
            raise EnterpriseServiceError("未找到匹配的企业，请检查名称或统一社会信用代码是否正确", status_code=404)
        if status in ("101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112"):
            raise EnterpriseServiceError(message or "企查查鉴权失败，请检查 Key 与 SecretKey", status_code=502)
        raise EnterpriseServiceError(message, status_code=502)


def get_qichacha_client() -> QichachaClient:
    return QichachaClient()


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _first_items(value: Any, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value[:limit] if isinstance(item, dict)]


def normalize_risk_scan(raw: dict[str, Any]) -> dict[str, Any]:
    """将 736 接口返回映射为前端统一结构。"""
    contact = raw.get("ContactInfo") if isinstance(raw.get("ContactInfo"), dict) else {}
    website = ""
    sites = contact.get("WebSite")
    if isinstance(sites, list) and sites:
        first_site = sites[0]
        if isinstance(first_site, dict):
            website = str(first_site.get("Url") or first_site.get("Name") or "").strip()

    key_no = raw.get("KeyNo")
    profile_url = f"https://www.qcc.com/firm_{key_no}.html" if key_no else None

    penalties = _first_items(raw.get("Penalty"))
    exceptions = _first_items(raw.get("Exceptions"))
    shixin = _first_items(raw.get("ShiXinItems"))
    zhixing = _first_items(raw.get("ZhiXingItems"))

    risk_summary = {
        "penalty_count": _list_len(raw.get("Penalty")),
        "exception_count": _list_len(raw.get("Exceptions")),
        "shixin_count": _list_len(raw.get("ShiXinItems")),
        "zhixing_count": _list_len(raw.get("ZhiXingItems")),
        "m_pledge_count": _list_len(raw.get("MPledge")),
        "pledge_count": _list_len(raw.get("Pledge")),
        "spot_check_count": _list_len(raw.get("SpotCheck")),
        "has_liquidation": bool(raw.get("Liquidation")),
        "has_risk": any(
            [
                _list_len(raw.get("Penalty")),
                _list_len(raw.get("Exceptions")),
                _list_len(raw.get("ShiXinItems")),
                _list_len(raw.get("ZhiXingItems")),
                _list_len(raw.get("MPledge")),
                _list_len(raw.get("Pledge")),
            ]
        ),
    }

    return {
        "company": {
            "id": str(key_no) if key_no is not None else None,
            "name": str(raw.get("Name") or "").strip(),
            "credit_code": str(raw.get("CreditCode") or "").strip() or None,
            "reg_status": str(raw.get("Status") or "").strip() or None,
            "legal_person": str(raw.get("OperName") or "").strip() or None,
            "reg_capital": str(raw.get("RegistCapi") or raw.get("RegisteredCapital") or "").strip() or None,
            "establish_time": str(raw.get("StartDate") or "").strip() or None,
            "address": str(raw.get("Address") or "").strip() or None,
            "business_scope": str(raw.get("Scope") or "").strip() or None,
            "company_type": str(raw.get("EconKind") or "").strip() or None,
            "phone": str(contact.get("PhoneNumber") or "").strip() or None,
            "email": str(contact.get("Email") or "").strip() or None,
            "website": website or None,
            "profile_url": profile_url,
            "source": "qichacha",
            "belong_org": str(raw.get("BelongOrg") or "").strip() or None,
            "insured_count": str(raw.get("InsuredCount") or "").strip() or None,
            "person_scope": str(raw.get("PersonScope") or "").strip() or None,
        },
        "risk_summary": risk_summary,
        "risks": {
            "penalties": penalties,
            "exceptions": exceptions,
            "shixin_items": shixin,
            "zhixing_items": zhixing,
        },
    }


def external_search_url(keyword: str) -> str:
    return f"https://www.qcc.com/web/search?key={quote(keyword.strip())}"
