# -*- coding: utf-8 -*-
"""生成 REV.A 审查包 PDF：封面 + 原理图连接表 + 通道映射 + 预布局 + 管座 1:1 页 + ERC 摘要。

合并用 pypdf；封面与摘要页用 Pillow 渲染。
输出：docs/QS30-6_REV.A_审查包.pdf
"""
import datetime
import io
import os

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
DPI = 200.0
MM = DPI / 25.4
A4 = (int(round(210 * MM)), int(round(297 * MM)))
F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_CJKB = "C:/Windows/Fonts/msyhbd.ttc"


def font(pt, bold=False):
    return ImageFont.truetype(F_CJKB if bold else F_CJK, int(round(pt * DPI / 72.0)))


def page() -> Image.Image:
    return Image.new("RGB", A4, "white")


def wrap(d, s, f, w):
    out = []
    for para in str(s).split("\n"):
        cur = ""
        for ch in para:
            if d.textlength(cur + ch, font=f) > w and cur:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        out.append(cur)
    return out


def cover():
    img = page()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, A4[0], int(28 * MM)], fill=(20, 40, 70))
    d.text((int(14 * MM), int(7 * MM)), "QS30-6 REV.A 审查包", font=font(26, True),
           fill="white")
    d.text((int(14 * MM), int(18 * MM)),
           "六位静态辉光钟 · ESP32-S3-WROOM-1-N8 · 南昌 QS30-1 · 立创EDA 设计输入",
           font=font(12), fill=(220, 230, 245))
    y = int(38 * MM)
    lines = [
        ("项目", "QS30-6 REV.A（PCB 修订 A，尚未投板）"),
        ("状态", "HOLD —— 可继续预布局/实物验证，禁止投板与生产放行"),
        ("生成日期", datetime.date.today().isoformat()),
        ("工程规模", "227 器件 / 736 引脚 / 172 网络 / 60 路数字阴极 / 2×HV5622(64 路)"),
        ("自动检查", "19 项网表级一致性检查 PASS（0 ERROR / 0 WARN），见 docs/erc_report.md"),
        ("高压工作点", "HV_BUS 172.18 V；OVP 198.8 V（独立硬件 + 锁存 + 受控复位）；Ra=20 kΩ/管"),
        ("升压仿真", "功率级 SPICE（仓库自带 minispice，已执行：171.99 V vs 解析 171.95 V，纹波 8.7 mVpp，效率 95.8%）+ 闭环行为模型 S1–S10（Ts/80 收敛）"),
        ("SPICE 边界", "厂商 ngspice/LTspice 未安装；sim/boost_uc3843.cir 未执行，已如实标注"),
        ("待关闭", "H01–H09 全部未关闭；其中 H02/H03/H04/H05/H06/H07 阻止投板"),
    ]
    for k, v in lines:
        d.text((int(14 * MM), y), k, font=font(11, True), fill=(20, 40, 70))
        for i, ln in enumerate(wrap(d, v, font(11), int(178 * MM))):
            d.text((int(48 * MM), y + i * int(6 * MM)), ln, font=font(11), fill=(20, 20, 20))
        y += max(1, len(wrap(d, v, font(11), int(178 * MM)))) * int(6 * MM) + int(4 * MM)

    y += int(4 * MM)
    d.text((int(14 * MM), y), "本包内容与阅读顺序", font=font(13, True), fill=(20, 40, 70))
    y += int(8 * MM)
    toc = [
        "1. 系统框图 / 电源树 / 安全使能链（1 页）",
        "2. 分页连接表式原理图（9 页：P1 电源、P2 MCU/USB、P3 驱动/电平/门控、P4 升压/OVP、P5 管座、P6 测试点，含续页）",
        "3. 60 路数字阴极通道映射表（1 页，含 PQFP 引脚与串行位序假设）",
        "4. PCB 预布局与分区/禁布约束（1 页）",
        "5. QS30-1 管座 1:1 校对页（A4，300 dpi，须按“实际大小/100%”打印）",
        "6. ERC / 一致性检查摘要（1 页）",
        "7. DRC 预检摘要（网表级 10 项，1 页）",
        "8. SPICE 验证摘要（minispice：解析解自检 + 升压功率级，1 页）",
        "9. HOLD 证据状态（10 个证据模板 + 自动校验，1 页）",
        "10. HOLD 进度看板（填写进度 + 关键路径，1 页）",
        "11. HOLD 签署与关闭联动（自动证据 + 人工签审，1 页）",
        "12. 环路参数敏感性扫描（27 组，供 H06 补偿调整，1 页）",
        "13. OVP 时序回归（复位脉宽/锁存保持，1 页）",
        "14. 测试计划 ↔ 证据一致性（37 项，1 页）",
        "15. 固件约束清单（8 控制脚/64 位帧/13 条约束，1 页）",
        "16. 文档关键数字一致性（5 项检查，1 页）",
        "17. BOM 选型复核（14 关键件，1 页）",
        "18. 热与浪涌复核（HV5622/PPTC，1 页）",
        "19. 投板前检查清单（RELEASE BLOCKED，1 页）",
        "20. 总交接页（交付物索引 / 证据分级 / 复现验证，1 页）",
    ]
    for t in toc:
        for ln in wrap(d, t, font(10.5), int(178 * MM)):
            d.text((int(18 * MM), y), ln, font=font(10.5), fill=(30, 30, 30))
            y += int(5.5 * MM)
        y += int(2 * MM)

    y += int(4 * MM)
    d.text((int(14 * MM), y), "签名 / 版本", font=font(13, True), fill=(20, 40, 70))
    y += int(8 * MM)
    for ln in ["设计：________________    日期：__________",
               "复核：________________    日期：__________",
               "文件版本：REV.A r1        审查结论：______________________"]:
        d.text((int(18 * MM), y), ln, font=font(11), fill=(30, 30, 30))
        y += int(8 * MM)
    return img


