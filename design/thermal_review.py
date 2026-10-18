# -*- coding: utf-8 -*-
"""热与浪涌复核：HV5622 驱动 IC 功耗/温升估算 + PPTC 浪涌 I²t 分析。

数据来源：
  - `docs/channel_mapping.csv`：每管恒有 1 路阴极导通（静态驱动）→ 每片 HV5622 同时导通 3 路；
  - `sim/results/csv_S1.csv`：启动波形（电感电流 iL），用于浪涌 I²t 与超 1.5 A 持续时间；
  - H02 期望工作点：I_ka 2.36 mA（1.5–3 mA 中点）、U_ka ≈ 126 V。

**重要边界**：HV5622 的 VDD 静态电流、输出低电平电压 Von、PQFP-44 热阻 Rth_ja
尚未从手册核实（见 source_register），本复核全部用参数区间 + 敏感性表达，
不把假设值写成"已验证数据"。结论只能作为 H06 温升实测的预期范围。

输出：docs/thermal_review.md / .json
运行：python design/thermal_review.py
"""
import csv
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
S1 = os.path.join(ROOT, "sim", "results", "csv_S1.csv")

I_CH = 2.36e-3                 # A，H02 期望工作点中点
VDD = 11.45                    # V，DRV_VDD
ON_PER_DEV = 3                 # 每片 HV5622 同时导通通道数（六管静态驱动，每管 1 路）
IQ_RANGE = (1e-3, 3e-3, 5e-3)  # A，VDD 静态电流假设区间（待手册核实）
VON_RANGE = (1.0, 2.0, 3.0)    # V，输出低电平电压假设区间（待手册核实）
RTH_RANGE = (40, 60, 80)       # °C/W，PQFP-44 热阻假设区间（待手册核实）


def inrush_stats():
    rows = list(csv.DictReader(open(S1, encoding="utf-8")))
    t = np.array([float(r["t_ms"]) for r in rows]) * 1e-3
    il = np.array([float(r["iL_mA"]) for r in rows]) * 1e-3
    # 启动窗口：前 60 ms（软启动 + 输出建立）
    m = t < 0.06
    tt, ii = t[m], np.clip(il[m], 0, None)
    # I²t：只统计超 1.5 A 保持电流的区间（PPTC 关注）
    h = ii[ii > 1.5]
    i2t = float(np.trapezoid(np.clip(ii, 0, None) ** 2, tt))
    over = float(np.trapezoid((ii > 1.5).astype(float), tt))
    return dict(peak_A=float(ii.max()), i2t_A2s=i2t, over1p5_s=over,
                sample_ms=float(tt[np.argmax(ii)] * 1e3))


def hv5622_thermal():
    out = []
    for iq in IQ_RANGE:
        for von in VON_RANGE:
            p_out = ON_PER_DEV * I_CH * von
            p_q = VDD * iq
            p = p_out + p_q
            out.append(dict(iq_mA=iq * 1e3, von_V=von, p_out_mW=p_out * 1e3,
                            p_q_mW=p_q * 1e3, p_total_mW=p * 1e3,
                            rise_C={r: p * r for r in RTH_RANGE}))
    return out


