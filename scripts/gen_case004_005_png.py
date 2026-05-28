from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def gen_case004(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    title, text, small = _font(42), _font(28), _font(22)

    img = Image.new("RGB", (1200, 760), "#f3f4f6")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d.text((390, 74), "微信入职沟通截图", font=title, fill="#111827")
    d.text((110, 150), "2025-11-17 20:13", font=text, fill="#6b7280")
    d.rounded_rectangle((110, 196, 840, 286), radius=12, fill="#ffffff", outline="#d1d5db")
    d.text((132, 228), "明天来金鸡湖店后厨先上班，合同后面补签。", font=text, fill="#111827")
    d.rounded_rectangle((260, 314, 1080, 404), radius=12, fill="#95ec69", outline="#84cc16")
    d.text((282, 346), "好的，我明早9点到店报到。", font=text, fill="#111827")
    d.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img.save(base / "入职沟通截图.png")

    img2 = Image.new("RGB", (1200, 760), "#f3f4f6")
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d2.text((390, 74), "工资转账记录", font=title, fill="#111827")
    rows = [
        ("日期", "摘要", "金额(元)", "渠道"),
        ("2025-12-30", "12月工资", "6500.00", "银行卡"),
        ("2026-01-31", "1月工资", "6500.00", "微信转账"),
        ("2026-02-28", "2月工资", "6200.00", "银行卡"),
        ("2026-03-31", "3月工资", "6500.00", "银行卡"),
    ]
    y = 150
    for i, row in enumerate(rows):
        h = 58 if i == 0 else 72
        d2.rectangle((110, y, 1090, y + h), fill="#f9fafb" if i == 0 else "white", outline="#e5e7eb")
        d2.text((150, y + 18), row[0], font=text, fill="#111827")
        d2.text((410, y + 18), row[1], font=text, fill="#111827")
        d2.text((650, y + 18), row[2], font=text, fill="#dc2626" if row[2] == "6200.00" else "#111827")
        d2.text((900, y + 18), row[3], font=text, fill="#111827")
        y += h
    d2.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img2.save(base / "工资转账记录.png")


def gen_case005(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    title, text, small = _font(42), _font(28), _font(22)

    img = Image.new("RGB", (1200, 760), "#f3f4f6")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d.text((400, 74), "作业现场照片说明", font=title, fill="#111827")
    d.rectangle((110, 150, 1090, 560), fill="#e5e7eb", outline="#9ca3af", width=2)
    d.text((180, 260), "2号月台 / 叉车尾板作业区域", font=_font(34), fill="#374151")
    d.text((180, 314), "事故时间：2026-05-07 22:35", font=text, fill="#374151")
    d.text((180, 360), "地面存在水渍，夜班照明较暗。", font=text, fill="#dc2626")
    d.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img.save(base / "作业现场照片.png")

    img2 = Image.new("RGB", (1200, 760), "#f3f4f6")
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d2.text((420, 74), "夜班排班截图", font=title, fill="#111827")
    rows = [
        ("日期", "班次", "岗位", "状态"),
        ("2026-05-06", "18:00-02:00", "搬运", "出勤"),
        ("2026-05-07", "18:00-02:00", "搬运", "出勤"),
        ("2026-05-08", "18:00-02:00", "搬运", "病休"),
        ("2026-05-09", "休息", "-", "休息"),
    ]
    y = 150
    for i, row in enumerate(rows):
        h = 58 if i == 0 else 72
        d2.rectangle((110, y, 1090, y + h), fill="#f9fafb" if i == 0 else "white", outline="#e5e7eb")
        d2.text((150, y + 18), row[0], font=text, fill="#111827")
        d2.text((390, y + 18), row[1], font=text, fill="#111827")
        d2.text((680, y + 18), row[2], font=text, fill="#111827")
        d2.text((900, y + 18), row[3], font=text, fill="#dc2626" if row[3] == "病休" else "#111827")
        y += h
    d2.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img2.save(base / "排班截图.png")


def main() -> None:
    root = Path("f:/Undergraduate/Skill Learning/LaborAid/resources/test")
    gen_case004(root / "case-004-未签合同二倍工资" / "materials" / "images")
    gen_case005(root / "case-005-工伤认定争议" / "materials" / "images")


if __name__ == "__main__":
    main()
