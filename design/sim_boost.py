# -*- coding: utf-8 -*-
"""QS30-6 REV.A 升压 + 独立过压保护：可运行的开关级（行为模型）仿真。

模型边界（必须与结论一起引用）：
  * UC3843 用行为模型：峰值电流模式、固定 78 kHz、COMP 软启动斜率
    dV/dt = 1 mA / 22 µF（取自 UC3843 COMP 内部 1 mA 上拉 + C55）；
  * MOSFET 用 Rds_on + 体二极管，二极管用 Vf + 反向恢复忽略，
    电感含 DCR，输出电容含 ESR；
  * QS30-1 负载用“起辉阈值 + 20 kΩ 限流”的分段线性模型；
  * OVP 用理想比较器 + 分立 SCR 锁存（阈值 190 V，取自 2.5 V × 1520/20）；
  * 这不是器件级 SPICE：开关损耗、寄生振铃、磁芯损耗、温升均未建模。
    ngspice 网表见 sim/boost_uc3843.cir（本机未安装 ngspice，未执行）。

运行：python sim_boost.py
输出：sim/results/*.csv, sim/results/*.png, sim/results/summary.json
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for _f in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
    if os.path.exists(_f):
        font_manager.fontManager.addfont(_f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=_f).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "sim", "results")
os.makedirs(OUT, exist_ok=True)

# ---------------- 电路参数（与网表 BOM 一致） ----------------
P = dict(
    Vin=12.0, L=220e-6, L_dcr=0.30, fsw=78e3, Vf=1.0, Rds=0.55,
    Cout=20e-6, Cout_esr=0.50, Rbleed=200e3,
    R_fb_top=1.50e6, R_fb_bot=22.1e3, Vref=2.5, Vref_hyst=0.0,
    Ilim=1.00, Vcomp_min=0.50, Vcomp_max=4.50,
    comp_softstart_slope=1e-3 / 22e-6,      # 45.45 V/s
    ovp_trip=198.8,
    tube_R=20e3, tube_Vop=125.0, tube_Vstrike=150.0,
    n_tubes=6,
    tps=1e-6,       # 采样步长
)
TS = 1.0 / P["fsw"]
DT = TS / 80.0


def rload_current(v, n_tubes):
    """QS30-1 分段线性负载：起辉前几乎不导通，起辉后按 20 kΩ 限流。"""
    if n_tubes <= 0:
        return 0.0
    if v < P["tube_Vstrike"]:
        return 1e-6 * n_tubes          # 起辉前漏电流
    return n_tubes * (v - P["tube_Vop"]) / P["tube_R"]


def vfb(v, fb_open=False):
    if fb_open:
        return 0.0
    return v * P["R_fb_bot"] / (P["R_fb_top"] + P["R_fb_bot"])


class Sim:
    def __init__(self, name, n_tubes=6, vin_nom=12.0, fb_open=False):
        self.name = name
        self.n_tubes = n_tubes
        self.vin_nom = vin_nom
        self.fb_open = fb_open
        self.vin = 0.0
        self.vout = 0.0
        self.iL = 0.0
        self.vcomp = 0.0        # 日志用：等效误差放大器输出
        self.ipk = 0.0          # 峰值电流给定
        self.integ = 0.0        # PI 积分项 (A)
        self.ref = 0.0          # 软启动参考 (V)
        self.latch = False
        self.hv_en = False
        self.t = 0.0
        self.log = []
        self.next_log = 0.0
        self.peak_iL = 0.0
        self.cum_in_q = 0.0      # ∫Vin*iL dt
        self.cum_out_e = 0.0     # ∫vout*(load) dt
        self.ovp_trip_t = None

    # ---- 逐步积分 ----
    def step(self, dt):
        p = P
        vin = self.vin
        v = self.vout
        il = self.iL
        # 输入功率积分
        p_in = vin * max(il, 0.0)
        self.cum_in_q += p_in * dt
        # 负载/泄放/分压电流
        i_load = rload_current(v, self.n_tubes) + v / getattr(self, "r_short", 1e12)
        i_bleed = v / p["Rbleed"]
        i_div = 0.0 if self.fb_open else v / (p["R_fb_top"] + p["R_fb_bot"])
        i_out = i_load + i_bleed + i_div
        self.cum_out_e += v * i_out * dt
        return i_out

    def run_switch_cycle(self, dt):
        """一个开关周期：峰值电流模式，ON 段（受 COMP/Ilim 限制）+ OFF 段。"""
        p = P
        ts = TS
        t = 0.0
        i_out = 0.0
        # ---- OFF / 开始新周期，判断是否允许开通 ----
        ipk_ref = self.ipk if (self.hv_en and not self.latch) else 0.0
        if ipk_ref < 0.02:
            ipk_ref = 0.0
        # ON 段
        ton = 0.0
        on = ipk_ref > 0.02
        while t < ts - 1e-15:
            if on:
                # di/dt = (Vin - iL*DCR - iL*Rds)/L
                didt = (self.vin - self.iL * (p["L_dcr"] + p["Rds"])) / p["L"]
                self.iL += didt * dt
                self.peak_iL = max(self.peak_iL, self.iL)
                # 输出侧只由电容放电
                i_out = self.step(dt)
                self.vout -= i_out * dt / p["Cout"]          # 仅负载/泄放放电
                if self.iL >= ipk_ref:
                    on = False
                ton += dt
                if ton >= ts * 0.95:
                    on = False
            else:
                # 二极管导通：di/dt = (Vin - Vout - Vf - iL*DCR)/L
                if self.iL > 0.0:
                    didt = (self.vin - self.vout - p["Vf"] - self.iL * p["L_dcr"]) / p["L"]
                    self.iL += didt * dt
                    if self.iL < 0.0:
                        self.iL = 0.0
                    i_out = self.step(dt)
                    # 输出电容：dv/dt = (iL_diode - i_out)/C
                    self.vout += (self.iL - i_out) * dt / p["Cout"]
                else:
                    i_out = self.step(dt)
                    self.vout -= i_out * dt / p["Cout"]
            t += dt
        # ---- 软启动参考 + 峰值电流环 PI（UC3843 环路的行为等效） ----
        # 参考以 2.5 V/50 ms 上升（对应 COMP 上 22 uF + 1 mA 上拉）
        self.ref = min(p["Vref"], self.ref + p["Vref"] / 0.150 * TS)
        err = self.ref - vfb(self.vout, self.fb_open)
        self.integ += err * TS / 0.010            # Ti = 10 ms
        ipk = self.integ * 1.2 + 0.35 * err       # 电流环给定 (A)
        if ipk > p["Ilim"] or ipk < 0.0:
            # 反算抗积分饱和（back-calculation）
            self.integ = (p["Ilim"] if ipk > p["Ilim"] else 0.0) - 0.35 * err
            ipk = self.integ * 1.2 + 0.35 * err
        self.integ = max(-0.5, min(p["Ilim"], self.integ))
        self.ipk = max(0.0, min(p["Ilim"], ipk))
        self.vcomp = self.ipk                # 日志列沿用 comp 名称
        # ---- OVP（独立硬件路径，触发即锁存） ----
        if (not self.latch) and self.vout >= p["ovp_trip"]:
            self.latch = True
            self.ovp_trip_t = self.t
        if self.latch:
            self.ipk = 0.0
            self.integ = 0.0
            self.ref = 0.0

    def run(self, t_end, events=None):
        events = sorted(events or [])
        ei = 0
        t = 0.0
        while t < t_end - 1e-15:
            # 事件
            while ei < len(events) and events[ei][0] <= t:
                _, fn = events[ei]
                fn(self)
                ei += 1
            self.run_switch_cycle(DT)
            self.t = t
            if t >= self.next_log:
                self.log.append(dict(
                    t_ms=self.t * 1e3, vout=self.vout, iL_mA=self.iL * 1e3,
                    comp=self.vcomp, latch=1.0 if self.latch else 0.0,
                    hv_en=1.0 if self.hv_en else 0.0,
                    cum_in=self.cum_in_q, cum_out=self.cum_out_e))
                self.next_log += P["tps"]
            t += TS

    def metrics(self):
        lg = self.log
        if not lg:
            return {}
        t = [x["t_ms"] for x in lg]
        v = [x["vout"] for x in lg]
        steady = [x for x in lg if x["t_ms"] > t[-1] * 0.70 and x["vout"] > 5]
        vs = float(np.mean([x["vout"] for x in steady])) if steady else 0.0
        ripple = (max(x["vout"] for x in steady)
                  - min(x["vout"] for x in steady)) if steady else 0.0
        eff_energy = (self.cum_out_e / self.cum_in_q) if self.cum_in_q > 0 else 0.0
        # 稳态效率：用累计能量在稳态窗口内取差值
        eff_ss = 0.0
        if len(steady) >= 2:
            din = steady[-1]["cum_in"] - steady[0]["cum_in"]
            dout = steady[-1]["cum_out"] - steady[0]["cum_out"]
            if din > 0:
                eff_ss = dout / din
        vmax = max(v)
        over = 100.0 * (vmax - P["Vref"] * (P["R_fb_top"] + P["R_fb_bot"])
                        / P["R_fb_bot"]) / (P["Vref"] * (P["R_fb_top"] + P["R_fb_bot"])
                                             / P["R_fb_bot"])
        return dict(name=self.name, vout_mean=vs, ripple_pp=ripple,
                    vout_max=vmax, overshoot_pct=over,
                    peak_iL_A=self.peak_iL, eff_energy=eff_energy,
                    eff_steady=eff_ss, ovp_trip_t_ms=self.ovp_trip_t,
                    latch=self.latch)


def scenario(name, n_tubes, t_end, events=None, vin_nom=12.0, fb_open=False,
             vin_profile=None):
    s = Sim(name, n_tubes=n_tubes, vin_nom=vin_nom, fb_open=fb_open)
    s.vin = 0.0
    s.log = []

    # HV_EN 在 5 ms 时由门控给出；之后由 vin_profile 控制输入电压
    ev = list(events or [])

    def hv_on(sim):
        sim.hv_en = True
        sim.vin = vin_nom if vin_profile is None else vin_profile(sim.t)

    ev.append((5e-3, hv_on))

    # 用步进驱动 + 周期性 vin 更新
    if vin_profile is not None:
        # 包装：每个周期重设 vin
        orig = s.run_switch_cycle

        def wrapped(dt):
            s.vin = vin_profile(s.t) if s.hv_en else 0.0
            orig(dt)
        s.run_switch_cycle = wrapped
    s.run(t_end, ev)
    return s


def save_plot(sims, fname, title, ylab="输出电压 (V)"):
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=130)
    for s in sims:
        t = [x["t_ms"] for x in s.log]
        v = [x["vout"] for x in s.log]
        ax.plot(t, v, lw=1.2, label=s.name)
    ax.set_xlabel("时间 (ms)")
    ax.set_ylabel(ylab)
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = os.path.join(OUT, fname)
    fig.savefig(p)
    plt.close(fig)
    return p


def discharge_analytic(sim, t0_s, t_end_s):
    """断电后：>150 V 无负载；150..100 V 六管导通；<100 V 熄灭后纯 RC。
    以 0.5 ms 步长积分，追加到日志（仅用于泄放时间结论）。"""
    v = sim.log[-1]["vout"]
    t = t0_s
    dt = 0.5e-3
    rows = []
    while t < t_end_s and v > 1.0:
        i_tube = 6 * max(0.0, (v - 125.0)) / 20e3 if v > 100.0 else 0.0
        i = v / P["Rbleed"] + i_tube
        v -= i * dt / P["Cout"]
        t += dt
        if (t * 1e3) % 5 < dt * 1e3:
            rows.append(dict(t_ms=t * 1e3, vout=v, iL_mA=0.0, comp=0.0,
                             latch=1.0 if sim.latch else 0.0, hv_en=0.0))
    sim.log.extend(rows)
    t50 = None
    for r in sim.log:
        if r["t_ms"] > t0_s * 1e3 + 1 and r["vout"] <= 50.0:
            t50 = r["t_ms"] - t0_s * 1e3
            break
    return t50


def main():
    results = []

    # 1) 上电启动：软启动 + 起辉 150 V 时刻负载投入 + 稳态
    s1 = scenario("S1 启动/软启动/起辉(6管)", 6, 0.45)
    results.append(s1.metrics())
    # 2) 空载（仅泄放/分压，等效无管）
    s2 = scenario("S2 空载", 0, 0.90)
    results.append(s2.metrics())
    # 3) 单管
    s3 = scenario("S3 单管负载", 1, 0.60)
    results.append(s3.metrics())
    # 4) 六管
    s4 = scenario("S4 六管负载", 6, 0.45)
    results.append(s4.metrics())
    save_plot([s1, s2, s3, s4], "01_startup_and_loads.png",
              "启动 / 空载 / 单管 / 六管 输出电压（行为模型）")

    # 5) 负载突变 6 管 -> 1 管 -> 6 管
    def load_to_1(sim):
        sim.n_tubes = 1

    def load_to_6(sim):
        sim.n_tubes = 6
    s5 = scenario("S5 负载突变 6管->1管->6管", 6, 0.60,
                  events=[(0.20, load_to_1), (0.35, load_to_6)])
    results.append(s5.metrics())

    # 6) 输入电压变化 12 -> 11.4 -> 12.6 V
    def vin_step(sim_t):
        return 11.4 if 0.15 <= sim_t < 0.30 else (12.6 if sim_t >= 0.30 else 12.0)
    s6 = scenario("S6 输入电压变化 12/11.4/12.6", 6, 0.50, vin_profile=vin_step)
    results.append(s6.metrics())
    save_plot([s5, s6], "02_load_and_line_step.png", "负载突变 / 输入电压变化")

    # 7) 反馈分压开路 -> 输出失控 -> OVP 190 V 锁存
    s7 = scenario("S7 反馈开路->OVP锁存", 6, 0.60, fb_open=True)
    results.append(s7.metrics())

    # 8) OVP 后 MCU 受控复位（反馈仍开路 -> 再次触发）
    def reset_latch(sim):
        if sim.latch:
            sim.latch = False
            sim.ovp_trip_t = None
    s8 = scenario("S8 OVP锁存->受控复位", 6, 1.00, fb_open=True,
                  events=[(0.45, reset_latch)])
    results.append(s8.metrics())
    save_plot([s7, s8], "03_ovp_latch_and_reset.png",
              "反馈开路 -> OVP 190 V 锁存 -> 受控复位（反馈仍开路，再次触发）")

    # 9) 断电放电（开关仿真 + 解析泄放段）
    s9 = scenario("S9 断电放电", 6, 0.25, events=[(0.20, lambda s: setattr(s, "vin", 0.0))])
    m9 = s9.metrics()
    t50 = discharge_analytic(s9, 0.25, 8.0)
    m9["discharge_to_50V_ms"] = t50
    results.append(m9)
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=130)
    ax.plot([x["t_ms"] / 1e3 for x in s9.log], [x["vout"] for x in s9.log], lw=1.3)
    ax.axhline(50, ls="--", color="r", lw=1)
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("HV_BUS (V)")
    ax.set_title("断电后泄放（200 kΩ / 20 µF；六管在 >100 V 时仍导通）")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "04_discharge.png"))
    plt.close(fig)

    # 10) 输出短路（10 Ω）
    def do_short(sim):
        sim.r_short = 10.0
        sim.n_tubes = 0
    s10 = scenario("S10 输出短路 10Ω", 6, 0.40, events=[(0.15, do_short)])
    results.append(s10.metrics())
    save_plot([s10], "05_output_short.png", "输出短路 10 Ω：峰值电流限制行为")

    # 导出 CSV
    for s in [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10]:
        fn = os.path.join(OUT, "csv_" + s.name.split()[0] + ".csv")
        with open(fn, "w", encoding="utf-8") as f:
            f.write("t_ms,vout_V,iL_mA,ipk_ref,latch,hv_en\n")
            for row in s.log:
                f.write("%.4f,%.4f,%.4f,%.4f,%.0f,%.0f\n" % (
                    row["t_ms"], row["vout"], row["iL_mA"], row["comp"],
                    row["latch"], row["hv_en"]))
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(params=P, results=results,
                       model="switching behavioural model; not device-level SPICE; "
                             "UC3843 行为等效（PI 电流环 + 软启动参考斜坡）；"
                             "未建模开关损耗/振铃/磁芯损耗/温升"),
                  f, ensure_ascii=False, indent=2)
    for r in results:
        print({k: (round(v, 4) if isinstance(v, float) else v)
               for k, v in r.items()})


if __name__ == "__main__":
    main()
