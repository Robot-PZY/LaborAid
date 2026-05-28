"""法条审核核查路由"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.verification import (
    LawVerifyRequest,
    LawVerifyResponse,
    BatchVerifyRequest,
    BatchVerifyResponse,
)
from app.services.verification.engine import LawVerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/verify", response_model=LawVerifyResponse)
async def verify_law(
    data: LawVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    """单条法条核查 — 多源交叉验证"""
    if not data.law_name or not data.law_name.strip():
        raise HTTPException(400, "法律名称不能为空")
    if not data.article_number or not data.article_number.strip():
        raise HTTPException(400, "条款号不能为空")
    try:
        import time
        start = time.time()
        engine = LawVerificationEngine()
        result = await engine.verify_single(data)
        logger.info("Law verification took %.2fs for %s %s", time.time() - start, data.law_name, data.article_number)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Law verification failed: %s", e)
        raise HTTPException(500, "法条核查失败，请稍后重试")


@router.post("/verify-batch", response_model=BatchVerifyResponse)
async def verify_batch(
    data: BatchVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    """批量核查 — 从文书内容中自动提取法条引用并验证"""
    if not data.document_content or not data.document_content.strip():
        raise HTTPException(400, "文书内容不能为空")
    try:
        engine = LawVerificationEngine()
        results = await engine.verify_document(data.document_content)

        warnings = []
        for r in results:
            if not r.overall_consistent:
                warnings.append(f"{r.law_name} {r.article_number}: {r.recommendation}")

        return BatchVerifyResponse(
            total_references=len(results),
            verified=results,
            warnings=warnings,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch verification failed: %s", e)
        raise HTTPException(500, "批量核查失败，请稍后重试")
