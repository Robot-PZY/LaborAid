"""Test export pipeline with a mock document."""
import asyncio
from pathlib import Path
from types import SimpleNamespace


def make_mock_doc():
    return SimpleNamespace(
        id=999,
        title="2026.6.9 拖欠工资维权-劳动仲裁申请书",
        type="application",
        content="""# 劳动仲裁申请书

## 一、仲裁请求

1. 请求支付拖欠工资 24000 元

## 二、事实与理由

申请人于2023年3月入职被申请人处，担任钢筋工，月工资8000元。被申请人自2026年1月起拖欠工资，至今未支付。

依据《中华人民共和国劳动合同法》第三十条、第八十五条规定，用人单位应当按时足额支付劳动报酬。

## 落款

此致

南京市劳动人事争议仲裁委员会

申请人：（签名）
2026年6月9日
""",
        ai_metadata={"structured_payload": {}},
        exported_path=None,
        owner_id=1,
    )


async def test_export():
    doc = make_mock_doc()
    output_dir = Path("f:/Undergraduate/Skill Learning/LaborAid/LaborAid/backend/test_exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test 1: HTML export
    print("=== Test 1: HTML Export ===")
    try:
        from app.services.docgen.html_export import export_to_html
        result = await export_to_html(doc, output_dir)
        print(f"OK: {result}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Word export (html mode)
    print("\n=== Test 2: Word Export (html mode) ===")
    try:
        from app.services.docgen.word_export import export_to_docx
        result = await export_to_docx(doc, output_dir)
        print(f"OK: {result}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: PDF export
    print("\n=== Test 3: PDF Export ===")
    try:
        from app.services.docgen.pdf_export import export_to_pdf
        result = await export_to_pdf(doc, output_dir)
        print(f"OK: {result}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


asyncio.run(test_export())
