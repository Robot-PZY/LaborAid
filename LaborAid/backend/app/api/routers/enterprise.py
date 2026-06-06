"""企业信息查询 — 企查查 API 736（劳动者查用人单位）。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import check_rate_limit, get_current_user
from app.models.user import User
from app.services.enterprise.query_resolver import resolve_enterprise_search_key
from app.services.llm_resolver import resolve_user_llm
from app.schemas.enterprise import (
    EnterpriseCompanyOut,
    EnterpriseRiskItemsOut,
    EnterpriseRiskSummaryOut,
    EnterpriseScanOut,
    EnterpriseStatusOut,
)
from app.services.enterprise.qichacha import (
    EnterpriseServiceError,
    external_search_url,
    get_qichacha_client,
    normalize_risk_scan,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DISCLAIMER = "数据来源于企查查公开信息，仅供参考，请以市场监管部门及司法机关官方登记为准。"


@router.get("/status", response_model=EnterpriseStatusOut)
async def enterprise_status(_: User = Depends(get_current_user)):
    client = get_qichacha_client()
    if client.configured:
        return EnterpriseStatusOut(
            configured=True,
            message="企业风险扫描服务已就绪（企查查 736）",
        )
    return EnterpriseStatusOut(
        configured=False,
        message="未配置企查查凭证，可在 .env 中设置 QICHACHA_API_KEY 与 QICHACHA_SECRET_KEY",
    )


@router.get("/scan", response_model=EnterpriseScanOut)
async def scan_enterprise(
    search_key: str = Query(..., min_length=2, max_length=100, description="企业名称或统一社会信用代码"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not check_rate_limit(f"enterprise_scan:{current_user.id}", max_requests=10, window_seconds=60):
        raise HTTPException(429, "查询过于频繁，请稍后再试")

    client = get_qichacha_client()
    key = search_key.strip()
    llm = await resolve_user_llm(db, current_user)
    api_search_key = await resolve_enterprise_search_key(key, llm=llm)

    try:
        raw = await client.risk_scan(api_search_key)
        normalized = normalize_risk_scan(raw)
        company = normalized["company"]
        if not company.get("name"):
            raise HTTPException(404, "未找到该企业信息")

        return EnterpriseScanOut(
            search_key=key,
            company=EnterpriseCompanyOut.model_validate(company),
            risk_summary=EnterpriseRiskSummaryOut.model_validate(normalized["risk_summary"]),
            risks=EnterpriseRiskItemsOut.model_validate(normalized["risks"]),
            external_search_url=external_search_url(key),
            disclaimer=DISCLAIMER,
        )
    except EnterpriseServiceError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Enterprise scan failed: %s", exc)
        raise HTTPException(502, "企业查询失败，请稍后重试") from exc
