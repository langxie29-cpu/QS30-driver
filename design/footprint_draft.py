# -*- coding: utf-8 -*-
"""QS30-1 管座封装草案（PROVISIONAL）+ H03 实测工作表 + 1:1 校对页。

原则（依交接文件与任务书）：
  * 原厂资料只给出**管子**尺寸与脚号关系，不给**管座**焊脚坐标；
  * GB 787-74 J13-1A 正文未取得，且"J13-1A"是管基型号，不等于任何在售管座；
  * 因此本文件**不填任何猜测的焊脚坐标/孔径/镜像方向**，只把已核实项画出来，
    把必须实测的项做成待填字段与待填表格；
  * 1:1 校对页按 300 dpi 精确尺寸输出（打印时选择"实际大小/100%"）。

输出：
  symbols/QS30-1_socket_footprint_draft.json   参数化封装定义（含 TBD 字段）
  docs/footprint/QS30-1_管座_1比1校对页.pdf/.png
  docs/footprint/H03_管座实测工作表.md
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_D = os.path.join(ROOT, "docs", "footprint")
OUT_S = os.path.join(ROOT, "symbols")
os.makedirs(OUT_D, exist_ok=True)
os.makedirs(OUT_S, exist_ok=True)

DPI = 300.0
MM = DPI / 25.4            # px per mm
A4 = (int(round(210 * MM)), int(round(297 * MM)))

F_CJK = "C:/Windows/Fonts/msyh.ttc"
F_CJKB = "C:/Windows/Fonts/msyhbd.ttc"


def font(sz, bold=False):
    """sz 以 pt 为单位，按 300 dpi 转像素。"""
    return ImageFont.truetype(F_CJKB if bold else F_CJK,
                              max(10, int(round(sz * DPI / 72.0))))


def wrap(d, text, f, maxw):
    out = []
    for para in str(text).split("\n"):
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
# 1) 参数化封装草案（不猜测）
# ---------------------------------------------------------------------------
DRAFT = {
    "project": "QS30-6 REV.A",
    "object": "J13-1A 13-pin socket footprint for Nanchang QS30-1",
    "status": "PROVISIONAL",
    "blocked_by": "H03",
    "note": "禁止据本文件投板；所有 TBD 字段必须有实测/原厂机械图后才能填并升版本",
    "pad_count": 13,
    "pad_numbering": {
        "rule": "焊盘编号 = QS30-1 物理脚号 = 符号脚号（1:1），禁止按数字 0..9 重排",
        "map": {
            "1": "IC_KEEP_OPEN", "2": "A", "3": "K0", "4": "K9", "5": "K8",
            "6": "K7", "7": "K6", "8": "IC8_KEEP_OPEN", "9": "K5",
            "10": "K4", "11": "K3", "12": "K2", "13": "K1",
        },
        "electrical_only_note": "1/8 号焊盘保留但不接网络（悬空）",
    },
    "verified_from_datasheet": {
        "source": "S6 南昌电子管厂 QS30 型式说明书（原厂扫描页）",
        "tube_body_max_dia_mm": 30.2,
        "tube_overall_height_mm": "34±1.5",
        "tube_body_height_mm": "26±0.5",
        "pin_count_and_dia": "13 × φ1.3 mm（管子引脚，非管座焊脚）",
        "pin_layout": "13 脚圆周均布，编号 1..13 顺时针（按原厂电极接线图，观察方向待 H03）",
        "base_standard": "GB 787-74 J13-1A",
    },
    "tbd_from_h03": {
        "bolt_circle_diameter_mm": None,
        "pad_drill_mm": None,
        "pad_diameter_mm": None,
        "pad_annular_ring_mm": None,
        "pad_shape": "round THT（待定）",
        "pad1_marker": None,
        "keying_notch_or_pin1_reference": None,
        "view_direction_of_pad_coordinates": None,
        "socket_body_dia_mm": None,
        "socket_seat_height_mm": None,
        "socket_pin_length_mm": None,
        "mechanical_fixing": None,
        "insertion_force_and_travel_mm": None,
        "socket_voltage_rating": None,
    },
    "layout_placeholder": {
        "angular_pitch_deg": 360.0 / 13.0,
        "pin1_angle_deg": "TBD（以定位缺口或不对称脚位配准；不得用屏幕上的顺/逆时针编号）",
        "mirroring_rule": "禁止镜像；管底视图/插入口顶视图/焊脚底视图/PCB 顶视封装图必须分别标注",
    },
    "verification_evidence_required": [
        "带尺寸的实物照片（管座正/反/侧）",
        "13 个触点 → 13 个焊脚逐一通断表（确认有无交叉引出）",
        "各焊脚 XY 坐标 / 脚径或脚宽 / 公差 / 节圆或非等分位置",
        "安装孔与外形尺寸、座高、插拔空间",
        "1:1 打印图与实物叠图照片",
        "试插样板或机械治具记录",
        "标注观察面的 1 脚方向图",
    ],
}


def write_json():
    DRAFT["no_guessed_geometry"] = True
    DRAFT["generator_validation"] = "design/footprint_draft.py verify_no_guesses() PASS"
    p = os.path.join(OUT_S, "QS30-1_socket_footprint_draft.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(DRAFT, f, ensure_ascii=False, indent=2)
    return p


# ---------------------------------------------------------------------------
# 2) 1:1 校对页（300 dpi → 物理尺寸精确）
# ---------------------------------------------------------------------------
def one_to_one_page():
    img = Image.new("RGB", A4, "white")
    d = ImageDraw.Draw(img)

    def pmm(x, y):
        return (x * MM, y * MM)

    def txt(x, y, t, pt=9, bold=False, fill=(0, 0, 0), w=None):
        lines = wrap(d, t, font(pt, bold), int((w if w else 186) * MM))
        for i, ln in enumerate(lines):
            d.text(pmm(x, y + i * (pt * 0.42)), ln, font=font(pt, bold), fill=fill)
        return y + len(lines) * pt * 0.42

    d.rectangle([pmm(8, 8), pmm(202, 289)], outline=(0, 0, 0), width=2)
    txt(12, 11, "QS30-1 管座 1:1 校对页（PROVISIONAL，H03 未关闭）", 15, True)
    txt(12, 19.5,
        "打印必须选择「实际大小 / 100%」，关闭“适合页面/缩放”。打印后先量下方 100 mm 标尺，"
        "偏差 >0.5 mm 必须重打；本页只画已核实尺寸，灰色环仅为角度示意。", 8.5, False,
        (150, 40, 40))

    # 100 mm 标尺
    ry = 31
    d.line([pmm(12, ry), pmm(112, ry)], fill=(0, 0, 0), width=3)
    for i in range(0, 101, 10):
        d.line([pmm(12 + i, ry), pmm(12 + i, ry - 2.5)], fill=(0, 0, 0), width=2)
        d.text(pmm(11.2 + i, ry + 1), f"{i}", font=font(6.5), fill=(0, 0, 0))
    txt(114, ry - 2.5, "100 mm 标尺（应为 100.0 mm）", 8)

    # ---- 俯视：φ30.2 玻壳 + 显示窗口 + 13 等分角度示意 ----
    cx, cy = 62, 74
    r_body = 30.2 / 2
    d.ellipse([pmm(cx - r_body, cy - r_body), pmm(cx + r_body, cy + r_body)],
              outline=(0, 0, 0), width=2)
    txt(cx - 14, cy - r_body - 7, "管子玻壳 φ30.2（原厂）", 9)
    r_win = 15.5 / 2
    d.ellipse([pmm(cx - r_win, cy - r_win), pmm(cx + r_win, cy + r_win)],
              outline=(150, 60, 60), width=1)
    d.line([pmm(cx + 6.5, cy + 6.5), pmm(cx + 22, cy + 22)], fill=(150, 60, 60), width=1)
    txt(cx + 20, cy + 22, "显示窗口 ≈φ15.5", 7, False, (150, 60, 60), w=40)
    d.line([pmm(cx - 3, cy), pmm(cx + 3, cy)], fill=(0, 0, 0), width=1)
    d.line([pmm(cx, cy - 3), pmm(cx, cy + 3)], fill=(0, 0, 0), width=1)
    # 13 等分角度示意环（灰色）
    import math
    r_ref = 8.0
    d.ellipse([pmm(cx - r_ref, cy - r_ref), pmm(cx + r_ref, cy + r_ref)],
              outline=(185, 185, 185), width=1)
    for i in range(13):
        a = math.radians(-90 + i * 360.0 / 13)
        d.line([pmm(cx + r_ref * math.cos(a), cy + r_ref * math.sin(a)),
                pmm(cx + (r_ref + 2.2) * math.cos(a),
                    cy + (r_ref + 2.2) * math.sin(a))], fill=(150, 150, 150), width=1)
        d.text(pmm(cx + (r_ref + 3.2) * math.cos(a) - 1,
                   cy + (r_ref + 3.2) * math.sin(a) - 1.3), str(i + 1),
               font=font(6), fill=(140, 140, 140))
    txt(12, cy + r_body + 4,
        "灰色环 = 13 等分角度示意（360/13）；节圆直径、孔径、1 脚方向全部待实测，禁止照此画焊盘。",
        8, False, (140, 140, 140), w=96)

    # ---- 侧视：26±0.5 / 34±1.5 ----
    x0, ytop, bw = 122, 58, 30.2
    d.rectangle([pmm(x0, ytop), pmm(x0 + bw, ytop + 26)], outline=(0, 0, 0), width=2)
    txt(x0, ytop - 6.5, "本体高 26±0.5（原厂）", 9)
    for i in range(13):
        x = x0 + 3 + i * 2.0
        d.line([pmm(x, ytop + 26), pmm(x, ytop + 33)], fill=(160, 160, 160), width=1)
    txt(x0, ytop + 34.5, "总高 34±1.5（含引脚，原厂）", 9)
    d.line([pmm(x0 + bw + 3, ytop), pmm(x0 + bw + 3, ytop + 26)], fill=(0, 0, 0), width=1)
    d.line([pmm(x0 + bw + 2, ytop), pmm(x0 + bw + 4, ytop)], fill=(0, 0, 0), width=1)
    d.line([pmm(x0 + bw + 2, ytop + 26), pmm(x0 + bw + 4, ytop + 26)], fill=(0, 0, 0), width=1)
    d.text(pmm(x0 + bw + 4, ytop + 11), "26", font=font(8), fill=(0, 0, 0))
    txt(x0, ytop + 40,
        "说明：灰色引脚为位置示意，不代表管座焊脚尺寸/坐标。", 7.5, False, (140, 140, 140), w=72)

    # ---- H03 实测填表区 ----
    ty = 112
    txt(12, ty, "H03 实测填写区（完成前不得生成封装、不得投板）", 12, True)
    rows = [
        "管座完整型号（采购件）",
        "观察方向（管底视图 / 插入口顶视图 / 焊脚底视图）",
        "1 脚定位特征（缺口 / 不对称脚位）描述",
        "节圆直径；各焊脚极坐标(r,θ) 或 XY",
        "焊脚直径或宽度 / 公差（mm）",
        "建议钻孔 / 焊盘外径（mm，需板厂能力）",
        "安装孔位置与尺寸（mm）",
        "座高 / 插拔行程 / 插拔力",
        "13 触点→焊脚通断表（是否交叉引出）",
        "管座耐压 / 绝缘资料（引用）",
    ]
    yy = ty + 8
    for label in rows:
        d.rectangle([pmm(12, yy), pmm(198, yy + 9)], outline=(150, 150, 150), width=1)
        d.text(pmm(13.5, yy + 2.2), label, font=font(8.5), fill=(0, 0, 0))
        yy += 10

    txt(12, yy + 2,
        "填表后：把实测值写入 symbols/QS30-1_socket_footprint_draft.json 的 tbd_from_h03 → "
        "生成封装 v2 → 1:1 叠图 → 作为 H03 关闭证据归档。", 8, False, (150, 60, 60))
    txt(12, yy + 7, "测量人：____________   日期：__________   "
        "管座批次：____________   打印比例校验：____________", 8.5)

    png = os.path.join(OUT_D, "QS30-1_管座_1比1校对页.png")
    img.save(png)
    pdf = os.path.join(OUT_D, "QS30-1_管座_1比1校对页.pdf")
    img.save(pdf, "PDF", resolution=DPI)
    return png, pdf


def verify_no_guesses():
    """确保草案里没有任何被猜出来的几何尺寸（只允许 None 或 TBD 文本）。"""
    tbd = DRAFT["tbd_from_h03"]
    bad = {k: v for k, v in tbd.items()
           if isinstance(v, (int, float))}
    if bad:
        raise SystemExit(f"FAIL: 封装草案出现猜测数值: {bad}")
    dia_fields = [k for k in tbd if k.endswith("_mm")]
    assert all(tbd[k] is None for k in dia_fields), "TBD 尺寸必须为 None"
    print("PASS: 封装草案未包含任何猜测的几何尺寸（全部 TBD/H03）")


def main():
    verify_no_guesses()
    p = write_json()
    png, pdf = one_to_one_page()
    print("wrote", p)
    print("wrote", png)
    print("wrote", pdf)


if __name__ == "__main__":
    main()
