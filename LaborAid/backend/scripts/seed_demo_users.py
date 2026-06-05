"""填充演示用户、案件、材料库等数据，便于管理端后台展示。

用法（在 LaborAid/backend 目录）:
  python scripts/seed_demo_users.py
  python scripts/seed_demo_users.py --count 50
  python scripts/seed_demo_users.py --clear
  python scripts/seed_demo_users.py --clear --count 40

演示账号邮箱: demo001@demo.laboraid.local ...  统一密码: Demo123456
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.research import ResearchReport
from app.models.user import User
from app.models.user_material import UserMaterial
from app.services.vault import vault_dest_path

DEMO_DOMAIN = "demo.laboraid.local"
DEMO_PASSWORD = "Demo123456"

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
    "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英", "华", "慧",
    "建国", "建华", "志强", "秀英", "桂英", "玉兰", "秀兰", "海涛", "晓明", "雪梅",
]

EMPLOYERS = [
    "华创科技有限公司", "味享餐饮管理有限公司", "鑫达建设工程有限公司", "顺通物流有限公司",
    "绿洲物业管理有限公司", "星辰电子商务有限公司", "博雅教育培训中心", "安泰保安服务有限公司",
    "金鼎制造有限公司", "云帆信息技术有限公司",
]

CASE_SCENARIOS = [
    {
        "title": "试用期违法解除劳动关系",
        "description": "用人单位以不能胜任工作为由在试用期内解除劳动合同，劳动者主张违法解除并要求赔偿金。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
    {
        "title": "拖欠工资及加班费争议",
        "description": "用人单位连续三个月未足额支付工资，且未支付休息日加班工资，劳动者申请劳动仲裁。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
    {
        "title": "未签订劳动合同二倍工资",
        "description": "入职超过一个月未签订书面劳动合同，劳动者主张二倍工资差额。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
    {
        "title": "孕期调岗降薪争议",
        "description": "女职工怀孕期间被调整岗位并降低薪资待遇，主张恢复原岗位及工资标准。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
    {
        "title": "工伤认定及待遇争议",
        "description": "工作期间受伤，用人单位未申请工伤认定，劳动者自行主张工伤待遇。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
    {
        "title": "违法解除劳动合同赔偿金",
        "description": "用人单位单方解除劳动合同，劳动者认为缺乏合法理由，主张2N赔偿金。",
        "plaintiff_tpl": "{name}",
        "defendant_tpl": "{employer}",
    },
]

EVIDENCE_ITEMS = [
    ("劳动合同", "documentary", "证明劳动关系成立"),
    ("工资银行流水", "electronic", "证明工资发放情况"),
    ("解除劳动合同通知书", "documentary", "证明解除事实"),
    ("考勤记录", "electronic", "证明加班及出勤"),
    ("微信工作群聊天记录", "electronic", "证明工作安排沟通过程"),
    ("社保缴费记录", "documentary", "证明社保缴纳主体"),
]

VAULT_FILES = [
    ("劳动合同扫描件.txt", "preparation", "manual", "劳动合同（2023年3月签订，约定试用期3个月）"),
    ("工资流水摘要.txt", "preparation", "manual", "2024年1-6月工资发放记录摘要"),
    ("解除通知照片说明.txt", "arbitration", "evidence", "用人单位出具的解除劳动合同通知书"),
    ("仲裁申请书草稿.txt", "complaint", "document", "劳动仲裁申请书（草稿）"),
    ("通话录音文字稿.txt", "preparation", "manual", "与HR沟通解除理由的录音整理"),
    ("考勤截图说明.txt", "preparation", "evidence", "企业微信考勤导出截图"),
]

DOC_SNIPPETS = [
    ("劳动仲裁申请书", "application", "draft"),
    ("证据清单", "evidence_list", "generated"),
    ("律师函（催告支付工资）", "lawyer_letter", "reviewed"),
]

RESEARCH_QUERIES = [
    "试用期解除劳动合同的法定条件有哪些？",
    "未签劳动合同二倍工资的仲裁时效如何计算？",
    "女职工孕期用人单位能否单方调岗降薪？",
]


def _rand_dt(days_back: int = 60) -> datetime:
    base = datetime.now(timezone.utc) - timedelta(days=random.randint(0, days_back))
    return base.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))


def _demo_email(seq: int) -> str:
    return f"demo{seq:03d}@{DEMO_DOMAIN}"


def _make_name(rng: random.Random) -> str:
    return rng.choice(SURNAMES) + rng.choice(GIVEN)


async def _count_demo_users(db) -> int:
    row = await db.execute(
        select(func.count(User.id)).where(User.email.like(f"%@{DEMO_DOMAIN}"))
    )
    return int(row.scalar() or 0)


async def clear_demo_data(db) -> None:
    result = await db.execute(select(User.id).where(User.email.like(f"%@{DEMO_DOMAIN}")))
    ids = [r[0] for r in result.all()]
    if not ids:
        print("No demo users to clear.")
        return
    await db.execute(delete(User).where(User.id.in_(ids)))
    await db.commit()
    print(f"Cleared {len(ids)} demo users (cascaded cases, docs, vault records).")


async def seed_demo_data(db, count: int, rng: random.Random) -> None:
    existing = await _count_demo_users(db)
    start_seq = existing + 1
    if existing >= count:
        print(f"Already have {existing} demo users (>= {count}). Use --clear to reset.")
        return

    to_create = count - existing
    print(f"Creating {to_create} demo users (existing {existing}, target {count})...")

    pwd_hash = hash_password(DEMO_PASSWORD)
    users_created = 0
    cases_created = 0
    vault_created = 0

    for i in range(to_create):
        seq = start_seq + i
        name = _make_name(rng)
        email = _demo_email(seq)
        dup = await db.execute(select(User).where(User.email == email))
        if dup.scalar_one_or_none():
            continue

        created_at = _rand_dt(55)
        role = "assistant" if rng.random() < 0.08 else "lawyer"
        is_active = rng.random() > 0.06

        user = User(
            name=name,
            email=email,
            password_hash=pwd_hash,
            role=role,
            is_active=is_active,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(user)
        await db.flush()
        users_created += 1

        employer = rng.choice(EMPLOYERS)
        num_cases = 1 if rng.random() < 0.35 else (2 if rng.random() < 0.7 else 3)

        for _ in range(num_cases):
            scenario = rng.choice(CASE_SCENARIOS)
            case_dt = created_at + timedelta(days=rng.randint(0, 14), hours=rng.randint(1, 48))
            case = Case(
                title=f"{name} - {scenario['title']}",
                case_type="administrative_labor",
                status=rng.choice(["active", "active", "active", "closed", "archived"]),
                plaintiff=scenario["plaintiff_tpl"].format(name=name),
                defendant=scenario["defendant_tpl"].format(employer=employer),
                description=scenario["description"],
                owner_id=user.id,
                ai_snapshot={
                    "cause": "labor_dispute",
                    "scenario_id": rng.choice(["probation", "wage_arrears", "maternity", "work_injury"]),
                    "readiness_score": rng.randint(45, 92),
                },
                created_at=case_dt,
                updated_at=case_dt,
            )
            db.add(case)
            await db.flush()
            cases_created += 1

            ev_count = rng.randint(2, min(5, len(EVIDENCE_ITEMS)))
            for j, (ev_title, ev_type, purpose) in enumerate(rng.sample(EVIDENCE_ITEMS, ev_count)):
                ev_dt = case_dt + timedelta(hours=j + 1)
                has_ocr = rng.random() < 0.75
                ocr = None
                if has_ocr:
                    ocr = (
                        f"【OCR摘录】{ev_title}\n"
                        f"劳动者：{name}\n用人单位：{employer}\n"
                        f"证明目的：{purpose}\n"
                        f"扫描时间：{ev_dt.date()}"
                    )
                db.add(
                    Evidence(
                        case_id=case.id,
                        type=ev_type,
                        title=ev_title,
                        ocr_text=ocr,
                        tags=["demo", "labor"],
                        sort_order=j,
                        analysis=f"证明{purpose}。" if rng.random() < 0.5 else None,
                        created_at=ev_dt,
                    )
                )

            if rng.random() < 0.55:
                doc_title, doc_type, doc_status = rng.choice(DOC_SNIPPETS)
                doc_dt = case_dt + timedelta(days=rng.randint(1, 10))
                db.add(
                    Document(
                        case_id=case.id,
                        owner_id=user.id,
                        type=doc_type,
                        title=f"{name} - {doc_title}",
                        content=(
                            f"（演示文书）\n申请人：{name}\n被申请人：{employer}\n"
                            f"案由：{scenario['title']}\n\n"
                            f"事实与理由：{scenario['description']}\n"
                        ),
                        status=doc_status,
                        created_at=doc_dt,
                        updated_at=doc_dt,
                    )
                )

            if rng.random() < 0.4:
                q = rng.choice(RESEARCH_QUERIES)
                res_dt = case_dt + timedelta(days=rng.randint(2, 12))
                db.add(
                    ResearchReport(
                        owner_id=user.id,
                        case_id=case.id,
                        query=q,
                        report=(
                            f"【演示研究报告】针对问题：{q}\n"
                            f"结合{scenario['title']}，建议劳动者补充工资流水、考勤记录等证据，"
                            f"并在一年仲裁时效内提出申请。\n"
                            f"参考：《劳动合同法》《劳动争议调解仲裁法》相关条款。"
                        ),
                        sources_used=["demo_knowledge", "labor_contract_law"],
                        created_at=res_dt,
                    )
                )

        mat_count = rng.randint(2, 5)
        for filename, stage, source, note in rng.sample(VAULT_FILES, min(mat_count, len(VAULT_FILES))):
            content = (
                f"LaborAid 演示材料\n用户：{name}\n备注：{note}\n"
                f"生成时间：{datetime.now(timezone.utc).isoformat()}\n"
            ).encode("utf-8")
            dest, rel = vault_dest_path(user.id, filename)
            dest.write_bytes(content)
            mat_dt = created_at + timedelta(days=rng.randint(0, 20))
            db.add(
                UserMaterial(
                    user_id=user.id,
                    case_id=None,
                    source=source,
                    title=filename.replace(".txt", ""),
                    original_filename=filename,
                    stored_path=rel,
                    mime_type="text/plain",
                    size_bytes=len(content),
                    stage=stage,
                    tags=["demo", "labor"],
                    note=note,
                    created_at=mat_dt,
                    updated_at=mat_dt,
                )
            )
            vault_created += 1

    await db.commit()
    print("Done.")
    print(f"  Users:   +{users_created}")
    print(f"  Cases:   +{cases_created}")
    print(f"  Vault:   +{vault_created} material files")
    print(f"  Login:   demo001@{DEMO_DOMAIN} ... demo{count:03d}@{DEMO_DOMAIN}")
    print(f"  Password (all demo users): {DEMO_PASSWORD}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo users and sample data for admin dashboard")
    parser.add_argument("--count", type=int, default=45, help="Target number of demo users (default 45)")
    parser.add_argument("--clear", action="store_true", help="Remove all @demo.laboraid.local users first")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible data")
    args = parser.parse_args()

    if args.count < 1 or args.count > 200:
        print("--count must be between 1 and 200")
        sys.exit(1)

    rng = random.Random(args.seed)

    async with AsyncSessionLocal() as db:
        if args.clear:
            await clear_demo_data(db)
        await seed_demo_data(db, args.count, rng)


if __name__ == "__main__":
    asyncio.run(main())