def md_page(path, title, note):
    img = page()
    d = ImageDraw.Draw(img)
    d.text((int(14 * MM), int(12 * MM)), title, font=font(17, True), fill=(20, 40, 70))
    y = int(24 * MM)
    f_n = font(9.0)
    if os.path.exists(path):
        for line in open(path, encoding="utf-8").read().splitlines():
            if not line.strip():
                y += int(1.6 * MM)
                continue
            line = line.replace("**", "").replace("`", "")
            if line.startswith("#"):
                d.text((int(14 * MM), y), line.lstrip("# "), font=font(11.5, True),
                       fill=(20, 40, 70))
                y += int(6 * MM)
                continue
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if set("".join(cells)) <= set("-: "):
                    continue
                txt = " | ".join(cells)
            else:
                txt = line
            for ln in wrap(d, txt, f_n, int(180 * MM)):
                d.text((int(16 * MM), y), ln, font=f_n, fill=(20, 20, 20))
                y += int(4.3 * MM)
            if y > int(276 * MM):
                break
    d.text((int(14 * MM), int(283 * MM)), note, font=font(8.5), fill=(150, 60, 60))
    return img


def erc_summary():
    return md_page(os.path.join(DOC, "erc_report.md"),
                   "ERC / 一致性检查摘要（网表级）",
                   "以上为 design/build.py 生成的网表级检查；立创EDA 原生 ERC/DRC 尚未执行（H09）。")


def drc_summary():
    return md_page(os.path.join(DOC, "drc_precheck.md"),
                   "DRC 预检摘要（网表级，10 项）",
                   "这不是立创EDA 原生 DRC；布线间距/孔径/天线禁布/爬电距离仍须在 EDA 中执行（H07/H09）。")


def evidence_summary():
    return md_page(os.path.join(DOC, "hold_closure_report.md"),
                   "HOLD 证据状态（证据模板 + 自动校验）",
                   "当前无实物数据，0/7 已提交；框架已用合成数据自测（docs/evidence_selftest.md）。"
                   "自动校验通过后仍需 HOLD_REGISTER 人工签署。")


def dashboard_summary():
    return md_page(os.path.join(DOC, "hold_dashboard.md"),
                   "HOLD 进度看板（填写进度 + 关键路径）",
                   "由 design/hold_dashboard.py 自动统计；当前 0/7 已提交（无实物数据），"
                   "关键路径 H03 → PCB 封装冻结、H02/H06 → 高压验证、H04 → 固件 LUT。")


def thermal_summary():
    return md_page(os.path.join(DOC, "thermal_review.md"),
                   "热与浪涌复核（HV5622 温升 / PPTC 浪涌）",
                   "器件参数未核实处全部用区间表达：温升 0.7–6.3 °C、I²t 0.0010 A²s（预期 PPTC 不误动）。")


def handover_summary():
    return md_page(os.path.join(DOC, "HANDOVER.md"),
                   "总交接页（交付物索引 / 证据分级 / HOLD 解除路径）",
                   "先读此页：软件侧完成并可从零复现；实物侧 0/9 HOLD 关闭 → 禁止投板/下单。")


