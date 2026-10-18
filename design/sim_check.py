# -*- coding: utf-8 -*-
"""升压仿真数值收敛性检查（独立于主仿真结果的证据）。

目的：证明 design/sim_boost.py 的结论不是某一步长下的偶然数值结果。
方法：同一场景用 3 种积分步长（开关周期的 1/40、1/80、1/160）重复运行，
      比较稳态电压、峰值、启动过冲、OVP 触发时刻；相对偏差应随步长减小而收敛。

输出：sim/results/convergence.json, sim/results/convergence.md
运行：python design/sim_check.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_boost as sb

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "sim", "results")
os.makedirs(OUT, exist_ok=True)

DIVS = (40, 80, 160)


def run_case(div, kind):
    sb.DT = sb.TS / float(div)
    if kind == "startup6":
        s = sb.scenario("startup6", 6, 0.30)
    elif kind == "load6":
        s = sb.scenario("load6", 6, 0.25)
    elif kind == "fb_open":
        s = sb.scenario("fb_open", 6, 0.40, fb_open=True)
    else:
        raise ValueError(kind)
    m = s.metrics()
    return dict(div=div, kind=kind,
                vout_mean=round(m["vout_mean"], 3),
                vout_max=round(m["vout_max"], 3),
                peak_iL_A=round(m["peak_iL_A"], 4),
                ovp_trip_ms=(None if m.get("ovp_trip_t_ms") is None
                             else round(m["ovp_trip_t_ms"], 3)),
                latch=m.get("latch"))


def main():
    rows = []
    for kind in ("startup6", "load6", "fb_open"):
        for div in DIVS:
            rows.append(run_case(div, kind))
    # 以最细步长作为参考，计算相对偏差
    ref = {r["kind"]: r for r in rows if r["div"] == DIVS[-1]}
    for r in rows:
        b = ref[r["kind"]]
        for k in ("vout_mean", "vout_max"):
            r["d_" + k + "_pct"] = round(100.0 * (r[k] - b[k]) / b[k], 3)
        r["d_peak_iL_pct"] = round(100.0 * (r["peak_iL_A"] - b["peak_iL_A"])
                                   / b["peak_iL_A"], 3)

    json.dump(dict(divs=DIVS, reference_div=DIVS[-1], rows=rows),
              open(os.path.join(OUT, "convergence.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    lines = ["# 升压仿真数值收敛性检查", "",
             "同一场景在 3 种积分步长下重复运行；以最细步长（Ts/160）为参考。", "",
             "| 场景 | 步长 | 稳态电压 (V) | 峰值 (V) | 峰值电流 (A) | OVP 触发 (ms) | ΔV稳态 | ΔV峰值 | ΔI峰值 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| {kind} | Ts/{div} | {vout_mean} | {vout_max} | {peak_iL_A} | "
                     "{ovp} | {d1}% | {d2}% | {d3}% |".format(
                         kind=r["kind"], div=r["div"],
                         vout_mean=r["vout_mean"], vout_max=r["vout_max"],
                         peak_iL_A=r["peak_iL_A"],
                         ovp="—" if r["ovp_trip_ms"] is None else r["ovp_trip_ms"],
                         d1=r["d_vout_mean_pct"], d2=r["d_vout_max_pct"],
                         d3=r["d_peak_iL_pct"]))
    lines += ["", "判据：最粗步长（Ts/40）相对参考的稳态电压偏差应 <1%，"
              "峰值电压偏差 <2%，峰值电流偏差 <5%；否则需要减小步长后重跑。"]
    open(os.path.join(OUT, "convergence.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
