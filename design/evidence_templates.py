# -*- coding: utf-8 -*-
"""生成 HOLD 关闭证据模板（CSV，Excel 可直接填写；UTF-8-SIG）。

目的：把 HOLD_REGISTER 中"需要什么证据"变成**可机器校验的表格**：
  - 期望值（expected/limit）从设计数据库自动填入，避免人工抄错；
  - 填写区统一用 FILL 标记，`design/evidence_check.py` 会区分"未提交/部分/完整"，
    并对完整提交做自动判据校验。

输出目录：docs/evidence/
运行：python design/evidence_templates.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import sheet_lv
import sheet_hv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "evidence")
os.makedirs(OUT, exist_ok=True)

FILL = "FILL"


def write(name, header, rows):
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {p}  ({len(rows)} rows)")


def build():
    sheet_lv.build()
    sheet_hv.build()
    model.class_by_prefix()


def h02():
    # 逐脚点亮：期望功能来自原厂电极图（model.PIN_DB["QS30-1"]）
    rows = []
    for t in range(1, 7):
        for pin in [str(i) for i in range(1, 14)]:
            func = model.PIN_DB["QS30-1"][pin]
            expect_glow = "N" if "KEEP_OPEN" in func else "Y"
            rows.append([f"J_T{t}", pin, func, expect_glow, FILL, FILL, ""])
    write("H02_tube_pin_test.csv",
          ["tube_id", "pin", "expected_function", "expect_glow",
           "glow_observed_Y/N", "pin_current_mA", "note"], rows)

    rows = []
    for t in range(1, 7):
        rows.append([f"J_T{t}", FILL, FILL, FILL, FILL, FILL, FILL, FILL])
    write("H02_tube_operating_point.csv",
          ["tube_id", "batch_mark_photo_file", "strike_V", "extinguish_V",
           "U_tube_at_172V_V", "I_mA_at_172V", "brightness_note", "operator"],
          rows)


def h03():
    items = [
        ("M1", "节圆直径（13 焊脚所在圆）", "mm", "非等分时改为逐个极坐标"),
        ("M2", "相邻焊脚中心距（实测 3 处）", "mm", "记录 3 个位置"),
        ("M3", "焊脚直径/宽度", "mm", "3 个样本"),
        ("M4", "焊脚长度（座底面以下）", "mm", "3 个样本"),
        ("M5", "座体最大外径", "mm", "3 个样本"),
        ("M6", "座高（PCB 面到插管面）", "mm", "3 个样本"),
        ("M7", "安装孔位置/孔径", "mm", "相对 1 脚"),
        ("M8", "外形轮廓（方/圆/倒角/缺口）", "-", "照片+描述"),
        ("M9", "定位缺口/1 脚特征", "-", "照片+描述"),
        ("M10", "插拔行程/插拔力", "mm/N", "记录仪器"),
    ]
    rows = [[i, d, FILL, FILL, FILL, u, note] for i, d, u, note in items]
    write("H03_socket_measurement.csv",
          ["item", "description", "sample1", "sample2", "sample3", "unit",
           "note"], rows)
    # 四视图与通断表
    views = ["管底视图（引脚面向观察者）", "管座插入口顶视图",
             "管座焊脚底视图", "PCB 顶层封装图"]
    rows = [[i + 1, v, FILL, FILL, FILL] for i, v in enumerate(views)]
    write("H03_socket_views.csv",
          ["view_id", "view", "observed_from", "pin1_location", "photo_file"], rows)
    rows = [[i, FILL, FILL, FILL] for i in range(1, 14)]
    write("H03_socket_continuity.csv",
          ["socket_contact", "solder_pin", "continuity", "cross_routed_note"], rows)


def h04():
    rows = []
    for step in range(64):
        ch = step if step < 32 else step          # channel 顺序 0..63
        dev = sheet_hv.device_of(ch)
        hv = sheet_hv.hvout_of(ch)
        pin = sheet_hv.HVOUT_PIN[hv]
        bit = 63 - ch
        tube = ch // 10 + 1
        digit = ch % 10
        rows.append([step, ch, dev, f"HVOUT{hv}", pin, bit,
                     f"J_T{tube}", digit, FILL, FILL, ""])
    write("H04_walking_one.csv",
          ["step", "channel", "device", "driver_output", "pqfp_pin",
           "serial_bit_index", "expected_tube", "expected_digit",
           "observed_tube", "observed_digit", "note"], rows)


def h05():
    # 12 V 输入 / 电源域 / USB 供电验证（阶段 A）
    rows = [
        ["A1-EXT12", "12 V 输入保护后电压", FILL, "V", 11.3, 11.7,
         "12 V−SS54 压降"],
        ["A1-EXT5", "12V→5V 输出", FILL, "V", 4.95, 5.15, "TPS54202 Vref 0.596"],
        ["A1-5VSYS", "5V_SYS（双肖特基 OR 后）", FILL, "V", 4.30, 4.90, ""],
        ["A1-3V3", "3.3 V 主电源", FILL, "V", 3.25, 3.38, "SY8089A 0.6 V 基准"],
        ["A1-DRVVDD", "DRV_VDD", FILL, "V", 11.00, 11.80, "HV5622 需 10.8–13.2"],
        ["A2-USBmA", "仅 USB 供电总电流", FILL, "mA", 0, 500, "USB-C 默认 500 mA"],
        ["A3-backmV", "VBUS 反向回灌电压", FILL, "mV", 0, 50, "电源选择反向阻断"],
        ["A4-ENdelay", "EN RC 释放延时", FILL, "ms", 5, 30, "10k×1µF ≈10 ms"],
        ["A6-HVENQ0", "复位时 HV_EN_REQ 电平", FILL, "V", 0, 0.2, "外部下拉"],
        ["A6-BL0", "复位时 DRV_BL 电平", FILL, "V", 0, 0.2, "12 V 域下拉"],
        ["A7-3V3min", "Wi-Fi 发射时 3V3 最低值", FILL, "V", 3.00, 3.60, ""],
    ]
    write("H05_power.csv",
          ["test_id", "description", "measured", "unit", "limit_min",
           "limit_max", "note"], rows)


def h06():
    rows = [
        ["C1-Vout", "六管稳态输出", FILL, "V", 169.0, 175.0, "设计 172.2"],
        ["C1-ripple", "输出纹波（示波器）", FILL, "mVpp", 0, 200,
         "SPICE 8.7 mV，含探针/振铃"],
        ["C2-overshoot", "启动过冲峰值", FILL, "V", 0, 190.0,
         "仿真 180.7，OVP 198.8"],
        ["C3-line11.4-Vout", "输入 11.4 V 时输出", FILL, "V", 168.0, 175.0, ""],
        ["C4-loadstep", "负载突变恢复时间", FILL, "ms", 0, 50, ""],
        ["C5-OVPtrip", "OVP 触发电压", FILL, "V", 197.3, 200.3,
         "198.8 V ±1.5 V（电阻/基准容差）"],
        ["C5-OVPcomp", "OVP 后 COMP 电平", FILL, "V", 0, 0.2, "Q23 拉低"],
        ["C6-short-Vout", "输出短路 10Ω 时电压", FILL, "V", 0, 20, ""],
        ["C7-discharge50", "断电 172→50 V 时间", FILL, "s", 0.5, 5.0,
         "仿真 3.84 s（200 kΩ/20 µF）"],
        ["C8-inrush", "启动浪涌峰值", FILL, "A", 0, 3.5, "仿真 2.9–3.1 A"],
        ["C9-anoderes", "单管短路时阳极电阻温升", FILL, "°C", 0, 60,
         "1.48 W/管（2×2 W）"],
        ["C10-Q20", "MOSFET 表面温升", FILL, "°C", 0, 60, ""],
        ["C10-D20", "二极管表面温升", FILL, "°C", 0, 60, ""],
        ["C10-eff", "整机效率（输出/输入）", FILL, "%", 60, 90,
         "仿真功率级 95.9%（不含 Coss）"],
    ]
    write("H06_hv.csv",
          ["test_id", "description", "measured", "unit", "limit_min",
           "limit_max", "note"], rows)


def h07():
    rows = [
        ["HV_BUS ↔ 3V3", "PCB 实测最小间距", FILL, 1.0, "H07 待定标准", FILL],
        ["HV_BUS ↔ USB 差分", "PCB 实测最小间距", FILL, 1.0, "H07", FILL],
        ["KV 阴极 ↔ 地平面", "PCB 实测最小间距", FILL, 1.0, "H07", FILL],
        ["HV_BUS ↔ 天线禁布区", "PCB 实测最小间距", FILL, 1.0, "H07/H08", FILL],
        ["HV 爬电（管座焊盘间）", "PCB 实测最小爬电", FILL, 1.0, "H07", FILL],
    ]
    write("H07_spacing.csv",
          ["net_pair", "item", "measured_mm", "required_mm_placeholder",
           "standard_ref", "pass"], rows)


def h08():
    rows = [
        [c, "rssi_dbm", "throughput_mbps", "reconnect_s", "distance_m", "note"]
        for c in ["升压关闭", "升压带载（六管）", "六管切换（动态）", "装壳后复测"]
    ]
    rows = [[r[0], FILL, FILL, FILL, FILL, ""] for r in rows]
    write("H08_rf.csv",
          ["condition", "rssi_dbm", "throughput_mbps", "reconnect_s",
           "distance_m", "note"], rows)


def main():
    build()
    h02()
    h03()
    h04()
    h05()
    h06()
    h07()
    h08()
    # 说明
    p = os.path.join(OUT, "README.md")
    open(p, "w", encoding="utf-8").write("""# HOLD 关闭证据（模板）

