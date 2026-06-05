#!/usr/bin/env python3
"""E2E smoke test for case-001 (工地欠薪) via REST API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8010/api/v1"
CASE_DIR = Path(__file__).resolve().parents[1] / "resources" / "test" / "case-001-工地欠薪"

SUPPLEMENT = (
    "我是李强，2026年1月起在华城新区二期土建项目做钢筋工，与现场包工头赵建国口头约定月薪约8000元。"
    "2026年1–3月工资均未结清，累计约24000元。我仍在岗，多次微信催要，对方称工程款未下来。"
    "手中有微信催薪记录、工资发放明细图片和银行流水摘要，无书面劳动合同和完整考勤表。"
    "想确认先走劳动监察还是直接仲裁，以及如何准备申请书和证据清单。"
)

EVIDENCE_ITEMS = [
    ("微信催薪聊天记录", "electronic", "03-微信催薪记录.md"),
    ("工资发放明细", "documentary", "工资发放明细.svg"),
    ("银行流水摘要", "documentary", "04-银行流水摘要.md"),
]


def log(step: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    line = f"[{mark}] {step}"
    if detail:
        line += f" — {detail}"
    print(line, flush=True)


def main() -> int:
    if not CASE_DIR.is_dir():
        log("locate test data", False, str(CASE_DIR))
        return 1

    with httpx.Client(timeout=120.0) as client:
        # 1. Login
        r = client.post(f"{BASE}/auth/login", json={"email": "Admin", "password": "123456"})
        if r.status_code != 200:
            log("login", False, f"{r.status_code} {r.text[:200]}")
            return 1
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        log("login", True, "Admin")

        # 2. Structured intake (专项: 农民工 / 包工头欠薪)
        intake_payload = {
            "channel_id": "migrant-worker",
            "scenario_id": "wage_boss",
            "answers": {
                "work_region": "江苏省南京市",
                "industry": "建筑工地钢筋工",
                "employer_name": "华城建设劳务有限公司（现场包工头：赵建国）",
                "wage_amount": "24000",
                "wage_period": "2026年1月至2026年3月",
                "has_iou": "无",
                "still_employed": "是",
                "extra_notes": SUPPLEMENT,
            },
        }
        r = client.post(f"{BASE}/intake/structured", json=intake_payload, headers=headers)
        if r.status_code != 200:
            log("structured intake", False, f"{r.status_code} {r.text[:300]}")
            return 1
        plan = r.json()
        cause = plan.get("cause_type", "")
        log("structured intake", True, f"cause_type={cause}")
        if cause != "wage_arrears":
            log("cause check", False, f"expected wage_arrears, got {cause}")

        # 3. Create case
        create_payload = {
            "title": "李强诉华城建设劳务欠薪案",
            "case_type": "administrative_labor",
            "description": plan.get("summary") or SUPPLEMENT,
            "plaintiff": "李强",
            "defendant": "华城建设劳务有限公司（现场包工头：赵建国）",
            "cause_type": cause,
        }
        r = client.post(f"{BASE}/intake/create-case", json=create_payload, headers=headers)
        if r.status_code != 201:
            log("create case", False, f"{r.status_code} {r.text[:300]}")
            return 1
        case = r.json()
        case_id = case["id"]
        log("create case", True, f"id={case_id} title={case.get('title')}")

        # 4. Upload evidence
        uploaded = 0
        for title, ev_type, filename in EVIDENCE_ITEMS:
            fpath = CASE_DIR / filename
            if not fpath.exists():
                log(f"upload {filename}", False, "file missing")
                continue
            with fpath.open("rb") as fh:
                r = client.post(
                    f"{BASE}/evidence/quick-upload",
                    headers=headers,
                    data={"case_id": str(case_id), "title": title, "evidence_type": ev_type},
                    files={"file": (filename, fh, "application/octet-stream")},
                )
            if r.status_code not in (200, 201):
                log(f"upload {filename}", False, f"{r.status_code} {r.text[:200]}")
            else:
                uploaded += 1
                ev = r.json()
                log(f"upload {filename}", True, f"evidence_id={ev.get('id')}")
        if uploaded < 2:
            log("evidence uploads", False, f"only {uploaded} succeeded")
            return 1

        # 5. Readiness
        r = client.get(f"{BASE}/cases/{case_id}/readiness", headers=headers)
        if r.status_code == 200:
            rd = r.json()
            log("readiness", True, f"score={rd.get('score')} missing={len(rd.get('missing_items') or [])}")
        else:
            log("readiness", False, f"{r.status_code}")

        # 6. Evidence chain analysis (optional AI)
        r = client.post(f"{BASE}/evidence/chain-analysis/{case_id}", headers=headers, json={})
        if r.status_code == 200:
            ca = r.json()
            log("chain analysis", True, str(ca.get("summary", ca.get("message", ""))[:120]))
        else:
            log("chain analysis", False, f"{r.status_code} {r.text[:150]}")

        # 7. Doc pipeline (SSE)
        facts = create_payload["description"] or SUPPLEMENT
        with client.stream(
            "POST",
            f"{BASE}/cases/{case_id}/agent/doc-pipeline-stream",
            headers=headers,
            json={"doc_type": "application", "case_facts": facts, "skip_research": False},
            timeout=180.0,
        ) as stream:
            if stream.status_code != 200:
                body = stream.read().decode("utf-8", errors="replace")
                log("doc pipeline", False, f"{stream.status_code} {body[:300]}")
                return 1
            doc_id = None
            pipeline_error = None
            for line in stream.iter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    evt = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if evt.get("step") == "error":
                    pipeline_error = evt.get("error") or evt.get("label")
                if evt.get("status") == "completed" or evt.get("document_id"):
                    doc_id = evt.get("document_id") or doc_id
                if "document_id" in evt:
                    doc_id = evt["document_id"]
            if pipeline_error:
                log("doc pipeline", False, pipeline_error)
            elif doc_id:
                log("doc pipeline", True, f"document_id={doc_id}")
            else:
                log("doc pipeline", False, "no document_id in SSE stream")

        # 8. List documents for case
        r = client.get(f"{BASE}/documents", headers=headers, params={"case_id": case_id})
        if r.status_code == 200:
            docs = r.json()
            count = len(docs) if isinstance(docs, list) else len(docs.get("items", []))
            log("list documents", count > 0, f"count={count}")
        else:
            log("list documents", False, f"{r.status_code}")

        # 9. Vault materials linked to case
        r = client.get(f"{BASE}/vault", headers=headers, params={"case_id": case_id})
        if r.status_code == 200:
            vault = r.json()
            items = vault if isinstance(vault, list) else vault.get("items", [])
            log("vault materials", len(items) >= uploaded, f"count={len(items)}")
        else:
            log("vault", False, f"{r.status_code}")

        print(f"\nCase ID for manual check: {case_id}", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