def preflight_summary():
    return md_page(os.path.join(DOC, "preflight_checklist.md"),
                   "投板前检查清单（自动汇总 → RELEASE BLOCKED）",
                   "机器检查 11/11 PASS，但 HOLD CLOSED 0/9 → 不得投板/下单/Gerber；"
                   "放行须人工签署 + 原生 EDA ERC/DRC。")


def bom_summary():
    return md_page(os.path.join(DOC, "bom_review.md"),
                   "BOM 选型复核（关键器件降额/替代料）",
                   "14 个关键器件 5/5 PASS；U20 封装待冻结（WARN）；本表不是可下单 BOM。")


def firmware_summary():
    return md_page(os.path.join(DOC, "firmware_constraints.md"),
                   "固件约束清单（从设计数据库派生）",
                   "GPIO/网络名不手写：由 design/firmware_constraints.py 从网表+映射表反查；"
                   "位序 H04 实测前为 PROVISIONAL。")


def doccons_summary():
    return md_page(os.path.join(DOC, "doc_consistency.md"),
                   "文档关键数字一致性（防跨文档漂移）",
                   "单一事实来源=机器可读结果（design_summary/spice_validation/drc/test_plan）；本轮抓到并修正 4 处漂移。")


def ovp_timing_summary():
    return md_page(os.path.join(DOC, "ovp_timing.md"),
                   "OVP 时序回归（复位脉宽 + 锁存保持）",
                   "行为级 SCR 等效：最小可靠复位脉宽 0.2 ms；不复位时 0.9 s 保持；"
                   "器件级时序仍须 H06 实测。")


def test_plan_summary():
    return md_page(os.path.join(DOC, "test_plan_check.md"),
                   "测试计划 ↔ 证据一致性（37 项，5 条规则）",
                   "由 design/test_plan_check.py 生成；5/5 PASS：序号/证据引用/无孤立证据/"
                   "阶段映射/文档防漂移。")


def loop_scan_summary():
    return md_page(os.path.join(DOC, "loop_scan.md"),
                   "环路参数敏感性扫描（供 H06 补偿调整）",
                   "PI 等效 ≠ UC3843 电流模式 Type-II 补偿；结论仅用于趋势与稳定边界，"
                   "R72/C56 最终值须 H06 实测相位裕度确定。")


def signoff_summary():
    return md_page(os.path.join(DOC, "hold_signoff_report.md"),
                   "HOLD 签署与关闭联动",
                   "CLOSED = 自动证据通过 且 签署齐全；证据未过却签 CLOSED 记为 VIOLATION。"
                   "当前 CLOSED 0 / OPEN 7 / MANUAL 2 / VIOLATION 0（无实物数据）。")


def spice_summary():
    return md_page(os.path.join(ROOT, "sim", "results", "spice_validation.md"),
                   "SPICE 验证摘要（仓库自带 minispice 求解器）",
                   "厂商 ngspice 网表仍未执行（环境无 ngspice）；功率级 SPICE 已由 minispice 执行并通过解析解自检。")


def img_to_pdf_bytes(img, dpi=DPI):
    b = io.BytesIO()
    img.save(b, "PDF", resolution=dpi)
    b.seek(0)
    return b


def main():
    out = os.path.join(DOC, "QS30-6_REV.A_审查包.pdf")
    w = PdfWriter()
    # 封面 + ERC 摘要
    for img in (cover(), erc_summary(), drc_summary(), spice_summary(),
                evidence_summary(), dashboard_summary(), signoff_summary(),
                loop_scan_summary(), ovp_timing_summary(),
                test_plan_summary(), bom_summary(), firmware_summary(),
                doccons_summary(), thermal_summary(), preflight_summary(),
                handover_summary()):
        r = PdfReader(img_to_pdf_bytes(img))
        for p in r.pages:
            w.add_page(p)
    # 现有 PDF
    parts = [
        os.path.join(DOC, "schematic", "QS30-6_REV.A_原理图连接表.pdf"),
        os.path.join(DOC, "prelayout", "QS30-6_REV.A_prelayout.pdf"),
        os.path.join(DOC, "footprint", "QS30-1_管座_1比1校对页.pdf"),
    ]
    for p in parts:
        if not os.path.exists(p):
            print("WARN missing:", p)
            continue
        r = PdfReader(p)
        for pg in r.pages:
            w.add_page(pg)
    with open(out, "wb") as f:
        w.write(f)
    n = len(PdfReader(out).pages)
    print(f"wrote {out}  pages={n}")


if __name__ == "__main__":
    main()