用法：
1. 现场测试后，把 `FILL` 替换为实测值（保持列名与行序不变；Excel 另存为 UTF-8 CSV）。
2. 运行 `python design/evidence_check.py`，生成 `docs/hold_closure_report.md`：
   - 全部为 FILL → 该项记为"未提交"；
   - 部分填写 → "部分提交（需补全）"；
   - 全部填写 → 自动判据校验，输出 PASS/FAIL 与失败原因。
3. 证据 PASS 后仍需人工签署 `HOLD_REGISTER.md` 的关闭记录；自动校验不替代签审。

| 文件 | 对应 HOLD | 自动判据 |
|---|---|---|
| H02_tube_pin_test.csv / H02_tube_operating_point.csv | H02 | 期望发光/不发光；U_tube/I 范围 |
| H03_socket_measurement.csv / _views.csv / _continuity.csv | H03 | 全部数值已填、3 样本一致性、13 触点连通 |
| H04_walking_one.csv | H04 | 观测=期望，60 路双射（无重复/遗漏） |
| H05_power.csv | H05 | 每项落在 limit_min..limit_max |
| H06_hv.csv | H06 | 同上（OVP/浪涌/泄放/温升） |
| H07_spacing.csv | H07 | 实测 ≥ required（占位值，标准定稿后更新） |
| H08_rf.csv | H08 | 记录齐全（阈值待整机 RF 目标确定） |
""")
    print("wrote", p)


if __name__ == "__main__":
    main()
