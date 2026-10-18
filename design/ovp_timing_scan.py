# -*- coding: utf-8 -*-
"""OVP 时序回归：复位脉冲宽度扫描 + 锁存保持时间。

背景：OVP 锁存由分立 SCR（Q21/Q22）实现，Q25 由 MCU GPIO18 脉冲复位。
"复位脉冲多窄才可靠"、"不复位时锁存能保持多久"是 H06 实测前必须知道的时序窗口。
本脚本用 `sim/boost_ovp_logic.cir` 的同一行为模型，把复位脉冲宽度参数化扫描。

输出：docs/ovp_timing.md + docs/ovp_timing.csv + sim/results/ovp_timing.png
运行：python design/ovp_timing_scan.py
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))

import numpy as np                      # noqa: E402
import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402
import minispice as ms                  # noqa: E402

DOC = os.path.join(ROOT, "docs")
RES = os.path.join(ROOT, "sim", "results")
BASE = os.path.join(ROOT, "sim", "boost_ovp_logic.cir")
H = 20e-6
TSTOP = 0.9


def template():
    return open(BASE, encoding="utf-8").read()


def with_pulse(pw_s):
    """复位脉冲宽度 pw_s；pw_s<=0 表示不复位（VRST 恒 0）。"""
    s = template()
    if pw_s <= 0:
        s = s.replace("VRST  reset 0 PULSE(0 1 0.6 1m 1m 5m 100)",
                      "VRST  reset 0 DC 0")
    else:
        s = s.replace("VRST  reset 0 PULSE(0 1 0.6 1m 1m 5m 100)",
                      f"VRST  reset 0 PULSE(0 1 0.6 1m 1m {pw_s:g} 100)")
    s = s.replace(".tran 20u 1.2", f".tran {H:g} {TSTOP}")
    s = s.replace(".save v(out) v(latch) v(ovp) v(en) v(ci)",
                  ".save v(out) v(latch) v(ovp) v(en)")
    return s


def run(pw_s):
    c = ms.Circuit().parse(with_pulse(pw_s))
    recs = c.run()
    t = np.array([r["t"] for r in recs])
    vo = np.array([r["v(out)"] for r in recs])
    latch = np.array([r["v(latch)"] for r in recs])
    trip = np.where(vo >= 198.8)[0]
    first_trip = float(t[trip[0]]) if len(trip) else None
    # 只在锁存已经建立（latch>0.9）之后判断释放；否则会误把初始 0 当成释放
    set_idx = np.where(latch > 0.9)[0]
    t_set = float(t[set_idx[0]]) if len(set_idx) else None
    after = t > (t_set + 0.005) if t_set is not None else np.zeros_like(t, dtype=bool)
    hold = bool(t_set is not None and np.all(latch[after] > 0.9))
    rel_idx = np.where(after & (latch < 0.2))[0]
    rel = len(rel_idx) > 0
    rel_t = float(t[rel_idx[0]]) if rel else None
    retrip = bool(rel and np.any(latch[(t > (rel_t + 0.002))] > 0.9))
    return dict(pw_ms=pw_s * 1e3 if pw_s > 0 else 0.0,
                first_trip_ms=None if first_trip is None else round(first_trip * 1e3, 2),
                hold=hold, release=rel,
                release_ms=None if rel_t is None else round(rel_t * 1e3, 2),
                relatch=retrip, vmax=float(vo.max()), final_latched=bool(latch[-1] > 0.9),
                t=t, vo=vo, latch=latch)


def main():
    rows = []
    cases = [0.0, 0.2e-3, 0.5e-3, 1e-3, 2e-3, 5e-3, 10e-3]
    for pw in cases:
        r = run(pw)
        rows.append(r)
        print(f"pw={r['pw_ms']:5.1f} ms  trip={r['first_trip_ms']} ms  "
              f"release={r['release']}  relatch={r['relatch']}  "
              f"vmax={r['vmax']:.2f} V  final_latched={r['final_latched']}")

    # 可靠复位的最小脉冲宽度（release 且 relatch，且不依赖 Vmax 超限）
    ok = [r for r in rows if r["pw_ms"] > 0 and r["release"] and r["relatch"]]
    min_pw = min((r["pw_ms"] for r in ok), default=None)
    norel = next((r for r in rows if r["pw_ms"] == 0.0), None)

    with open(os.path.join(DOC, "ovp_timing.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["reset_pulse_ms", "first_trip_ms", "latch_hold_no_reset",
                    "release", "release_ms", "relatch", "vmax_V", "final_latched"])
        for r in rows:
            w.writerow([f"{r['pw_ms']:.1f}", r["first_trip_ms"], r["hold"],
                        r["release"], r["release_ms"], r["relatch"],
                        f"{r['vmax']:.2f}", r["final_latched"]])

    lines = ["# OVP 时序回归：复位脉冲宽度 + 锁存保持", "",
             f"- 模型：`sim/boost_ovp_logic.cir`（行为保护逻辑），步长 {H*1e6:.0f} µs，"
             f"仿真 {TSTOP*1e3:.0f} ms",
             "- 场景：反馈断路故障使输出升到 OVP；0.6 s 发一次复位脉冲（宽度扫描）；"
             "故障不消除时观察是否再次锁存。", "",
             "## 结果", "",
             "| 复位脉冲宽度 | 首次触发 (ms) | 释放锁存 | 释放时刻 (ms) | 再次锁存 | 最大电压 (V) | 最终锁存 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        pw_label = "无复位" if r["pw_ms"] == 0 else f"{r['pw_ms']:.1f} ms"
        rel = "是" if r["release"] else "否"
        rel_t = r["release_ms"] if r["release_ms"] is not None else "—"
        re_ = "是" if r["relatch"] else "否"
        fin = "是" if r["final_latched"] else "否"
        lines.append(f"| {pw_label} | {r['first_trip_ms']} | {rel} | {rel_t} | "
                     f"{re_} | {r['vmax']:.2f} | {fin} |")
    lines += ["", "## 结论", "",
              f"- **不复位时锁存保持**：{'是（0.05 s 之后一直保持，输出安全泄放）' if norel and norel['hold'] else '否/需检查'}",
              f"- **可靠复位的最小脉冲宽度**：**{min_pw:.1f} ms**（更窄的脉冲可能无法释放锁存）"
              if min_pw is not None else "- **可靠复位的最小脉冲宽度**：扫描范围内未找到（需加宽脉冲或检查驱动）",
              f"- 复位后再次锁存：{'是' if all(r['relatch'] for r in rows if r['pw_ms'] > 0 and r['release']) else '部分'}（故障未消除时应再次保护）",
              "- 工程含义：MCU 复位脉冲需 ≥ 该最小宽度；固件应在 HV 低于 OVP 阈值后再执行复位，"
              "否则复位无效（等价 SCR 在 OVP 有效时不可关断）。",
              "",
              "## 边界", "",
              "本模型为行为级（非器件级 SCR）：忽略维持电流、门极触发延迟、结温与 dV/dt 误触发；"
              "上述时序窗口必须 H06 用实物验证并回填 `docs/evidence/H06_hv.csv`。"]
    open(os.path.join(DOC, "ovp_timing.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), dpi=130, sharex=True)
    for r in rows:
        if r["pw_ms"] in (0.0, 0.5, 2.0, 10.0):
            ax[0].plot(r["t"] * 1e3, r["vo"], lw=1.0,
                       label="no reset" if r["pw_ms"] == 0 else f"reset {r['pw_ms']:.1f} ms")
            ax[1].plot(r["t"] * 1e3, r["latch"], lw=1.0)
    ax[0].axhline(198.8, ls="--", color="r", lw=0.8)
    ax[0].set_ylabel("HV_BUS (V)")
    ax[0].set_title("OVP timing: reset pulse width vs latch/re-trip")
    ax[0].grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    ax[1].set_ylabel("latch (V)")
    ax[1].set_xlabel("time (ms)")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "ovp_timing.png"))
    plt.close(fig)
    print(f"\n最小可靠复位脉宽: {min_pw} ms；wrote docs/ovp_timing.md/.csv, sim/results/ovp_timing.png")


if __name__ == "__main__":
    main()