def main():
    stats = inrush_stats()
    therm = hv5622_thermal()
    worst = max(therm, key=lambda r: r["p_total_mW"])
    best = min(therm, key=lambda r: r["p_total_mW"])
    rise_hi = max(worst["rise_C"].values())
    rise_lo = min(best["rise_C"].values())

    # PPTC 判据：I²t 与超保持电流时间
    i2t_ok = stats["i2t_A2s"] < 0.1        # 保守取典型 1812 PPTC I²t 下限，需手册确认
    hold_ok = stats["over1p5_s"] < 0.05    # 超 1.5 A 时间 <50 ms（自恢复保险丝不动作的量级）

    lines = ["# 热与浪涌复核（HV5622 功耗 / PPTC 启动浪涌）", "",
             "> 本复核的器件参数（HV5622 静态电流、Von、PQFP-44 Rth_ja、PPTC I²t）**尚未从手册核实**，"
             "全部用参数区间表达；结论只作 H06 实测的预期范围，不是验证数据。", "",
             "## 1. HV5622 驱动 IC 功耗与温升估算", "",
             f"- 静态驱动：每管恒有 1 路阴极导通 → 每片 HV5622 同时导通 **{ON_PER_DEV}** 路；",
             f"- 单通道电流 **{I_CH*1e3:.2f} mA**（H02 期望 1.5–3 mA 中点），DRV_VDD = {VDD} V；",
             "", "| 假设 VDD 静态电流 | 假设 Von | 导通损耗 | 静态损耗 | 合计 | 温升 @Rth=40/60/80 °C/W |",
             "|---|---|---|---|---|---|"]
    for r in therm:
        lines.append(f"| {r['iq_mA']:.0f} mA | {r['von_V']:.1f} V | {r['p_out_mW']:.1f} mW | "
                     f"{r['p_q_mW']:.0f} mW | **{r['p_total_mW']:.0f} mW** | "
                     + " / ".join(f"{v:.1f}" for v in r["rise_C"].values()) + " °C |")
    lines += ["", f"- 估算温升范围 **{rise_lo:.1f}–{rise_hi:.1f} °C**（环境 25 °C → 结温约 "
              f"{25+rise_lo:.0f}–{25+rise_hi:.0f} °C），**远低于常规 125 °C 结温上限**；",
              "- 结论：HV5622 热风险低（60 路并非同时导通，静态驱动只有 6 路同时导通）；"
              "但仍需 H06 实测 U21/U22 表面温升与 VDD 电流，确认手册参数。", "",
              "## 2. PPTC 与启动浪涌（来自行为模型 S1 波形）", "",
              f"- 启动电感电流峰值 **{stats['peak_A']:.2f} A**（{stats['sample_ms']:.1f} ms）；",
              f"- 启动 60 ms 内 ∫i²dt ≈ **{stats['i2t_A2s']:.4f} A²·s**；"
              f"超 1.5 A 持续时间 ≈ **{stats['over1p5_s']*1e3:.1f} ms**；",
              f"- 判据（工程经验量级，待手册确认）：I²t < 0.1 A²·s（典型 1812 PPTC 下限），"
              f"超保持电流时间 < 50 ms → "
              f"**{'通过（预期不误动作）' if i2t_ok and hold_ok else '不通过，需换更大保持电流或延时保险丝'}**",
              "", "| 项 | 结果 | 判据 | 结论 |", "|---|---|---|---|",
              f"| 峰值电流 | {stats['peak_A']:.2f} A | PPTC 1.5 A 保持（短时可超） | 需实测波形 |",
              f"| I²t | {stats['i2t_A2s']:.4f} A²·s | <0.1（典型 1812 PPTC 下限） | "
              f"{'PASS' if i2t_ok else 'FAIL'} |",
              f"| 超 1.5 A 时间 | {stats['over1p5_s']*1e3:.1f} ms | <50 ms | "
              f"{'PASS' if hold_ok else 'FAIL'} |",
              "", "## 3. 待关闭项", "",
              "- **PPTC 手册 I²t / 触发时间曲线**未核实 → 新增 open_issues I-25；H05/H06 实测必须记录启动波形；",
              "- HV5622 手册的 VDD 静态电流、Von、PQFP-44 热阻未核实 → 实测 U21/U22 温升与 VDD 电流；",
              "- 本复核不改变任何 BOM 选型；若实测温升或 PPTC 误动作，按 D-29/CHANGELOG 流程变更。"]
    open(os.path.join(DOC, "thermal_review.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(hv5622=therm, inrush=stats,
                   conclusion=dict(rise_C_range=[rise_lo, rise_hi],
                                   i2t_ok=i2t_ok, hold_ok=hold_ok)),
              open(os.path.join(DOC, "thermal_review.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"thermal review: 温升 {rise_lo:.1f}–{rise_hi:.1f} °C；"
          f"启动峰值 {stats['peak_A']:.2f} A；I²t {stats['i2t_A2s']:.4f} A²s；"
          f"超1.5A {stats['over1p5_s']*1e3:.1f} ms")
    print("wrote docs/thermal_review.md/.json")


if __name__ == "__main__":
    main()
