# -*- coding: utf-8 -*-
"""HOLD 进度看板：把证据模板的填写进度、自动校验状态、关键路径汇总成一张表。

输出：docs/hold_dashboard.md（并作为审查包的一页）
运行：python design/hold_dashboard.py
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "docs", "evidence")
DOC = os.path.join(ROOT, "docs")
FILL = "FILL"

# HOLD -> (证据文件, 填写列, 关键路径说明)
HOLD_MAP = {
    "H02": (["H02_tube_pin_test.csv", "H02_tube_operating_point.csv"],
            ["glow_observed_Y/N", "pin_current_mA", "batch_mark_photo_file",
             "strike_V", "extinguish_V", "U_tube_at_172V_V", "I_mA_at_172V",
             "brightness_note", "operator"],
            "阻塞 H06 工作点与固件映射；先买 2–3 只 QS30-1 做单管夹具"),
    "H03": (["H03_socket_measurement.csv", "H03_socket_views.csv",
             "H03_socket_continuity.csv"],
            ["sample1", "sample2", "sample3", "observed_from", "pin1_location",
             "photo_file", "solder_pin", "continuity", "cross_routed_note"],
            "**唯一阻塞 PCB 封装的机械项**；购样 13 脚管座后实测"),
    "H04": (["H04_walking_one.csv"], ["observed_tube", "observed_digit", "note"],
            "阻塞固件通道 LUT；需要焊好的驱动板 + 低压测试负载"),
    "H05": (["H05_power.csv"], ["measured"],
            "低压电源/ USB 供电实测；可与 H06 部分并行"),
    "H06": (["H06_hv.csv"], ["measured"],
            "高压工作点/OVP/泄放/浪涌/温升；需隔离测试区与差分探头"),
    "H07": (["H07_spacing.csv"], ["measured_mm", "pass"],
            "高压间距与爬电标准定稿；与 H03 封装尺寸联动"),
    "H08": (["H08_rf.csv"], ["rssi_dbm", "throughput_mbps", "reconnect_s",
                             "distance_m"],
            "整机 RF；需外壳与整机装配"),
}


def read_csv(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    status = {}
    if os.path.exists(os.path.join(DOC, "hold_closure_report.json")):
        status = json.load(open(os.path.join(DOC, "hold_closure_report.json"),
                                encoding="utf-8"))
    rows = []
    for hid, (files, cols, path) in HOLD_MAP.items():
        filled = total = 0
        missing_files = []
        for fn in files:
            data = read_csv(os.path.join(EV, fn))
            if data is None:
                missing_files.append(fn)
                continue
            for r in data:
                for c in cols:
                    if c in r:
                        total += 1
                        v = str(r[c]).strip()
                        if v not in ("", FILL):
                            filled += 1
        pct = 0 if total == 0 else int(round(100.0 * filled / total))
        st = status.get(hid, {}).get("status", "missing") if status else "missing"
        rows.append(dict(hid=hid, filled=filled, total=total, pct=pct,
                         status=st, path=path, missing=missing_files))

    done = sum(1 for r in rows if r["status"] == "complete")
    submitted = sum(1 for r in rows if r["status"] != "missing")
    lines = ["# HOLD 进度看板（证据填写 + 关键路径）", "",
             f"- 证据提交：**{submitted}/7**；判据通过：**{done}/7**",
             f"- 说明：DASH 由 `design/hold_dashboard.py` 从 `docs/evidence/` 自动统计；"
             "自动校验不替代 `HOLD_REGISTER.md` 的人工签署。", "",
             "| HOLD | 模板填写进度 | 自动校验状态 | 关键路径 / 下一步 |",
             "|---|---|---|---|"]
    label = {"missing": "未提交", "partial": "部分提交",
             "complete": "通过", "fail": "判据失败"}
    for r in rows:
        bar = "#" * (r["pct"] // 10) + "-" * (10 - r["pct"] // 10)
        lines.append(f"| {r['hid']} | `{bar}` {r['pct']}% ({r['filled']}/{r['total']}) | "
                     f"{label.get(r['status'], r['status'])} | {r['path']} |")
    lines += ["", "## 关键路径（按阻塞影响排序）", "",
              "1. **H03 管座实测** → 冻结 PCB 封装（唯一机械阻塞项）→ 才能投板；",
              "2. **H02 单管工作点** → 确认 Ea/Ra/电流 → H06 高压额定值；",
              "3. **H06 高压实测** → OVP/泄放/浪涌/温升 → 安全放行依据；",
              "4. **H04 walking-one** → 冻结固件通道 LUT；",
              "5. **H05 低压实测** → 3.3 V/USB 供电验收；",
              "6. **H07 间距标准** → 写入 EDA 规则（与 H03 联动）；",
              "7. **H08 整机 RF** → 装壳后验收（最后一项）。",
              "",
              "## 当前可并行推进的软件侧工作",
              "",
              "- 立创EDA 工程按 `docs/lceda_implementation_guide.md` 重建（H01/H09）；",
              "- 固件通道映射以 `docs/channel_mapping.csv` 为输入，位序待 H04 回填；",
              "- 高压/低压测试按 `docs/test_plan.md` 阶段 A–E 执行并回填证据模板。"]
    open(os.path.join(DOC, "hold_dashboard.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    main()
