import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, or_, and_, false as sa_false
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.document import Template
from app.schemas.document import TemplateCreate, TemplateUpdate, TemplateOut
from app.services.docgen.template_helpers import enrich_template_dict

logger = logging.getLogger(__name__)
router = APIRouter()


def _template_out_payload(tmpl: Template) -> dict:
    base = TemplateOut.model_validate(tmpl).model_dump(mode="json")
    base.update(enrich_template_dict(tmpl))
    return base

ALLOWED_TEMPLATE_TYPES = {
    "complaint", "answer", "appeal", "counterclaim", "agency_opinion",
    "defense_opinion", "evidence_list", "cross_examination", "legal_opinion",
    "lawyer_letter", "contract", "labor_contract", "settlement_agreement", "other",
    "application",
    "labor_supervision",
    "preservation_application",
    "mediation",
    "wage_demand_letter",
    "forced_termination_notice",
    "arbitration_authorization",
    "jurisdiction_objection",
    "evidence_preservation",
}


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    if type and type not in ALLOWED_TEMPLATE_TYPES:
        raise HTTPException(400, f"无效的模板类型，允许值: {', '.join(sorted(ALLOWED_TEMPLATE_TYPES))}")
    try:
        team_filter = (
            and_(Template.team_id == current_user.team_id)
            if current_user.team_id is not None
            else sa_false()
        )
        base_where = or_(
            Template.is_public == True,
            Template.owner_id == current_user.id,
            team_filter,
        )
        # Count query for pagination header
        from sqlalchemy import func as sa_func
        count_q = select(sa_func.count(Template.id)).where(base_where)
        if type:
            count_q = count_q.where(Template.type == type)
        total = (await db.execute(count_q)).scalar() or 0

        q = select(Template).where(base_where)
        if type:
            q = q.where(Template.type == type)
        q = q.order_by(Template.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(q)
        items = result.scalars().all()
        data = [_template_out_payload(t) for t in items]
        return JSONResponse(content=data, headers={"X-Total-Count": str(total)})
    except Exception as e:
        logger.error("List templates failed: %s", e)
        raise HTTPException(500, "查询模板列表失败")


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.type and data.type not in ALLOWED_TEMPLATE_TYPES:
        raise HTTPException(400, f"无效的模板类型，允许值: {', '.join(sorted(ALLOWED_TEMPLATE_TYPES))}")
    try:
        tmpl = Template(
            **data.model_dump(),
            owner_id=current_user.id,
            team_id=current_user.team_id,
        )
        db.add(tmpl)
        await db.flush()
        await db.refresh(tmpl)
        return _template_out_payload(tmpl)
    except Exception as e:
        logger.error("Create template failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "创建模板失败")


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tmpl = await db.get(Template, template_id)
        if not tmpl:
            raise HTTPException(404, "模板不存在")
        return _template_out_payload(tmpl)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get template failed: %s", e)
        raise HTTPException(500, "查询模板失败")


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tmpl = await db.get(Template, template_id)
        if not tmpl or (tmpl.owner_id != current_user.id):
            raise HTTPException(404, "模板不存在或无权编辑")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(tmpl, k, v)
        await db.flush()
        await db.refresh(tmpl)
        return _template_out_payload(tmpl)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update template failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "更新模板失败")


@router.post("/seed-platform")
async def seed_platform_templates(
    current_user: User = Depends(get_current_user),
):
    """导入平台劳动者文书模板包（幂等）。"""
    require_admin(current_user)
    try:
        from templates.seed_platform_pack import seed_platform_pack

        result = seed_platform_pack()
        return {
            "message": "平台文书模板已同步",
            "ok": True,
            "pack": result,
        }
    except Exception as e:
        logger.error("Seed platform templates failed: %s", e)
        raise HTTPException(500, "导入模板包失败")


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tmpl = await db.get(Template, template_id)
        if not tmpl or tmpl.owner_id != current_user.id:
            raise HTTPException(404, "模板不存在或无权删除")
        await db.delete(tmpl)
        await db.flush()
        return {"message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete template failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除模板失败")
