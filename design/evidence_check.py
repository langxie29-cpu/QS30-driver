# -*- coding: utf-8 -*-
"""HOLD 证据校验：读取 docs/evidence/*.csv，判断 未提交/部分/完整，并对完整数据自动判据。

输出：docs/hold_closure_report.md + docs/hold_closure_report.json
退出码：0 = 无失败；2 = 有已提交证据未通过判据。
运行：python design/evidence_check.py
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.environ.get("QS30_EVIDENCE_DIR", os.path.join(ROOT, "docs", "evidence"))
DOC = os.environ.get("QS30_DOC_DIR", os.path.join(ROOT, "docs"))
FILL = "FILL"


def read(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fill_status(rows):
    """返回 (状态, 已填单元格, 总单元格)。状态: missing/partial/complete"""
    total = filled = 0
    for r in rows:
        for k, v in r.items():
            if k in ("tube_id", "pin", "expected_function", "expect_glow",
                     "step", "channel", "device", "driver_output", "pqfp_pin",
                     "serial_bit_index", "expected_tube", "expected_digit",
                     "item", "description", "unit", "test_id", "limit_min",
                     "limit_max", "note", "condition", "net_pair",
                     "required_mm_placeholder", "standard_ref", "view_id",
                     "view", "socket_contact", "solder_pin", "description"):
                continue
            total += 1
            if v is not None and str(v).strip() not in ("", FILL):
                filled += 1
    if filled == 0:
        return "missing", filled, total
    return ("complete" if filled == total else "partial"), filled, total


def num(v):
    try:
        return float(str(v).strip())
    except Exception:
        return None


def check_h02():
    rows = read("H02_tube_pin_test.csv")
    op = read("H02_tube_operating_point.csv")
    if not rows or not op:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    sto, fo, to = fill_status(op)
    if st != "complete" or sto != "complete":
        return ("missing" if st == "missing" and sto == "missing" else "partial"), \
            [f"逐脚 {f}/{t}，工作点 {fo}/{to}"]
    errs = []
    for r in rows:
        glow = str(r["glow_observed_Y/N"]).strip().upper()
        if glow not in ("Y", "N"):
            errs.append(f"{r['tube_id']}.{r['pin']} glow 取值非法: {glow}")
            continue
        if glow != r["expect_glow"]:
            errs.append(f"{r['tube_id']}.{r['pin']} 期望 {r['expected_function']} "
                        f"发光 {r['expect_glow']}，实测 {glow}")
        i = num(r["pin_current_mA"])
        if i is not None and not (0 <= i <= 5):
            errs.append(f"{r['tube_id']}.{r['pin']} 引脚电流 {i} mA 异常")
    for r in op:
        u = num(r["U_tube_at_172V_V"])
        i = num(r["I_mA_at_172V"])
        strike = num(r["strike_V"])
        ext = num(r["extinguish_V"])
        if u is None or i is None or strike is None or ext is None:
            errs.append(f"{r['tube_id']} 工作点缺数值")
            continue
        if not (100 <= u <= 150):
            errs.append(f"{r['tube_id']} U_tube={u}V 超出 100–150 V 合理范围")
        if not (1.5 <= i <= 3.0):
            errs.append(f"{r['tube_id']} I={i}mA 超出原厂 1.5–3 mA")
        if strike > 150:
            errs.append(f"{r['tube_id']} 起辉 {strike}V > 原厂最大 150 V")
        if ext < 100:
            errs.append(f"{r['tube_id']} 熄灭 {ext}V < 原厂最小 100 V")
    return ("complete" if not errs else "fail"), errs


def check_h03():
    rows = read("H03_socket_measurement.csv")
    views = read("H03_socket_views.csv")
    cont = read("H03_socket_continuity.csv")
    if not rows or not views or not cont:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    sv, fv, tv = fill_status(views)
    sc, fc, tc = fill_status(cont)
    if st == "missing" and sc == "missing":
        return "missing", [f"测量 {f}/{t}，视图 {fv}/{tv}，通断 {fc}/{tc}"]
    if not (st == sv == sc == "complete"):
        return "partial", [f"测量 {f}/{t}，视图 {fv}/{tv}，通断 {fc}/{tc}"]
    errs = []
    # 3 样本一致性（相对偏差 < 5%）
    for r in rows:
        vals = [num(r[k]) for k in ("sample1", "sample2", "sample3")]
        vals = [v for v in vals if v is not None]
        if len(vals) >= 2:
            mx, mn = max(vals), min(vals)
            if mx > 0 and (mx - mn) / mx > 0.05:
                errs.append(f"{r['item']} 3 样本偏差 >5%：{vals}")
    for r in cont:
        if str(r["continuity"]).strip().upper() not in ("Y", "N"):
            errs.append(f"触点 {r['socket_contact']} 通断值非法")
        elif str(r["continuity"]).strip().upper() != "Y":
            errs.append(f"触点 {r['socket_contact']} 未连通")
    for r in views:
        v = str(r["pin1_location"]).strip()
        if v in ("", FILL) or v.upper() == "FILL":
            errs.append(f"{r['view']} 未填 1 脚位置")
    return ("complete" if not errs else "fail"), errs


def check_h04():
    rows = read("H04_walking_one.csv")
    if not rows:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    if st == "missing":
        return "missing", [f"{f}/{t}"]
    if st == "partial":
        return "partial", [f"{f}/{t}"]
    errs = []
    seen = set()
    for r in rows:
        ot = str(r["observed_tube"]).strip()
        od = str(r["observed_digit"]).strip()
        if (ot, od) in seen:
            errs.append(f"CH{r['channel']} 观测重复 {ot}/{od}")
        seen.add((ot, od))
        if ot != r["expected_tube"] or od != r["expected_digit"]:
            # 允许整体位序颠倒（walking-one 确认的另一种常见结果）：记录但不判失败前先看全局
            errs.append(f"CH{r['channel']} 期望 {r['expected_tube']}/{r['expected_digit']}，"
                        f"实测 {ot}/{od}")
    if len(seen) < 60:
        errs.append(f"仅覆盖 {len(seen)} 个不同通道（应 ≥60，双射）")
    return ("complete" if not errs else "fail"), errs


def check_limits(name):
    rows = read(name)
    if not rows:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    if st == "missing":
        return "missing", [f"{f}/{t}"]
    if st == "partial":
        return "partial", [f"{f}/{t}"]
    errs = []
    for r in rows:
        v = num(r["measured"])
        lo, hi = num(r["limit_min"]), num(r["limit_max"])
        if v is None:
            errs.append(f"{r['test_id']} 非数值: {r['measured']}")
        elif lo is not None and hi is not None and not (lo <= v <= hi):
            errs.append(f"{r['test_id']} 实测 {v} 不在 [{lo}, {hi}]")
    return ("complete" if not errs else "fail"), errs


def check_h07():
    rows = read("H07_spacing.csv")
    if not rows:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    if st != "complete":
        return st, [f"{f}/{t}"]
    errs = []
    for r in rows:
        v = num(r["measured_mm"])
        req = num(r["required_mm_placeholder"])
        if v is None:
            errs.append(f"{r['net_pair']} 非数值")
        elif req is not None and v < req:
            errs.append(f"{r['net_pair']} 实测 {v} < 占位要求 {req} mm")
    return ("complete" if not errs else "fail"), errs


def check_h08():
    rows = read("H08_rf.csv")
    if not rows:
        return "missing", ["模板缺失"]
    st, f, t = fill_status(rows)
    if st != "complete":
        return st, [f"{f}/{t}"]
    errs = []
    for r in rows:
        for k in ("rssi_dbm", "throughput_mbps", "reconnect_s", "distance_m"):
            if num(r[k]) is None:
                errs.append(f"{r['condition']} {k} 非数值")
    return ("complete" if not errs else "fail"), errs


CHECKS = {
    "H02": check_h02,
    "H03": check_h03,
    "H04": check_h04,
    "H05": lambda: check_limits("H05_power.csv"),
    "H06": lambda: check_limits("H06_hv.csv"),
    "H07": check_h07,
    "H08": check_h08,
}


def main():
    results = {}
    any_fail = False
    for hid, fn in CHECKS.items():
        status, msgs = fn()
        results[hid] = dict(status=status, messages=msgs)
        if status == "fail":
            any_fail = True
    submitted = sum(1 for r in results.values() if r["status"] != "missing")
    passed = sum(1 for r in results.values() if r["status"] == "complete")

    lines = ["# HOLD 关闭证据自动校验报告", "",
             f"- 已提交 HOLD：{submitted}/{len(results)}；通过：{passed}",
             f"- 生成时间：由 `design/evidence_check.py` 运行",
             "", "> 自动校验只检查数据是否齐全、是否落在设计判据内；"
             "HOLD 正式关闭仍需 `HOLD_REGISTER.md` 的人工签署。", "",
             "| HOLD | 状态 | 说明 |", "|---|---|---|"]
    label = {"missing": "未提交", "partial": "部分提交（需补全）",
             "complete": "已提交·判据通过", "fail": "**已提交·判据失败**"}
    for hid in CHECKS:
        r = results[hid]
        detail = "; ".join(r["messages"][:6]) if r["messages"] else "—"
        lines.append(f"| {hid} | {label[r['status']]} | {detail} |")
    lines += ["", "## 用法", "",
              "1. 打开 `docs/evidence/` 下对应 CSV，把 `FILL` 替换为实测值；",
              "2. `python design/evidence_check.py`；",
              "3. 通过后在 `HOLD_REGISTER.md` 记录签署人/日期/版本（自动校验不代替签审）。"]
    open(os.path.join(DOC, "hold_closure_report.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(results, open(os.path.join(DOC, "hold_closure_report.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(lines))
    sys.exit(2 if any_fail else 0)


if __name__ == "__main__":
    main()
