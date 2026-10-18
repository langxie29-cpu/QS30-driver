# -*- coding: utf-8 -*-
"""投板前检查清单（自动汇总所有机器检查与 HOLD 状态）。

读：
  docs/design_summary.json        ERC 统计
  docs/drc_precheck.json          DRC 预检
  sim/results/spice_validation.json   SPICE 证据
  docs/test_plan_check.json       测试计划一致性
  docs/bom_review.json            BOM 选型复核
  docs/doc_consistency.json       文档一致性
  docs/thermal_review.json        热/浪涌复核
  docs/hold_signoff_report.json   HOLD 签署联动
写：
  docs/preflight_checklist.md / .json

结论规则（硬性）：
  - 任一 HOLD 未 CLOSED → 状态 **RELEASE BLOCKED（不得投板/下单/释放 Gerber）**
  - 任一机器检查 FAIL → RELEASE BLOCKED
  - 全部满足 → 仍需人工在 HOLD_REGISTER 签署后才允许释放（本脚本不会自动放行）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")


def load(name, base=DOC):
    p = os.path.join(base, name)
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def main():
    d = load("design_summary.json")
    drc = load("drc_precheck.json")
    sv = load("spice_validation.json", os.path.join(ROOT, "sim", "results"))
    tp = load("test_plan_check.json")
    br = load("bom_review.json")
    dc = load("doc_consistency.json")
    th = load("thermal_review.json")
    hold = load("hold_signoff_report.json")
    fw = load("firmware_constraints.json")

    checks = []

    def add(name, ok, detail):
        checks.append(dict(name=name, pass_=bool(ok), detail=detail))

    add("ERC（19 项，0 错 0 警）", d and d["errors"] == 0 and d["warnings"] == 0,
        f"器件 {d['parts']}/引脚 {d['pins']}/网络 {d['nets']}/通道 {d['used_channels']}；"
        f"错误 {d['errors']} 告警 {d['warnings']}")
    add("DRC 预检（14 项）", drc and drc["passed"] == drc["total"],
        f"{drc['passed']}/{drc['total']}")
    avg_ok = sum(1 for _, ok in sv["averaged_closed_loop"]["checks"] if ok)
    ovp_ok = sum(1 for _, ok in sv["ovp_logic"]["checks"] if ok)
    add("SPICE 自检 4/4", all(r["passed"] for r in sv["validation"]), "RC/RL/二极管/B 源")
    add("开关级功率级", abs(sv["boost"]["vout_mean"] - 172.0) < 1.0,
        f"Vout {sv['boost']['vout_mean']:.2f} V，效率 {sv['boost']['eff_pct']:.1f}%")
    add("平均模型闭环 8/8", sv["averaged_closed_loop"]["passed"], f"{avg_ok}/8")
    add("OVP 保护逻辑 7/7", sv["ovp_logic"]["passed"],
        f"首次触发 {sv['ovp_logic']['trip_level']:.2f} V，峰值 {sv['ovp_logic']['vmax']:.2f} V")
    add("测试计划一致性 5/5", tp and tp["passed"] == tp["total"], f"{tp['passed']}/{tp['total']}")
    add("BOM 选型复核 5/5", br and all(c["pass_"] for c in br["checks"]),
        f"{sum(1 for c in br['checks'] if c['pass_'])}/{len(br['checks'])}")
    add("文档一致性 5/5", dc and dc["passed"] == dc["total"], f"{dc['passed']}/{dc['total']}")
    add("热/浪涌复核", th is not None,
        f"HV5622 温升 {th['conclusion']['rise_C_range'][0]:.1f}–{th['conclusion']['rise_C_range'][1]:.1f} °C；"
        f"启动峰值 {th['inrush']['peak_A']:.2f} A；I²t {th['inrush']['i2t_A2s']:.4f} A²s")
    add("固件约束派生", fw is not None,
        f"{len(fw['constraints'])} 条；帧 {fw['frame']['bits']} bit；{len(fw['control_pins'])} 控制脚")

    # HOLD 状态
    holds = {h: "OPEN" for h in ["H01", "H02", "H03", "H04", "H05", "H06", "H07", "H08", "H09"]}
    if hold:
        for r in hold:
            holds[r["hold"]] = r["status"]
    closed = [h for h, v in holds.items() if v == "CLOSED"]
    open_holds = [h for h, v in holds.items() if v != "CLOSED"]

    machine_pass = all(c["pass_"] for c in checks)
    release_blocked = bool(open_holds) or not machine_pass

    pending = [
        ("H01 旧基线原理图/PCB 原件", "需原始工程文件与版本确认", "H01"),
        ("H02 QS30-1 六管工作点/脚位实测", "需实物管 + 单管夹具", "H02"),
        ("H03 13 脚管座实测 → 封装冻结（14 个 TBD 字段）", "需购样管座 + 卡尺/影像仪", "H03"),
        ("H04 walking-one 位序回填（当前 PROVISIONAL）", "需焊好的驱动板 + 低压测试负载", "H04"),
        ("H05 低压电源/USB 实测", "需样机（低压部分）", "H05"),
        ("H06 高压实测（含 OVP 时序/温升/Coss/PPTC）", "需隔离测试区 + 差分探头", "H06"),
        ("H07 高压间距/爬电标准定稿", "需结构/标准输入 + PCB", "H07"),
        ("H08 整机 RF（装壳后）", "需外壳与整机", "H08"),
        ("H09 立创EDA 工程与原生 ERC/DRC 验收", "需立创EDA + 人工审查", "H09"),
        ("U20 封装冻结（DIP-8 / SOIC-8）", "结构与散热确定后二选一", "D-29"),
        ("HV5622 手册参数（VDD 电流/Von/Rth_ja）", "需厂商手册核实", "thermal_review"),
        ("PPTC 手册 I²t / 触发曲线", "需厂商手册 + H05/H06 波形", "I-25"),
    ]

    lines = ["# 投板前检查清单（自动汇总）", "",
             f"**当前状态：{'🚫 RELEASE BLOCKED — 不得投板 / 下单 / 释放 Gerber' if release_blocked else '✅ 机器检查全绿（仍须人工签署 HOLD 后才可释放）'}**", "",
             f"- 机器检查：{sum(1 for c in checks if c['pass_'])}/{len(checks)} 通过；"
             f"HOLD：CLOSED {len(closed)}/{len(holds)}；未关闭 {len(open_holds)} 项",
             f"- 判定依据：任一 HOLD 未 CLOSED，或任一机器检查 FAIL → RELEASE BLOCKED。"
             "本脚本**不会自动放行**，最终放行必须人工在 `HOLD_REGISTER.md` 签署。", "",
             "## 1. 机器检查", "",
             "| 检查 | 结果 | 详情 |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['name']} | {'PASS' if c['pass_'] else 'FAIL'} | {c['detail']} |")
    lines += ["", "## 2. HOLD 状态（来自签署联动报告）", "",
              "| HOLD | 状态 |", "|---|---|"]
    for h, v in holds.items():
        lines.append(f"| {h} | **{v}** |")
    lines += ["", "## 3. 投板前必须关闭/冻结的事项", "",
              "| 事项 | 解除条件 | 关联 |", "|---|---|---|"]
    for item, cond, link in pending:
        lines.append(f"| {item} | {cond} | {link} |")
    lines += ["", "## 4. 放行流程（人工）", "",
              "1. 实物测试 → 回填 `docs/evidence/*.csv` → `python design/evidence_check.py` 判据通过；",
              "2. 在 `docs/HOLD_SIGNOFF.csv` 填写签署人/日期/版本并决定 CLOSED → `python design/hold_signoff.py`；",
              "3. 重建原生 EDA 工程并跑 ERC/DRC（H09），记录到 `docs/`；",
              "4. 重新运行本清单：状态变为\"机器检查全绿\"且所有 HOLD=CLOSED；",
              "5. 人工复核后按 `HOLD_REGISTER.md` 签署放行，才允许生成/释放 Gerber。", "",
              "> 摘要：本设计当前**不具备投板条件**——所有阻塞均需实物数据或原生 EDA，"
              "不是软件侧可关闭项；已执行部分见审查包与各检查报告。"]
    open(os.path.join(DOC, "preflight_checklist.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(release_blocked=release_blocked, machine_pass=machine_pass,
                   checks=checks, holds=holds, closed=closed,
                   open_holds=open_holds, pending=pending),
              open(os.path.join(DOC, "preflight_checklist.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"preflight: release_blocked={release_blocked}；"
          f"机器检查 {sum(1 for c in checks if c['pass_'])}/{len(checks)}；"
          f"HOLD CLOSED {len(closed)}/{len(holds)}")
    print("wrote docs/preflight_checklist.md/.json")


if __name__ == "__main__":
    main()
