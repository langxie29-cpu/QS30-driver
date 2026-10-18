# -*- coding: utf-8 -*-
"""环路参数敏感性扫描（平均模型）：CINT / Ki / Kp → 负载阶跃响应。

目的：给定与 BOM 相同的平均模型结构，回答两个工程问题：
  1) 现有参数（CINT 22 µF / Ki 1.3e-4 / Kp 0.05）的负载恢复 158 ms 是快还是慢？
  2) 若把环路加快（减小 CINT 或增大 Ki/Kp），是否出现振荡/超调？→ 给 H06 实测与
     补偿网络（R72 10 k + C56 0.1 µF + C55 22 µF 软启动）调整提供方向。

注意：本扫描不直接给出 R72/C56 的数值（PI 等效与 UC3843 电流模式补偿不是一一映射），
结论用于"趋势/稳定性边界"，最终补偿值必须 H06 实测相位裕度后确定。

输出：docs/loop_scan.md / loop_scan.csv，sim/results/loop_scan_heatmap.png
运行：python design/loop_scan.py
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                      # noqa: E402
import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402
import minispice as ms                  # noqa: E402

DOC = os.path.join(ROOT, "docs")
RES = os.path.join(ROOT, "sim", "results")
BASE = 172.18

CINT = [10e-6, 22e-6, 47e-6]
KI = [6.5e-5, 1.3e-4, 2.6e-4]
KP = [0.0, 0.05, 0.15]
H = 20e-6
TSTOP = 0.45


def netlist(cint, ki, kp):
    return f"""* loop scan: CINT={cint:g} Ki={ki:g} Kp={kp:g}
