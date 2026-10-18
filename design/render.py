# -*- coding: utf-8 -*-
"""Render QS30-6 REV.A review figures:
  * system block diagram            (docs/schematic/QS30-6_REV.A_系统框图.png)
  * per-sheet connection sheets     (docs/schematic/sheet_XX.png)
  * 60-channel drive mapping table  (docs/schematic/通道映射表.png)
  * PCB pre-layout zone map         (docs/prelayout/QS30-6_REV.A_prelayout.png)
and bind everything into PDFs.

The connection sheets are generated from the SAME python netlist model that
produced the CSV netlist, so figure and netlist cannot diverge.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import sheet_lv
import sheet_hv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_SCH = os.path.join(ROOT, "docs", "schematic")
OUT_LAY = os.path.join(ROOT, "docs", "prelayout")
os.makedirs(OUT_SCH, exist_ok=True)
os.makedirs(OUT_LAY, exist_ok=True)

# A3 landscape @ 6 px/mm  (420 x 297 mm)  -> print at 6 px/mm = 152 dpi
W, H = 2520, 1782
PXMM = 6.0

F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_CJKB = "C:/Windows/Fonts/msyhbd.ttc"
F_MONO = "C:/Windows/Fonts/consola.ttf"
if not os.path.exists(F_MONO):
    F_MONO = "C:/Windows/Fonts/arial.ttf"


def font(size, bold=False, mono=False):
    p = F_MONO if mono else (F_CJKB if bold else F_CJK)
    return ImageFont.truetype(p, size)


INK = (25, 25, 25)
GRAY = (120, 120, 120)
LIGHT = (235, 235, 235)
BLUE = (0, 70, 160)
RED = (170, 20, 20)
ORANGE = (190, 90, 0)
GREEN = (20, 110, 50)
PURPLE = (110, 40, 140)

NET_COLOR = {"HV": RED, "DRV": ORANGE, "POWER": BLUE, "DIFF": PURPLE,
             "SIGNAL": GREEN, "GND": GRAY}

SHEET_TITLES = {
    "01_PWR": "01  电源输入与保护 / 12V-5V-3.3V / DRV_VDD 负载开关",
    "02_MCU": "02  ESP32-S3-WROOM-1-N8 与 USB-C / UART0 / 按键接口",
    "03_DRV": "03  HV5622 高压驱动 x2 / 3.3V→DRV_VDD 电平转换 / 监控与门控",
    "04_HV": "04  12V→172V 升压 / 独立硬件过压保护与锁存",
    "05_TUBE": "05  六组 QS30-1 管座与阳极限流",
    "06_TP": "06  测试点与扩展接口",
}
SHEET_ORDER = ["01_PWR", "02_MCU", "03_DRV", "04_HV", "05_TUBE", "06_TP"]


def new_page(title, subtitle="", sheet=""):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([28, 28, W - 28, H - 28], outline=INK, width=3)
    d.rectangle([28, 28, W - 28, 108], outline=INK, width=2)
    d.text((52, 44), "QS30-6 REV.A", font=font(26, bold=True), fill=INK)
    d.text((300, 50), title, font=font(24, bold=True), fill=INK)
    if subtitle:
        d.text((52, 82), subtitle, font=font(15), fill=GRAY)
    # footer
    d.line([28, H - 96, W - 28, H - 96], fill=INK, width=2)
    d.text((52, H - 84), "QS30-6 REV.A  |  立创EDA 设计输入  |  状态: HOLD "
           "（禁止投板/生产放行）  |  生成脚本 design/render.py",
           font=font(14), fill=GRAY)
    if sheet:
        d.text((W - 420, H - 84), f"sheet {sheet}", font=font(14), fill=GRAY)
    return img, d


def text_len(d, s, f):
    try:
        return d.textlength(s, font=f)
    except Exception:
        return len(s) * 8


def wrap(d, s, f, maxw):
    out = []
    for para in str(s).split("\n"):
        cur = ""
        for ch in para:
            if d.textlength(cur + ch, font=f) > maxw and cur:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        out.append(cur)
    return out


# ---------------------------------------------------------------------------
def block_diagram():
    img, d = new_page("系统框图 / 电源树 / 安全使能链",
                      "粗线=功率路径，细线=信号；标号为原理图网络名。"
                      "所有门控在硬件中建立默认关断状态。", "BLOCK")
    boxes = {}
    # (x0,y0,x1,y1) in px on A3 canvas
    def box(key, x0, y0, x1, y1, title, sub="", fill=(246, 246, 250)):
        d.rounded_rectangle([x0, y0, x1, y1], 10, fill=fill, outline=INK, width=2)
        d.text((x0 + 12, y0 + 8), title, font=font(17, bold=True), fill=INK)
        if sub:
            yy = y0 + 32
            for line in wrap(d, sub, font(13), x1 - x0 - 24):
                d.text((x0 + 12, yy), line, font=font(13), fill=GRAY)
                yy += 17
        boxes[key] = (x0, y0, x1, y1)

    def arrow(p, q, color=INK, width=3):
        d.line([p, q], fill=color, width=width)
        # arrow head at q
        import math
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        L, A = 14, 0.42
        d.polygon([q,
                   (q[0] - L * math.cos(ang - A), q[1] - L * math.sin(ang - A)),
                   (q[0] - L * math.cos(ang + A), q[1] - L * math.sin(ang + A))],
                  fill=color)

    def lab(x, y, s, color=GRAY, size=13):
        d.text((x, y), s, font=font(size, mono=True), fill=color)

    box("in", 70, 150, 330, 250, "J1 12 V DC 输入",
        "F1 PPTC 1.5 A / D1 SMBJ16A TVS / D2 SS54 反接保护", (255, 250, 240))
    box("p12", 380, 150, 640, 250, "EXT12 保护后 12 V",
        "供：5V buck / DRV_VDD 开关 / 升压开关", (240, 246, 255))
    box("b5", 700, 140, 980, 240, "U1 TPS54202 12V→5.08V/2A",
        "L1 10µH · C6 22µF · EN UVLO≈4.8 V", (240, 246, 255))
    box("or", 1040, 140, 1320, 240, "D3/D4 双肖特基 OR",
        "EXT5 / VBUS → 5V_SYS，反向阻断，无回灌", (240, 246, 255))
    box("b3", 1380, 140, 1660, 240, "U2 SY8089A 5V→3.315V/2A",
        "L2 2.2µH · C11 22µF · 3.3 V 预算 800 mA", (240, 246, 255))
    box("mcu", 1750, 110, 2430, 300, "U10 ESP32-S3-WROOM-1-N8",
        "GPIO11/12/14 = DIN/CLK/LAT · GPIO15 = DISP_ALLOW · "
        "GPIO16 = HV_EN_REQ · GPIO1 = HV_SENSE · GPIO7 = HV_FAULT_N · "
        "GPIO19/20 = USB D-/D+ · GPIO43/44 = UART0 · 天线端伸出板边 + 禁布区",
        (238, 252, 240))
    box("usb", 1040, 330, 1400, 470, "J2 USB-C 16P (2.0 device)",
        "CC1/CC2 5.1 kΩ · U11 USBLC6-2SC6 ESD · 22 Ω 串联 · "
        "VBUS 仅逻辑下载", (245, 240, 255))
    box("mon", 700, 520, 1120, 700, "电源监控 + 硬件使能门控",
        "U5/U8 LM393 + U6 TL431(2.5 V) + U7 74HC08\n"
        "EXT12_PG(11.0 V) · 3V3_PG(3.11 V) · DRV_PG(10.41 V) · FAULT_OK\n"
        "DRV_VDD_EN = EXT12_PG·3V3_PG·HV_EN_REQ\n"
        "HV_EN = DRV_PG·FAULT_OK·HV_EN_REQ", (252, 250, 235))
    box("sw", 120, 520, 480, 680, "Q1 DRV_VDD 高边开关",
        "默认关断（栅极 100 kΩ 上拉到 EXT12）\n"
        "DRV_VDD ≈ 11.5 V → HV5622 VDD", (252, 245, 240))
    box("ls", 1530, 520, 1900, 700, "U3/U4 CD40109B 电平转换",
        "3.3 V → 12 V：DIN/CLK/LAT/ALLOW + HV_EN_REQ\n"
        "VCC=3V3, VDD=DRV_VDD；EN=3V3，3V3 失电即高阻\n"
        "12 V 域全部 10 kΩ 下拉（BL 低=消隐）", (252, 245, 240))
    box("drv", 1980, 520, 2430, 720, "U21/U22 HV5622 (PQFP-44) x2",
        "32+32=64 路开漏，60 路用于 6×10 数字阴极\n"
        "VDD=DRV_VDD · POL≡DRV_VDD · BL 低=全关\n"
        "DATA 级联：U21→U22，帧长 64 bit", (255, 240, 240))
    box("boost", 120, 820, 560, 1040, "12 V → 172 V 升压 (U20 UC3843)",
        "fsw≈78 kHz · L20 220 µH (Isat≥5 A) · Q20 IRF740 · D20 UF4007\n"
        "C50/C51 20 µF/250 V · R67/R68 200 kΩ 泄放（172→50 V≈3.8 s）\n"
        "HV_EN → Q26/Q27 高边开关（默认关断）", (255, 240, 240))
    box("ovp", 620, 820, 1060, 1040, "独立硬件过压保护 / 锁存",
        "U23 LM393 + U24 TL431 · 门限 198.8 V (2.5 V·1519.1/19.1)\n"
        "OVP_SET → Q21/Q22 分立 SCR 锁存 → Q23 拉低 COMP,\n"
        "Q24 拉低 HV_FAULT_N；Q25 由 GPIO18 受控复位", (255, 240, 240))
    box("hv", 1120, 820, 1560, 1040, "HV_BUS 172 V",
        "C50/C51/C52 · 反馈 2×750 k/22.1 k\n"
        "R27/R28 1 MΩ×2 分压 → ADC1_CH0（1.70 V @172 V）",
        (255, 240, 240))
    box("anode", 1620, 820, 2040, 1040, "六路阳极限流",
        "每管 2×10 kΩ/2 W 串联 = 20 kΩ\n"
        "正常工作 ≈2.35 mA；单管短路耗散 ≈1.45 W", (255, 240, 240))
    box("tubes", 2100, 820, 2430, 1040, "J31..J36 QS30-1 管座",
        "13 脚 1:1 映射；1/8 脚不接\n"
        "阴极 → HV5622 HVOUT（60 路）", (255, 240, 240))

    # power arrows
    arrow((330, 200), (380, 200)); arrow((640, 190), (700, 190))
    arrow((980, 190), (1040, 190)); arrow((1320, 190), (1380, 190))
    arrow((1660, 210), (1750, 210), BLUE, 4)
    lab(1345, 205, "3V3", BLUE)
    arrow((1150, 330), (1150, 240), BLUE, 4)
    lab(1160, 280, "VBUS", BLUE)
    arrow((190, 250), (190, 520))            # EXT12 -> DRV switch
    arrow((330, 250), (380, 250))
    lab(300, 255, "EXT12", BLUE)
    arrow((700, 640), (484, 640), GREEN)
    lab(520, 620, "DRV_VDD_EN", GREEN)
    d.line([(900, 700), (900, 790)], fill=GREEN, width=3)
    arrow((900, 790), (560, 790), GREEN)
    lab(620, 770, "HV_EN", GREEN)
    arrow((340, 680), (340, 820)); lab(350, 730, "EXT12", BLUE)
    arrow((560, 930), (620, 930))
    arrow((1060, 930), (1120, 930)); arrow((1560, 930), (1620, 930))
    arrow((2040, 930), (2100, 930))
    lab(1160, 900, "172 V", RED)
    # signal arrows mcu -> level shift -> driver
    arrow((1820, 300), (1820, 518), GREEN)
    lab(1400, 330, "DISP_DIN/CLK/LAT/ALLOW", GREEN)
    arrow((1900, 620), (1980, 620), ORANGE)
    lab(1905, 600, "DRV_*", ORANGE)
    lab(1400, 700, "DRV_PG/FAULT_OK 在门控内使用", GRAY, 12)
    arrow((2200, 300), (2200, 518), GREEN)
    lab(2210, 400, "HV_EN_REQ", GREEN)
    # driver -> tubes
    arrow((2430, 700), (2430, 790), RED)
    d.text((1500, 1120), "注：DRV_VDD / HV_BUS / 阴极网络按 HV 或 DRV 网络类别设置 PCB 规则；"
           "天线禁布区与高压区间距见预布局图（H07/H08 未关闭）。",
           font=font(15), fill=GRAY)
    d.text((1500, 1150), "帧长由 96 bit（3 片）修正为 64 bit（2 片，32×2），"
           "详见 REV_A_CHANGELOG.md。", font=font(15), fill=RED)
    p = os.path.join(OUT_SCH, "QS30-6_REV.A_系统框图.png")
    img.save(p)
    return p, img


# ---------------------------------------------------------------------------
def connection_sheets():
    design, nclass = model.DESIGN, model.NET_CLASS
    pages, paths = [], []
    for sid in SHEET_ORDER:
        parts = [p for p in design.values() if p.sheet == sid]
        img, d = new_page(SHEET_TITLES[sid],
                          "连接表式原理图：每引脚列出 引脚号/名称 → 网络。网络颜色 红=HV 橙=DRV_VDD域 "
                          "蓝=电源 紫=USB差分 绿=信号 灰=GND。与 CSV 网表同源生成。",
                          sid)
        margin, gap = 52, 14
        full_w = W - 2 * margin
        col_w = (full_w - 2 * gap) // 3
        col_top, col_bot = 132, H - 132

        def part_box(p, bw, bh, x0, y0, ncols):
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 6, outline=INK,
                                width=2, fill=(252, 252, 252))
            d.text((x0 + 8, y0 + 5), f"{p.ref}  {p.mpn}",
                   font=font(14, bold=True), fill=INK)
            d.text((x0 + 8, y0 + 24), f"[{p.pkg}] {p.val}  {p.status}",
                   font=font(11), fill=GRAY)
            if "DNP" in p.flags:
                d.text((x0 + bw - 66, y0 + 5), "[DNP]", font=font(12, bold=True),
                       fill=RED)
            d.line([x0 + 6, y0 + 40, x0 + bw - 6, y0 + 40], fill=LIGHT)
            pins = list(p.rows())
            rows = (len(pins) + ncols - 1) // ncols
            inw = bw // ncols
            for i, (pin, name, net) in enumerate(pins):
                ci, ri = divmod(i, rows)
                cx = x0 + 6 + ci * inw
                cy = y0 + 44 + ri * 18
                d.text((cx, cy), f"{pin:>3}", font=font(11, mono=True), fill=GRAY)
                d.text((cx + 30, cy), name[:18], font=font(11, mono=True), fill=INK)
                nx = cx + 30 + int(text_len(d, name[:18], font(11, mono=True))) + 8
                if net == "NC":
                    d.text((nx, cy), "NC", font=font(11, mono=True), fill=GRAY)
                else:
                    col = NET_COLOR.get(nclass.get(net, "SIGNAL"), INK)
                    d.text((nx, cy), net, font=font(12, bold=True), fill=col)

        col_y = [col_top, col_top, col_top]
        for p in parts:
            npin = len(p.pins)
            ncols = 1 if npin <= 12 else (2 if npin <= 30 else 3)
            wide = npin > 30
            bw = full_w if wide else col_w
            rows = (npin + ncols - 1) // ncols
            bh = 50 + rows * 18
            if wide:
                ytop = max(col_y)
                if ytop + bh > col_bot:
                    pages.append(img)
                    img, d = new_page(SHEET_TITLES[sid] + "（续）", "", sid)
                    col_y = [col_top, col_top, col_top]
                    ytop = col_top
                part_box(p, bw, bh, margin, ytop, ncols)
                col_y = [ytop + bh + gap] * 3
            else:
                ci = min(range(3), key=lambda i: col_y[i])
                if col_y[ci] + bh > col_bot:
                    pages.append(img)
                    img, d = new_page(SHEET_TITLES[sid] + "（续）", "", sid)
                    col_y = [col_top, col_top, col_top]
                    ci = 0
                part_box(p, bw, bh, margin + ci * (col_w + gap), col_y[ci], ncols)
                col_y[ci] += bh + gap
        pages.append(img)
        paths.append(sid)
    return pages, paths


# ---------------------------------------------------------------------------
def channel_table():
    img, d = new_page("60 路数字阴极通道映射表",
                      "管位→显示数字→QS30-1 物理脚号→驱动器输出→PQFP 引脚→串行位序。"
                      "串行位序为假设约定，必须用 walking-one 实测确认。", "MAP")
    x0, y0 = 52, 130
    cols = [70, 55, 70, 165, 145, 75, 95, 70, 95]
    heads = ["管位", "数字", "QS30脚", "阴极网络", "逻辑通道", "器件",
             "输出", "PQFP脚", "串行位"]
    cw = [max(text_len(d, h, font(14, bold=True)) + 26, c) for h, c in zip(heads, cols)]
    row_h = 24
    y = y0
    d.rectangle([x0, y, x0 + sum(cw), y + row_h], fill=(225, 230, 240))
    x = x0
    for h, w in zip(heads, cw):
        d.text((x + 8, y + 4), h, font=font(14, bold=True), fill=INK)
        x += w
    y += row_h
    # 64 rows in two blocks of 32
    rows = []
    for t in range(1, 7):
        for dg in range(10):
            ch = sheet_hv.channel(t, dg)
            rows.append((f"J_T{t}", dg, sheet_hv.TUBE_DIGIT_PIN[dg],
                         sheet_hv.cathode_net(t, dg), ch,
                         sheet_hv.device_of(ch),
                         f"HVOUT{sheet_hv.hvout_of(ch)}",
                         sheet_hv.HVOUT_PIN[sheet_hv.hvout_of(ch)],
                         63 - ch, "used"))
    for ch in range(60, 64):
        rows.append(("备用", "-", "-", "NC", ch, sheet_hv.device_of(ch),
                     f"HVOUT{sheet_hv.hvout_of(ch)}",
                     sheet_hv.HVOUT_PIN[sheet_hv.hvout_of(ch)], 63 - ch, "spare"))
    half = 32
    for block in range(2):
        bx = x0 + block * (sum(cw) + 80)
        y = y0 + row_h
        for r in rows[block * half:(block + 1) * half]:
            if r[9] == "spare":
                d.rectangle([bx, y, bx + sum(cw), y + row_h], fill=(245, 230, 230))
            for i, (v, w) in enumerate(zip(r[:9], cw)):
                col = RED if i == 3 else INK
                d.text((bx + 8 + sum(cw[:i]), y + 4), str(v),
                       font=font(13, mono=(i in (3,))), fill=col)
            d.line([bx, y + row_h, bx + sum(cw), y + row_h], fill=LIGHT)
            y += row_h
        d.rectangle([bx, y0 + row_h, bx + sum(cw), y], outline=INK, width=1)
    d.text((52, 1000), "说明：通道 = (管位-1)×10 + 数字；CH0..31 → U21，CH32..63 → U22；"
           "HVOUT 与 PQFP 引脚按 Microchip DS20005854A Table 2-1（HVOUT1=pin22 … "
           "HVOUT22=pin1, HVOUT23=pin44 … HVOUT32=pin35）。", font=font(14), fill=GRAY)
    d.text((52, 1030), "串行位假设：64 bit 帧按 bit0 先发，bit_j = CH(63-j)；"
           "实际近端/远端与字节位序须用单通道 walking-one 测试确定，"
           "不得用软件数组掩盖镜像。", font=font(14), fill=RED)
    p = os.path.join(OUT_SCH, "QS30-6_REV.A_通道映射表.png")
    img.save(p)
    return p, img


# ---------------------------------------------------------------------------
def prelayout():
    # board 230 x 120 mm, canvas 6 px/mm + margins
    MM = 6
    BW, BH = 230, 120
    pad = 110
    Wp, Hp = BW * MM + 2 * pad, BH * MM + 2 * pad + 120
    img = Image.new("RGB", (Wp, Hp), "white")
    d = ImageDraw.Draw(img)
    ox, oy = pad, pad

    def P(x, y):
        return (ox + x * MM, oy + y * MM)

    d.text((30, 24), "QS30-6 REV.A  PCB 预布局（PROVISIONAL — 不得据此投板）",
           font=font(26, bold=True), fill=INK)
    d.text((30, 58), "230 × 120 mm 建议外形；按交接文件 6 页划分。"
           "管座坐标、天线禁布与 HV 间距分别受 H03/H08/H07 阻塞。",
           font=font(14), fill=GRAY)
    # board outline
    d.rounded_rectangle([P(0, 0), P(BW, BH)], 24, outline=INK, width=3,
                        fill=(252, 252, 250))

    def zone(x0, y0, x1, y1, title, sub, fill):
        d.rectangle([P(x0, y0), P(x1, y1)], outline=(150, 150, 150), fill=fill)
        d.text((P(x0, y0)[0] + 6, P(x0, y0)[1] + 5), title,
               font=font(15, bold=True), fill=INK)
        yy = P(x0, y0)[1] + 24
        for line in wrap(d, sub, font(12), (x1 - x0) * MM - 12)[:6]:
            d.text((P(x0, y0)[0] + 6, yy), line, font=font(12), fill=GRAY)
            yy += 15

    # tube row along top
    zone(14, 4, 216, 46, "Z5  六组 QS30-1 管座区（J31..J36）",
         "管座中心距 = 36 mm 占位（φ30.2 玻壳 + 插拔/散热间隙），"
         "需按 H03 实测管座与 H07 高压间距冻结；每管阳极 20 kΩ/2 W 就近布置。",
         (255, 244, 240))
    for i in range(6):
        cx = 25 + 36 * i
        d.ellipse([P(cx - 14, 27 - 14), P(cx + 14, 27 + 14)], outline=(170, 60, 60),
                  width=2)
        d.ellipse([P(cx - 6.0, 27 - 6.0), P(cx + 6.0, 27 + 6.0)],
                  outline=(170, 60, 60), width=2)
        d.text((P(cx - 12, 40)[0], P(cx - 12, 40)[1]), f"J_T{i+1}",
               font=font(11, bold=True), fill=(140, 40, 40))
    # HV power left-bottom
    zone(4, 48, 86, 112, "Z4  12V→172V 升压 + OVP + DRV_VDD 开关",
         "HV 回路（L20/Q20/D20/C50）保持最小环路面积；"
         "OVP/锁存紧邻；与 Z1/Z2 之间加 2 mm 隔离槽 + 禁布。", (255, 238, 238))
    # drivers centre
    zone(90, 48, 150, 96, "Z3  HV5622 x2（U21/U22）",
         "两片 PQFP-44 靠近管座，HVOUT 扇出到 60 路阴极；"
         "下方为地平面参考，不得跨越分割。", (255, 244, 238))
    # MCU right
    zone(168, 48, 226, 112, "Z1  ESP32-S3 模组 + USB-C",
         "模组天线端朝右伸出板边；天线区全层禁铜/禁线/禁孔/禁件，"
         "外壳各方向留 ≥15 mm（H08）。USB 差分 90 Ω，靠近连接器放 ESD。",
         (238, 248, 238))
    d.rectangle([P(196, 62), P(214, 87.5)], outline=(20, 120, 60), width=2,
                fill=(225, 242, 228))
    d.text((P(197, 63)[0], P(197, 63)[1]), "U10 18×25.5", font=font(11, bold=True),
           fill=(20, 100, 60))
    d.text((P(197, 74)[0], P(197, 74)[1]), "天线→板边", font=font(10), fill=(20, 100, 60))
    # antenna keepout hatch beyond right edge
    for yy in range(int(45), int(112), 4):
        d.line([P(226, yy), P(241, yy - 3)], fill=(220, 120, 120), width=1)
    d.text((P(226, 45)[0], P(226, 45)[1] - 18), "天线禁布/净空 ≥15 mm",
           font=font(11, bold=True), fill=(190, 60, 60))
    # USB connector bottom edge
    d.rectangle([P(176, 112), P(192, 120)], outline=(90, 60, 160), width=2,
                fill=(240, 235, 252))
    d.text((P(176, 113)[0], P(176, 113)[1]), "J2 USB-C", font=font(11, bold=True),
           fill=(90, 60, 160))
    # 12V input left edge
    d.rectangle([P(4, 96), P(18, 108)], outline=(30, 80, 160), width=2,
                fill=(235, 242, 252))
    d.text((P(5, 97)[0], P(5, 97)[1]), "J1 12V", font=font(11, bold=True),
           fill=(30, 80, 160))
    # power converters bottom-left
    zone(18, 96, 90, 112, "Z2  12V→5V→3.3V + 电源选择",
         "开关电源输入回路小、远离天线；5V_SYS 去耦靠近 U2。", (235, 242, 252))
    # test points bottom
    zone(92, 98, 172, 112, "Z6  测试点/扩展接口", "TP1..TP20 + J4 排针", (245, 245, 235))
    # isolation slot
    d.rectangle([P(86.5, 48), P(89.5, 112)], fill=(200, 200, 200))
    d.text((P(80, 88)[0], P(80, 88)[1] - 40), "HV 隔离槽\n/禁布带", font=font(11),
           fill=(80, 80, 80))
    # mounting holes
    for (x, y) in ((8, 8), (222, 8), (8, 112), (222, 112)):
        d.ellipse([P(x - 3.2, y - 3.2), P(x + 3.2, y + 3.2)], outline=INK, width=2)
        d.ellipse([P(x - 1.6, y - 1.6), P(x + 1.6, y + 1.6)], outline=INK, width=1)
    d.text((P(0, 0)[0], Hp - 96), "尺寸单位 mm；M3 安装孔 4×（φ3.2/φ6）距板边 8 mm；"
           "板厚/层叠建议 4 层（信号-地-电源-底层），两层板仅在回流与禁布满足且实测通过后采用。",
           font=font(13), fill=GRAY)
    d.text((P(0, 0)[0], Hp - 70), "本预布局仅表达分区与约束优先级：管座中心距、"
           "天线净空、HV 爬电/间隙均需 H03/H07/H08 关闭后才能冻结。",
           font=font(13), fill=RED)
    # dimension strings
    d.line([P(0, BH + 4), P(BW, BH + 4)], fill=INK, width=1)
    d.text((P(BW / 2 - 12, BH + 5)[0], P(BW / 2 - 12, BH + 5)[1]), "230 mm",
           font=font(13, bold=True), fill=INK)
    d.line([P(BW + 4, 0), P(BW + 4, BH)], fill=INK, width=1)
    d.text((P(BW + 5, BH / 2)[0] + 6, P(BW + 5, BH / 2)[1]), "120 mm",
           font=font(13, bold=True), fill=INK)
    p = os.path.join(OUT_LAY, "QS30-6_REV.A_prelayout.png")
    img.save(p)
    return p, img


def main():
    sheet_lv.build()
    sheet_hv.build()
    model.class_by_prefix()
    bd_p, bd = block_diagram()
    pages, sheet_paths = connection_sheets()
    ch_p, ch = channel_table()
    lay_p, lay = prelayout()
    # PDFs
    for i, pg in enumerate(pages, 1):
        pg.save(os.path.join(OUT_SCH, f"page_{i:02d}.png"))
    pdf = os.path.join(OUT_SCH, "QS30-6_REV.A_原理图连接表.pdf")
    bd.save(pdf, "PDF", resolution=152.0, save_all=True, append_images=pages + [ch])
    print("wrote", pdf, bd_p, ch_p)
    lay_pdf = os.path.join(OUT_LAY, "QS30-6_REV.A_prelayout.pdf")
    lay.save(lay_pdf, "PDF", resolution=152.0)
    print("wrote", lay_pdf, lay_p)
    for p in sheet_paths:
        print("sheet:", p)


if __name__ == "__main__":
    main()
