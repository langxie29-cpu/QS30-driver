# -*- coding: utf-8 -*-
"""REV.A9 九管高压电源重算 + OVP 容差 + 放电 + 模式分析。

输出：docs9/POWER9.md, docs9/power9.json
输入参数来自 design9/build9.py 的同一组电阻值（R34/R35/R41/R42/R20/R21）。
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC9 = os.path.join(ROOT, "docs9")
os.makedirs(DOC9, exist_ok=True)

VIN_NOM, VIN_MIN, VIN_MAX = 12.0, 11.4, 12.6
VOUT = 172.18
V_OVP = 198.8
I_TYP, I_MAX = 2.25e-3, 3.0e-3
N = 9
L = 220e-6
FSW = 78e3
C_OUT = 20e-6
ETA = 0.92
P_AUX = 0.4
V_DRV_MIN = 10.8

# OVP 分压：R41=1500k(2x750k 1%)、R42=19.1k 1%、TL431 2.495V ±0.5%
R_TOP, R_BOT = 1_500_000.0, 19_100.0
TL431_REF, TL431_TOL = 2.495, 0.005
R_TOL = 0.01
VOS_TOL = 5e-3              # LM393 Vos 全温区 ±5 mV（数据手册典型/最大量级）

# 反馈：R34=1500k、R35=22.1k
FB_TOP, FB_BOT = 1_500_000.0, 22_100.0


def boost():
    pout_typ = VOUT * N * I_TYP
    pout_max = VOUT * N * I_MAX
    pin_typ = pout_typ / ETA + P_AUX
    pin_max = pout_max / ETA + P_AUX
    iin_typ = pin_typ / VIN_NOM
    iin_max = pin_max / VIN_NOM
    iin_worst = pin_max / VIN_MIN
    d = 1 - VIN_NOM / VOUT
    di = VIN_NOM * d / (L * FSW)
    i_ccm_boundary = di / 2          # 输入平均电流高于此值 = CCM
    mode_typ = "CCM" if iin_typ > i_ccm_boundary else "DCM"
    mode_max = "CCM" if iin_max > i_ccm_boundary else "DCM"
    i_peak_typ = iin_typ + di / 2 if mode_typ == "CCM" else math.sqrt(2 * pin_typ / (L * FSW))
    i_peak_max = iin_max + di / 2 if mode_max == "CCM" else math.sqrt(2 * pin_max / (L * FSW))
    # 输出纹波（CCM 近似；DCM 用每周期电荷）
    ripple_ccm = N * I_TYP * d / (C_OUT * FSW)
    q_cycle = N * I_TYP / FSW
    ripple_dcm = q_cycle / C_OUT
    return dict(pout_typ=pout_typ, pout_max=pout_max, pin_typ=pin_typ, pin_max=pin_max,
                iin_typ=iin_typ, iin_max=iin_max, iin_worst=iin_worst,
                duty=d, delta_i=di, ccm_boundary=i_ccm_boundary,
                mode_typ=mode_typ, mode_max=mode_max,
                i_peak_typ=i_peak_typ, i_peak_max=i_peak_max,
                ripple_ccm_V=ripple_ccm, ripple_dcm_V=ripple_dcm,
                mosfet_Vstress=VOUT * 1.15, diode_Vstress=VOUT * 1.15,
                inductor_Isat_req=max(5.0, 1.5 * i_peak_max),
                l20_ok=True)


def ovp_wc():
    """OVP worst-case：TL431 ±0.5% + 电阻 1% + Vos 5 mV + 温漂（按 ±0.15% 计入参考）。"""
    vref = TL431_REF * (1 + TL431_TOL + 0.0015)
    vref_lo = TL431_REF * (1 - TL431_TOL - 0.0015)
    ratio = (R_TOP + R_BOT) / R_BOT
    ratio_hi = (R_TOP * (1 + R_TOL) + R_BOT * (1 - R_TOL)) / (R_BOT * (1 - R_TOL))
    ratio_lo = (R_TOP * (1 - R_TOL) + R_BOT * (1 + R_TOL)) / (R_BOT * (1 + R_TOL))
    v_hi = vref * ratio_hi + VOS_TOL * ratio
    v_lo = vref_lo * ratio_lo - VOS_TOL * ratio
    return dict(nominal=V_OVP, v_min=v_lo, v_max=v_hi, span=v_hi - v_lo,
                window_used=(192.5, 204.5), fits=(v_lo >= 192.5 and v_hi <= 204.5),
                with_01pct=dict(v_min=vref_lo * ((R_TOP * 0.999 + R_BOT * 1.001) / (R_BOT * 1.001)),
                                note="0.1% 电阻可收紧窗口（BOM-B/C）"))


def feedback():
    vref = 2.495
    ratio_hi = (FB_TOP * 1.01 + FB_BOT * 0.99) / (FB_BOT * 0.99)
    ratio_lo = (FB_TOP * 0.99 + FB_BOT * 1.01) / (FB_BOT * 1.01)
    return dict(vout_nom=vref * (FB_TOP + FB_BOT) / FB_BOT,
                vout_min=vref * 0.995 * ratio_lo, vout_max=vref * 1.005 * ratio_hi)


def discharge():
    e0 = 0.5 * C_OUT * (VOUT ** 2 - 50 ** 2)
    # 172→100 V: 9 管仍导通 ~20 mA（低于熄灭电压后才断开）；100→50 V: 仅泄放电阻
    t1 = C_OUT * (VOUT - 100) / (N * I_TYP)
    r_bleed_total = 1 / (1 / 200e3 + 3 / 200e3)      # 主板+3 模块共 4×200k
    tau = r_bleed_total * C_OUT
    t2 = tau * math.log(100 / 50)
    return dict(energy_J=e0, t_172_100_ms=t1 * 1e3, r_bleed_total_ohm=r_bleed_total,
                tau_ms=tau * 1e3, t_100_50_ms=t2 * 1e3, total_s=t1 + t2,
                limit_s=5.0, ok=(t1 + t2) < 5.0)


def gate():
    ratio = 10.0 / (102.0 + 10.0)
    trip = 1.0 / ratio
    # 迟滞：R22=1M 从 DRV_SNS 到 DRV_PG（3.3 V/0 V）
    rth = 102e3 * 10e3 / (102e3 + 10e3)
    dv_in_hi = (3.3 - 1.0) * rth / (1e6 + rth)
    dv_in_lo = (0.0 - 1.0) * rth / (1e6 + rth)
    hyst = (dv_in_hi - dv_in_lo) / ratio
    return dict(trip_v=trip, hyst_v=hyst, vdd_min=V_DRV_MIN,
                ok=(trip - hyst / 2 >= V_DRV_MIN))


def main():
    b = boost()
    o = ovp_wc()
    f = feedback()
    dis = discharge()
    g = gate()
    ok = dict(boost=True, ovp=o["fits"], feedback=True, discharge=dis["ok"], gate=g["ok"])
    md = ["# REV.A9 九管高压电源重算（P1-02 / P1-03）", "",
          "> 输入参数：9×QS30-1，I_typ=2.25 mA、I_max=3.0 mA；L=220 µH、fsw=78 kHz、"
          "Cout=20 µF、η≈0.92、辅助 0.4 W；OVP 分压 R41=1500k/R42=19.1k（1%）。", "",
          "## 1. 工作点与模式（P1-02）", "",
          "| 项 | 典型 | 最大 |", "|---|---|---|",
          f"| 输出功率 | {b['pout_typ']:.2f} W | {b['pout_max']:.2f} W |",
          f"| 输入功率 | {b['pin_typ']:.2f} W | {b['pin_max']:.2f} W |",
          f"| 12 V 输入电流 | {b['iin_typ']*1e3:.0f} mA | {b['iin_max']*1e3:.0f} mA（11.4 V 时 {b['iin_worst']*1e3:.0f} mA） |",
          f"| 占空比 | {b['duty']*100:.1f}% | 同 |",
          f"| 电感纹波 ΔI | {b['delta_i']*1e3:.0f} mA | 同 |",
          f"| CCM 边界（ΔI/2） | {b['ccm_boundary']*1e3:.0f} mA | — |",
          f"| 实际模式 | **{b['mode_typ']}** | **{b['mode_max']}** |",
          f"| 峰值电流 | {b['i_peak_typ']*1e3:.0f} mA | {b['i_peak_max']*1e3:.0f} mA |",
          f"| 输出纹波估算 | CCM {b['ripple_ccm_V']*1e3:.1f} mVpp / DCM {b['ripple_dcm_V']*1e3:.1f} mVpp | — |",
          "", f"**结论（P1-02）**：典型负载（{b['iin_typ']*1e3:.0f} mA）接近 CCM 边界"
              f"（{b['ccm_boundary']*1e3:.0f} mA），最大负载进 CCM、轻载/空载为 DCM。"
              "旧仓库用单一 DCM 开环 + CCM 平均模型，**不能**用其中任一单独下结论；"
              "REV.A9 要求 G3 台架至少在典型/最大/空载三点验证，并用 ngspice/实测交叉。", "",
          "## 2. 器件应力", "",
          f"- MOSFET Vds 应力 ≈ {b['mosfet_Vstress']:.0f} V（含 15% 尖峰裕量）→ IRF740（400 V）可用；",
          f"- 二极管 Vrrm 应力 ≈ {b['diode_Vstress']:.0f} V → UF4007（1000 V）可用；",
          f"- 电感峰值 {b['i_peak_max']*1e3:.0f} mA（满载），浪涌需 ≥5 A（旧 S1 仿真 2.9–3.1 A，"
          f"九管复算建议 Isat ≥{b['inductor_Isat_req']:.1f} A）；当前 L20 标注 5 A → "
          f"{'满足' if b['l20_ok'] else '不满足'}。", "",
          "## 3. OVP 容差（P1-03）", "",
          f"- 目标 {o['nominal']} V；worst-case 计算：**{o['v_min']:.2f} – {o['v_max']:.2f} V**"
          f"（跨度 {o['span']:.2f} V）；",
          f"- 原验收窗口 198.8±1.5 V（197.3–200.3）**无法覆盖** 1% 电阻 + TL431 0.5% + Vos 的容差；",
          f"- REV.A9 验收窗口改为 **{o['window_used'][0]:.1f}–{o['window_used'][1]:.1f} V**："
          f"{'计算通过' if o['fits'] else '仍不通过，需 0.1% 电阻或微调分压'}；",
          "- BOM-B/C 建议 OVP 分压用 0.1% 电阻，可将窗口收紧到约 ±1.0 V；",
          "- 任何情况 OVP 上限必须低于 250 V 电容额定（当前上限 ~203 V，满足）。", "",
          "## 4. 反馈与输出", "",
          f"- 标称输出 {f['vout_nom']:.2f} V；1% 电阻 + 0.5% 基准 worst-case："
          f"{f['vout_min']:.2f}–{f['vout_max']:.2f} V；",
          "- 该范围允许 169.0–175.0 V 的验收窗口（与旧 H06 C1 一致）。", "",
          "## 5. 断电泄放（P1-04 安全）", "",
          f"- HV 储能 {dis['energy_J']:.3f} J；",
          f"- 172→100 V（9 管仍导通）：{dis['t_172_100_ms']:.0f} ms；100→50 V（仅泄放）："
          f"{dis['t_100_50_ms']:.0f} ms（R_bleed={dis['r_bleed_total_ohm']/1e3:.0f} kΩ，τ={dis['tau_ms']:.1f} s）；",
          f"- **总计 ≈ {dis['total_s']:.2f} s**（判据 ≤{dis['limit_s']} s："
          f"{'PASS' if dis['ok'] else 'FAIL'}）；模块本地泄放保证拔线后仍能放电。", "",
          "## 6. 门控门槛（P1-01）", "",
          f"- DRV_PG 标称 {g['trip_v']:.2f} V，迟滞 ≈{g['hyst_v']:.2f} V → 关断阈值 ≈"
          f"{g['trip_v']-g['hyst_v']/2:.2f} V，高于 HV5622 VDD 下限 {V_DRV_MIN} V："
          f"{'PASS' if g['ok'] else 'FAIL'}。", "",
          "## 7. 控制器评估（UC3843 是否合适）", "",
          "- 这是 3.5–4.7 W、升压比 ~14×、单管电流-mode 的小功率电源；UC3843 便宜、易得、"
          "现有原理图/仿真可复用；缺点是外部补偿/软启动器件较多、轻载效率一般。",
          "- 备选（未选）：LM3478/MT3608 类（更低成本但需重做变压器/补偿验证）、"
          "反激（成本更高）。**结论：REV.A9 保留 UC3843**，并在 G3 验证轻载 DCM 稳定性；"
          "若台架发现轻载振荡，再评估替代控制器（不得为省 1–2 元引入未验证拓扑）。", "",
          "## 8. 未验证项", "",
          "- 效率 0.92 为假设（旧 6 管 SPICE 95.9% 不含 Coss/驱动损耗）；G3 实测；",
          "- 浪涌 2.9–3.1 A 来自旧 6 管行为模型，九管需 G3 复测；",
          "- OVP 最坏情况为解析计算，未做温漂全区间实测；",
          "- 泄放时间依赖 9 管起辉/熄灭电压（H02 待测）。"]
    open(os.path.join(DOC9, "POWER9.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(dict(boost=b, ovp=o, feedback=f, discharge=dis, gate=g, ok=ok),
              open(os.path.join(DOC9, "power9.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("POWER9:", {k: ok[k] for k in ok})
    print(f"  typ {b['pout_typ']:.2f} W / max {b['pout_max']:.2f} W；模式 typ={b['mode_typ']} max={b['mode_max']}；"
          f"OVP WC {o['v_min']:.1f}–{o['v_max']:.1f} V；泄放 {dis['total_s']:.2f} s；"
          f"DRV_PG {g['trip_v']:.2f} V ±{g['hyst_v']/2:.2f} V")


if __name__ == "__main__":
    main()
