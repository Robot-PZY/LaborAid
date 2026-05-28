from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    base = Path(
        "f:/Undergraduate/Skill Learning/LaborAid/resources/test/case-001-工地欠薪/materials/images"
    )
    base.mkdir(parents=True, exist_ok=True)
    font_path = "C:/Windows/Fonts/msyh.ttc"
    title = ImageFont.truetype(font_path, 42)
    text = ImageFont.truetype(font_path, 28)
    small = ImageFont.truetype(font_path, 22)

    # wage slip png
    img = Image.new("RGB", (1200, 760), "#f3f4f6")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d.text((420, 70), "工资发放明细", font=title, fill="#111827")
    d.text((110, 140), "公司：华城建设劳务有限公司", font=text, fill="#374151")
    d.text((740, 140), "员工：李强", font=text, fill="#374151")

    y = 190
    rows = [
        ("月份", "应发(元)", "实发(元)", "备注"),
        ("2026-01", "8000.00", "0.00", "未发放"),
        ("2026-02", "8000.00", "0.00", "未发放"),
        ("2026-03", "8000.00", "0.00", "未发放"),
    ]
    for i, row in enumerate(rows):
        h = 58 if i == 0 else 74
        d.rectangle((110, y, 1090, y + h), fill="#f9fafb" if i == 0 else "white", outline="#e5e7eb")
        d.text((150, y + 18), row[0], font=text, fill="#111827")
        d.text((390, y + 18), row[1], font=text, fill="#111827")
        d.text((620, y + 18), row[2], font=text, fill="#dc2626" if i else "#111827")
        d.text((850, y + 18), row[3], font=text, fill="#dc2626" if i else "#111827")
        y += h

    d.text((110, 520), "合计应发：24000.00 元", font=text, fill="#111827")
    d.text((110, 565), "合计实发：0.00 元", font=text, fill="#dc2626")
    d.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img.save(base / "工资发放明细.png")

    # chat screenshot png
    img2 = Image.new("RGB", (900, 1600), "#ececec")
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((120, 20, 780, 1580), radius=36, fill="#f5f5f5", outline="#d1d5db", width=2)
    d2.rounded_rectangle((120, 20, 780, 108), radius=36, fill="white", outline="#d1d5db", width=1)
    d2.text((420, 52), "赵工", font=ImageFont.truetype(font_path, 40), fill="#111827")
    d2.text((350, 160), "2026-04-30 21:17", font=small, fill="#6b7280")

    d2.rounded_rectangle((160, 210, 520, 320), radius=14, fill="white", outline="#d1d5db")
    d2.text((180, 245), "赵工，1-3月工资还没结清。", font=text, fill="#111827")
    d2.text((180, 280), "家里要用钱，麻烦尽快安排。", font=text, fill="#111827")

    d2.rounded_rectangle((380, 370, 730, 480), radius=14, fill="#95ec69", outline="#84cc16")
    d2.text((402, 405), "我知道，这周先结一部分。", font=text, fill="#111827")
    d2.text((402, 440), "你先别着急。", font=text, fill="#111827")

    d2.text((350, 550), "2026-05-03 09:42", font=small, fill="#6b7280")

    d2.rounded_rectangle((160, 600, 520, 700), radius=14, fill="white", outline="#d1d5db")
    d2.text((182, 635), "月底又没到账，我准备走仲裁。", font=text, fill="#111827")

    d2.rounded_rectangle((350, 754, 730, 872), radius=14, fill="#95ec69", outline="#84cc16")
    d2.text((372, 790), "工程款还没下来，我明天对账。", font=text, fill="#111827")
    d2.text((372, 825), "你先等等。", font=text, fill="#111827")

    d2.text((315, 1515), "沟通记录截图（用于流程联调）", font=small, fill="#9ca3af")
    img2.save(base / "微信聊天截图.png")


if __name__ == "__main__":
    main()