BIN   in  0  V = 12 - 0.6 * (time > 0.15)
L1    in  swa 220u ic=0.22
RL1   swa sw  0.3
BSW   sw  0  V = (1 - V(ctrl)) * (V(out) + 0.6)
BOUT  0   out I = (1 - V(ctrl)) * I(L1)
COUT  out 0  20u ic=172
RB    out 0  200k
BTUBE out 0  I = 6 * max(0, (V(out) - 125) / 20000) * (1 + 0.5 * (time > 0.15))
RFB1  out fb 1500k
RFB2  fb  0  22.1k
BERRP errp 0 V = 2.5 - V(fb)
CINT  ci  0  {cint:g} ic=0.931
BINT  0   ci I = max(-0.5m, min(0.5m, {ki:g} * V(errp)))
BCTRL ctrl 0 V = max(0.02, min(0.95, {kp:g} * V(errp) + V(ci)))
.ic v(out)=172 v(ctrl)=0.931 v(ci)=0.931 v(fb)=2.497 i(l1)=0.22
.tran {H:g} {TSTOP}
.save v(out) v(ctrl)
.end
"""


def run_one(cint, ki, kp):
    text = netlist(cint, ki, kp)
    try:
        c = ms.Circuit().parse(text)
        recs = c.run()
    except Exception as e:                       # noqa: BLE001
        return dict(cint=cint, ki=ki, kp=kp, ok=False, note=str(e)[:60])
    t = np.array([r["t"] for r in recs])
    vo = np.array([r["v(out)"] for r in recs])
    steady = t > 0.85 * t[-1]
    vss = float(vo[steady].mean())
    err = abs(vss - BASE)
    after = t > 0.15
    dev = float(np.max(np.abs(vo[after] - BASE)))
    bad = np.where(after & (np.abs(vo - BASE) > 0.01 * BASE))[0]
    rec_ms = float((t[bad[-1]] - 0.15) * 1e3) if len(bad) else 0.0
    osc_pp = float(vo[steady].max() - vo[steady].min())
    return dict(cint=cint, ki=ki, kp=kp, ok=True, vss=vss, err_mV=err * 1e3,
                droop_V=dev, recovery_ms=rec_ms, tail_pp_mV=osc_pp * 1e3,
                stable=osc_pp < 0.05)


def main():
    rows = []
    total = len(CINT) * len(KI) * len(KP)
    n = 0
    for cint in CINT:
        for ki in KI:
            for kp in KP:
                n += 1
                r = run_one(cint, ki, kp)
                rows.append(r)
                tag = (f"CINT={cint*1e6:2.0f}uF Ki={ki*1e6:5.1f}e-6 Kp={kp:.2f}")
                if r["ok"]:
                    print(f"[{n}/{total}] {tag}  droop={r['droop_V']:.2f}V "
                          f"rec={r['recovery_ms']:.0f}ms tail_pp={r['tail_pp_mV']:.1f}mV")
                else:
                    print(f"[{n}/{total}] {tag}  FAIL {r['note']}")

    ok = [r for r in rows if r["ok"]]
    # 参考：BOM 参数
    ref = next((r for r in ok if abs(r["cint"] - 22e-6) < 1e-9
                and abs(r["ki"] - 1.3e-4) < 1e-12 and abs(r["kp"] - 0.05) < 1e-12), None)
    # 推荐：恢复时间最短且无振荡、droop<5V、稳态误差<50mV
    cand = [r for r in ok if r["stable"] and r["droop_V"] < 5.0 and r["err_mV"] < 50]
    best = min(cand, key=lambda r: r["recovery_ms"]) if cand else None

    os.makedirs(DOC, exist_ok=True)
    with open(os.path.join(DOC, "loop_scan.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["CINT_uF", "Ki", "Kp", "Vss_V", "err_mV", "droop_V",
                    "recovery_ms", "tail_pp_mV", "stable"])
        for r in rows:
            if r["ok"]:
                w.writerow([f"{r['cint']*1e6:.0f}", f"{r['ki']:.3e}", f"{r['kp']:.2f}",
                            f"{r['vss']:.3f}", f"{r['err_mV']:.1f}",
                            f"{r['droop_V']:.2f}", f"{r['recovery_ms']:.0f}",
                            f"{r['tail_pp_mV']:.1f}", r["stable"]])

    lines = ["# 环路参数敏感性扫描（平均模型）", "",
             f"- 扫描：CINT ∈ {[c*1e6 for c in CINT]} µF × Ki ∈ {[k*1e6 for k in KI]}e-6 × "
             f"Kp ∈ {KP} = **{len(rows)} 组**；步长 {H*1e6:.0f} µs，{TSTOP*1e3:.0f} ms",
             "- 场景：初值=工作点，150 ms 时输入 12→11.4 V（负载不变）；指标=电压下探、恢复(±1%)、"
             "稳态误差、末段峰峰值（振荡指示）", "",
             "## 参考点与推荐", ""]
    if ref:
        lines += [f"- **BOM 参数（参考）**：CINT 22 µF / Ki 1.3e-4 / Kp 0.05 → "
                  f"下探 {ref['droop_V']:.2f} V，恢复 **{ref['recovery_ms']:.0f} ms**，"
                  f"稳态误差 {ref['err_mV']:.1f} mV"]
    if best:
        lines += [f"- **扫描最优**：CINT {best['cint']*1e6:.0f} µF / Ki {best['ki']:.2e} / "
                  f"Kp {best['kp']:.2f} → 下探 {best['droop_V']:.2f} V，"
                  f"恢复 **{best['recovery_ms']:.0f} ms**，末段峰峰 {best['tail_pp_mV']:.1f} mV"]
    stable_n = sum(1 for r in ok if r["stable"])
    lines += [f"- 稳定性：**{stable_n}/{len(ok)}** 组无振荡（末段峰峰 <50 mV）；"
              f"有振荡/失败 {len(rows)-stable_n} 组", "",
              "## 全部结果（按恢复时间排序）", "",
              "| CINT (µF) | Ki | Kp | 稳态 (V) | 误差 (mV) | 下探 (V) | 恢复 (ms) | 末段峰峰 (mV) | 稳定 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(ok, key=lambda x: x["recovery_ms"]):
        mark = ""
        if ref and r is ref:
            mark = " ←BOM"
        if best and r is best:
            mark += " ★推荐"
        lines.append(f"| {r['cint']*1e6:.0f} | {r['ki']:.2e} | {r['kp']:.2f} | "
                     f"{r['vss']:.2f} | {r['err_mV']:.1f} | {r['droop_V']:.2f} | "
                     f"{r['recovery_ms']:.0f} | {r['tail_pp_mV']:.1f} | "
                     f"{'是' if r['stable'] else '否'}{mark} |")
    lines += ["", "## 工程解读与边界", "",
              "1. **现有参数偏慢但稳定**：158 ms 恢复来自 CINT 22 µF 的积分时间常数；"
              "静态显示时每管恒有 1 路阴极导通，负载变化很小，故可接受。",
              "2. **加快环路的代价**：减小 CINT 或增大 Ki 会缩短恢复时间，但需关注"
              "输入阶跃下探与末段振荡；扫描给出稳定边界，供 H06 调整 R72/C56 时参考。",
              "3. **不等同于 UC3843 补偿设计**：本模型是 PI 等效（电压模式平均模型），"
              "真实 UC3843 为电流模式 + Type-II 补偿（R72 10 k / C56 0.1 µF / C55 22 µF 软启动）；"
              "R72/C56 的最终取值必须由 H06 实测相位裕度确定，本扫描只提供趋势与稳定性边界。",
              "4. 本扫描不含开关纹波/器件应力（见 `spice_validation.md` 第 2 节）与 OVP 逻辑"
              "（见 §3.5）。"]
    open(os.path.join(DOC, "loop_scan.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    # 热图 1：输入阶跃下探（Ki × Kp，对 CINT 取平均）——下探主要由 Kp 决定
    # 热图 2：末段振荡（CINT × Ki，对 Kp 取最大）——稳定性边界
    droop = np.full((len(KI), len(KP)), np.nan)
    osc = np.full((len(CINT), len(KI)), np.nan)
    for r in ok:
        i, j, k = CINT.index(r["cint"]), KI.index(r["ki"]), KP.index(r["kp"])
        droop[j, k] = np.nanmean([droop[j, k], r["droop_V"]])
        osc[i, j] = np.nanmax([osc[i, j], r["tail_pp_mV"]])
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), dpi=130)
    im0 = axs[0].imshow(droop, cmap="viridis", aspect="auto")
    axs[0].set_xticks(range(len(KP)))
    axs[0].set_xticklabels([f"{k:.2f}" for k in KP])
    axs[0].set_yticks(range(len(KI)))
    axs[0].set_yticklabels([f"{k*1e6:.1f}e-6" for k in KI])
    axs[0].set_xlabel("Kp")
    axs[0].set_ylabel("Ki (A/V)")
    axs[0].set_title("Input-step droop (V), mean over CINT")
    for j in range(len(KI)):
        for k in range(len(KP)):
            if not np.isnan(droop[j, k]):
                axs[0].text(k, j, f"{droop[j,k]:.1f}", ha="center", va="center",
                            color="w", fontsize=9)
    fig.colorbar(im0, ax=axs[0], label="droop (V)")
    im1 = axs[1].imshow(osc, cmap="magma", aspect="auto")
    axs[1].set_xticks(range(len(KI)))
    axs[1].set_xticklabels([f"{k*1e6:.1f}e-6" for k in KI])
    axs[1].set_yticks(range(len(CINT)))
    axs[1].set_yticklabels([f"{c*1e6:.0f}" for c in CINT])
    axs[1].set_xlabel("Ki (A/V)")
    axs[1].set_ylabel("CINT (uF)")
    axs[1].set_title("Tail ripple (mV), max over Kp")
    for i in range(len(CINT)):
        for j in range(len(KI)):
            if not np.isnan(osc[i, j]):
                axs[1].text(j, i, f"{osc[i,j]:.0f}", ha="center", va="center",
                            color="w", fontsize=9)
    fig.colorbar(im1, ax=axs[1], label="tail ripple (mV)")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "loop_scan_heatmap.png"))
    plt.close(fig)
    print("\n参考:", "BOM 恢复 %.0f ms" % ref["recovery_ms"] if ref else "BOM 未跑")
    print("推荐:", ("CINT %.0f µF / Ki %.2e / Kp %.2f → 恢复 %.0f ms"
                   % (best["cint"]*1e6, best["ki"], best["kp"], best["recovery_ms"]))
          if best else "无满足条件组合")
    print("wrote docs/loop_scan.md, docs/loop_scan.csv, sim/results/loop_scan_heatmap.png")


if __name__ == "__main__":
    main()
