from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def gen_case002(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    title, text, small = _font(42), _font(28), _font(22)

    # 解除通知
    img = Image.new("RGB", (1180, 760), "#f3f4f6")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 36, 1110, 724), radius=12, fill="white", outline="#d1d5db", width=2)
    d.text((430, 74), "试用期解除通知", font=title, fill="#111827")
    d.text((110, 150), "收件人：周婷（运营专员）", font=text, fill="#374151")
    d.text((110, 196), "发件人：增长运营部", font=text, fill="#374151")
    d.text((110, 250), "通知时间：2026-04-26 10:12", font=text, fill="#111827")
    d.text((110, 304), "内容：试用期综合评估未达要求，今日办理离职。", font=text, fill="#111827")
    d.text((110, 350), "备注：请于当日17:30前完成设备与账号交接。", font=text, fill="#111827")
    d.text((110, 420), "附件：暂无书面考核表", font=text, fill="#dc2626")
    d.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img.save(base / "解除通知.png")

    # 工资发放记录
    img2 = Image.new("RGB", (1200, 760), "#f3f4f6")
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d2.text((420, 74), "工资发放记录", font=title, fill="#111827")
    d2.text((110, 140), "公司：启衡数字科技（杭州）有限公司", font=text, fill="#374151")
    d2.text((760, 140), "员工：周婷", font=text, fill="#374151")
    rows = [
        ("月份", "应发(元)", "实发(元)", "备注"),
        ("2026-02", "12000.00", "12000.00", "正常发放"),
        ("2026-03", "12000.00", "12000.00", "正常发放"),
        ("2026-04", "12000.00", "8800.00", "离岗当月按出勤"),
    ]
    y = 190
    for i, row in enumerate(rows):
        h = 58 if i == 0 else 74
        d2.rectangle((110, y, 1090, y + h), fill="#f9fafb" if i == 0 else "white", outline="#e5e7eb")
        d2.text((150, y + 18), row[0], font=text, fill="#111827")
        d2.text((390, y + 18), row[1], font=text, fill="#111827")
        d2.text((620, y + 18), row[2], font=text, fill="#111827" if i < 3 else "#dc2626")
        d2.text((850, y + 18), row[3], font=text, fill="#111827" if i == 0 else ("#dc2626" if i == 3 else "#111827"))
        y += h
    d2.text((110, 618), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img2.save(base / "工资发放记录.png")


def gen_case003(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    title, text, small = _font(42), _font(28), _font(22)

    # 调岗通知
    img = Image.new("RGB", (1180, 760), "#f3f4f6")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 36, 1110, 724), radius=12, fill="white", outline="#d1d5db", width=2)
    d.text((430, 74), "岗位调整通知", font=title, fill="#111827")
    d.text((110, 150), "员工：陈雯", font=text, fill="#374151")
    d.text((110, 196), "原岗位：客服主管", font=text, fill="#111827")
    d.text((110, 242), "新岗位：客服支持岗", font=text, fill="#111827")
    d.text((110, 288), "生效日期：2026-04-08", font=text, fill="#111827")
    d.text((110, 334), "薪资调整：15000 元/月 -> 9000 元/月", font=text, fill="#dc2626")
    d.text((110, 382), "调整原因：业务结构调整", font=text, fill="#111827")
    d.text((110, 620), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img.save(base / "调岗通知.png")

    # 工资对比明细
    img2 = Image.new("RGB", (1200, 760), "#f3f4f6")
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle((70, 40, 1130, 720), radius=12, fill="white", outline="#d1d5db", width=2)
    d2.text((420, 74), "工资对比明细", font=title, fill="#111827")
    d2.text((110, 140), "公司：禾木电子商务有限公司", font=text, fill="#374151")
    d2.text((760, 140), "员工：陈雯", font=text, fill="#374151")
    rows = [
        ("月份", "岗位", "税前工资(元)", "备注"),
        ("2026-02", "客服主管", "15000.00", "正常"),
        ("2026-03", "客服主管", "15000.00", "正常"),
        ("2026-04", "客服支持岗", "9000.00", "调岗后"),
    ]
    y = 190
    for i, row in enumerate(rows):
        h = 58 if i == 0 else 74
        d2.rectangle((110, y, 1090, y + h), fill="#f9fafb" if i == 0 else "white", outline="#e5e7eb")
        d2.text((150, y + 18), row[0], font=text, fill="#111827")
        d2.text((360, y + 18), row[1], font=text, fill="#111827")
        d2.text((620, y + 18), row[2], font=text, fill="#111827" if i < 3 else "#dc2626")
        d2.text((850, y + 18), row[3], font=text, fill="#111827")
        y += h
    d2.text((110, 618), "注：本文件用于案件流程与文书功能联调。", font=small, fill="#6b7280")
    img2.save(base / "工资对比明细.png")


def main() -> None:
    root = Path("f:/Undergraduate/Skill Learning/LaborAid/resources/test")
    gen_case002(root / "case-002-试用期辞退" / "materials" / "images")
    gen_case003(root / "case-003-孕期调岗降薪" / "materials" / "images")


if __name__ == "__main__":
    main()
