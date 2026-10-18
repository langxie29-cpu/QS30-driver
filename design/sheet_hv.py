# -*- coding: utf-8 -*-
"""QS30-6 REV.A high-voltage sheets 04 (升压+OVP), 05 (管座/阳极限流),
06 (测试点与扩展) and the 60-channel drive mapping."""
from model import add, conn, nc, net_class

# ---------------------------------------------------------------------------
# channel mapping:  CH = (tube-1)*10 + digit ,  CH 0..31 -> U21, 32..63 -> U22
# ---------------------------------------------------------------------------
HVOUT_PIN = {}          # HVOUT number (1..32) -> PQFP pin number
for _n in range(1, 23):
    HVOUT_PIN[_n] = 23 - _n          # HVOUT1 -> pin22 ... HVOUT22 -> pin1
for _n in range(23, 33):
    HVOUT_PIN[_n] = 67 - _n          # HVOUT23 -> pin44 ... HVOUT32 -> pin35

TUBE_DIGIT_PIN = {0: 3, 1: 13, 2: 12, 3: 11, 4: 10, 5: 9,
                  6: 7, 7: 6, 8: 5, 9: 4}     # QS30-1 原厂电极接线图


def channel(tube, digit):
    return (tube - 1) * 10 + digit


def device_of(ch):
    return "U21" if ch < 32 else "U22"


def hvout_of(ch):
    return (ch % 32) + 1


def cathode_net(tube, digit):
    return f"K_T{tube}_{digit}"


def anode_net(tube):
    return f"A_T{tube}"


def connect_tubes():
    """sheet 05: six 13-pin sockets + six 20 kOhm anode limit branches."""
    r = 90
    for t in range(1, 7):
        ref = f"J3{t}"
        add(ref, "J13-1A-SOCKET", "13 脚可拆管座 (QS30-1)", "13P socket",
            "HOLD", "S6", "管座焊脚坐标/孔径/视图未实测，封装为 PROVISIONAL", 
            "05_TUBE", pin_key="SOCKET-13",
            note="H03：J13-1A 尺寸/触点/1 脚视图/1:1 比对")
        for pin, name in (("1", "NC"), ("2", anode_net(t)),
                          ("3", cathode_net(t, 0)), ("4", cathode_net(t, 9)),
                          ("5", cathode_net(t, 8)), ("6", cathode_net(t, 7)),
                          ("7", cathode_net(t, 6)), ("8", "NC"),
                          ("9", cathode_net(t, 5)), ("10", cathode_net(t, 4)),
                          ("11", cathode_net(t, 3)), ("12", cathode_net(t, 2)),
                          ("13", cathode_net(t, 1))):
            if name == "NC":
                nc(ref, pin)
            else:
                conn(ref, pin, name)
        # two 10 kOhm / 2 W in series = 20 kOhm  (fault power split)
        add(f"R{r}", "10k 2W", "10 kΩ 2 W 厚膜", "2512", "PROVISIONAL", "S6",
            f"J_T{t} 阳极限流电阻 1/2（20 kΩ/2 W 支路）", "05_TUBE",
            pin_key="R", note="H06：故障耗散 1.45 W 需实测/降额")
        add(f"R{r+1}", "10k 2W", "10 kΩ 2 W 厚膜", "2512", "PROVISIONAL", "S6",
            f"J_T{t} 阳极限流电阻 2/2", "05_TUBE", pin_key="R", note="H06")
        conn(f"R{r}", 1, "HV_BUS"); conn(f"R{r}", 2, f"A_MID{t}")
        conn(f"R{r+1}", 1, f"A_MID{t}"); conn(f"R{r+1}", 2, anode_net(t))
        r += 2


def connect_drivers():
    """connect the 60 used HV5622 outputs to the six sockets (sheet 03)."""
    for t in range(1, 7):
        for d in range(10):
            ch = channel(t, d)
            dev = device_of(ch)
            hv = hvout_of(ch)
            pin = HVOUT_PIN[hv]
            conn(dev, pin, cathode_net(t, d))
    # 4 spare channels 60..63 left open (HVOUT29..32 of U22)
    for hv in (29, 30, 31, 32):
        nc("U22", HVOUT_PIN[hv])


def build():
    connect_tubes()
    connect_drivers()

    # =====================================================================
    # SHEET 04  12 V -> ~172 V 升压 + 独立硬件过压保护/锁存
    # =====================================================================
    S = "04_HV"

    # ---- 12 V 输入开关：HV_EN -> Q27 -> Q26，默认关断 -----------------
    add("Q26", "DMP3098L", "P-MOSFET 30 V/3.8 A", "SOT-23", "PROVISIONAL", "S16",
        "升压输入高边开关（HV_EN 硬件门控，默认关断）", S, pin_key="P-FET",
        note="H06")
    conn("Q26", 1, "Q26_G"); conn("Q26", 2, "EXT12"); conn("Q26", 3, "HV_IN")
    add("R87", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S16",
        "Q26 栅极上拉 → 默认关断", S, pin_key="R")
    conn("R87", 1, "EXT12"); conn("R87", 2, "Q26_G")
    add("R88", "100Ω", "100 Ω 1%", "0603", "VERIFIED", "S16",
        "Q27 栅极串联电阻", S, pin_key="R")
    conn("R88", 1, "HV_EN"); conn("R88", 2, "HV_EN_G")
    add("Q27", "2N7002", "N-MOSFET 60 V", "SOT-23", "VERIFIED", "S16",
        "Q26 栅极驱动", S, pin_key="N-FET")
    conn("Q27", 1, "HV_EN_G"); conn("Q27", 2, "GND"); conn("Q27", 3, "Q26_G")
    add("R89", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S16",
        "Q27 栅极下拉 → HV_EN 悬空时关断", S, pin_key="R")
    conn("R89", 1, "HV_EN_G"); conn("R89", 2, "GND")
    add("C43", "10uF/25V", "10 µF 25 V X5R", "1206", "VERIFIED", "S16",
        "HV_IN 输入储能", S, pin_key="C")
    conn("C43", 1, "HV_IN"); conn("C43", 2, "GND")

    # ---- UC3843 升压控制器 --------------------------------------------
    add("U20", "UC3843AN", "UC3843 电流型 PWM 控制器", "DIP-8/SOIC-8",
        "VERIFIED", "S17", "升压控制器，fsw≈78 kHz，峰值电流限制≈1 A", S,
        note="H06：开关频率/占空比/环路待实测")
    conn("U20", 1, "COMP_N"); conn("U20", 2, "FB_HV"); conn("U20", 3, "CS_FILT")
    conn("U20", 4, "RCT_N"); conn("U20", 5, "GND"); conn("U20", 6, "GATE_N")
    conn("U20", 7, "VCC_HV"); conn("U20", 8, "VREF5_HV")
    add("R60", "10Ω", "10 Ω 1%", "0805", "VERIFIED", "S17",
        "VCC 滤波电阻", S, pin_key="R")
    conn("R60", 1, "HV_IN"); conn("R60", 2, "VCC_HV")
    add("C44", "10uF/25V", "10 µF 25 V X5R", "1206", "VERIFIED", "S17",
        "VCC_HV 储能", S, pin_key="C")
    conn("C44", 1, "VCC_HV"); conn("C44", 2, "GND")
    add("C45", "100nF/25V", "0.1 µF 25 V", "0603", "VERIFIED", "S17",
        "VCC_HV 高频旁路", S, pin_key="C")
    conn("C45", 1, "VCC_HV"); conn("C45", 2, "GND")
    add("C46", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S17",
        "VREF 旁路", S, pin_key="C")
    conn("C46", 1, "VREF5_HV"); conn("C46", 2, "GND")
    add("R61", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S17",
        "RT（f≈1.72/(RT·CT)=78 kHz）", S, pin_key="R")
    conn("R61", 1, "VREF5_HV"); conn("R61", 2, "RCT_N")
    add("C47", "2.2nF/50V", "2.2 nF 50 V", "0603", "VERIFIED", "S17",
        "CT", S, pin_key="C")
    conn("C47", 1, "RCT_N"); conn("C47", 2, "GND")
    add("R62", "1Ω 1W", "1 Ω 1 W 合金采样", "2512", "PROVISIONAL", "S17",
        "峰值电流采样（1 V 门限 → 1 A）", S, pin_key="R", note="H06")
    conn("R62", 1, "CS_N"); conn("R62", 2, "GND")
    add("R63", "100Ω", "100 Ω 1%", "0603", "VERIFIED", "S17",
        "CS 滤波电阻", S, pin_key="R")
    conn("R63", 1, "CS_N"); conn("R63", 2, "CS_FILT")
    add("C48", "470pF/50V", "470 pF 50 V", "0603", "VERIFIED", "S17",
        "CS 前沿消隐滤波（τ≈47 ns）", S, pin_key="C")
    conn("C48", 1, "CS_FILT"); conn("C48", 2, "GND")
    add("R64", "22Ω", "22 Ω 1%", "0603", "VERIFIED", "S17",
        "MOSFET 栅极串联电阻", S, pin_key="R")
    conn("R64", 1, "GATE_N"); conn("R64", 2, "Q20_G")
    add("R65", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S17",
        "MOSFET 栅极下拉", S, pin_key="R")
    conn("R65", 1, "Q20_G"); conn("R65", 2, "GND")
    add("Q20", "IRF740", "N-MOSFET 400 V/10 A", "TO-220", "VERIFIED", "S18",
        "升压主开关（400 V 器件，Vds 峰值≈172 V+振铃）", S,
        pin_key="N-FET-TO220", note="H06：需实测 Vds 振铃/温升/雪崩")
    conn("Q20", 1, "Q20_G"); conn("Q20", 2, "SW_HV"); conn("Q20", 3, "CS_N")
    add("L20", "220uH/5A", "220 µH ≥5 A 功率电感（Isat≥5A）", "12x12 屏蔽",
        "PROVISIONAL", "S17", "升压电感，Isat≥2 A，DCR 尽量低", S,
        pin_key="L", note="H06：ΔI≈0.65 A @78 kHz")
    conn("L20", 1, "HV_IN"); conn("L20", 2, "SW_HV")
    add("D20", "UF4007", "1000 V 1 A 快恢复", "SMA/DO-41", "VERIFIED", "S17",
        "升压整流二极管（反压 172 V，1000 V 额定）", S, pin_key="D")
    conn("D20", 1, "HV_BUS"); conn("D20", 2, "SW_HV")
    add("D21", "UF4007", "1000 V 1 A 快恢复", "SMA/DO-41", "VERIFIED", "S17",
        "RCD 钳位二极管", S, pin_key="D")
    conn("D21", 1, "CLAMP_N"); conn("D21", 2, "SW_HV")
    add("C49", "10nF/630V", "10 nF 630 V X7R", "1206", "VERIFIED", "S17",
        "RCD 钳位电容", S, pin_key="C")
    conn("C49", 1, "CLAMP_N"); conn("C49", 2, "HV_BUS")
    add("R66", "100k 2W", "100 kΩ 2 W", "2512", "PROVISIONAL", "S17",
        "RCD 钳位电阻", S, pin_key="R", note="H06")
    conn("R66", 1, "CLAMP_N"); conn("R66", 2, "HV_BUS")
    add("C50", "10uF/250V", "10 µF 250 V 电解", "10x12.5 SMD",
        "PROVISIONAL", "S17", "HV_BUS 储能", S, pin_key="C", note="H06")
    conn("C50", 1, "HV_BUS"); conn("C50", 2, "GND")
    add("C51", "10uF/250V", "10 µF 250 V 电解", "10x12.5 SMD",
        "PROVISIONAL", "S17", "HV_BUS 储能", S, pin_key="C", note="H06")
    conn("C51", 1, "HV_BUS"); conn("C51", 2, "GND")
    add("C52", "100nF/630V", "0.1 µF 630 V", "1206", "VERIFIED", "S17",
        "HV_BUS 高频旁路", S, pin_key="C")
    conn("C52", 1, "HV_BUS"); conn("C52", 2, "GND")
    # 泄放：2x220k = 440k，τ≈8.8 s（20 µF）
    add("R67", "100k", "100 kΩ 1%", "1206", "VERIFIED", "S17",
        "HV 泄放电阻 1/2", S, pin_key="R")
    conn("R67", 1, "HV_BUS"); conn("R67", 2, "BLEED_MID")
    add("R68", "100k", "100 kΩ 1%", "1206", "VERIFIED", "S17",
        "HV 泄放电阻 2/2（合计 200 kΩ，τ≈4.0 s）", S, pin_key="R")
    conn("R68", 1, "BLEED_MID"); conn("R68", 2, "GND")
    add("C53", "100nF/50V", "0.1 µF 50 V", "0603", "VERIFIED", "S17",
        "HV 泄放交流旁路", S, pin_key="C")
    conn("C53", 1, "BLEED_MID"); conn("C53", 2, "GND")
    # 反馈分压：2x750k / 22.1k  -> 2.5 V*(1+1500/22.1)=172.2 V
    add("R69", "750k", "750 kΩ 1%", "1206", "VERIFIED", "S17",
        "HV 反馈上臂 1/2", S, pin_key="R")
    conn("R69", 1, "HV_BUS"); conn("R69", 2, "FB_MID")
    add("R70", "750k", "750 kΩ 1%", "1206", "VERIFIED", "S17",
        "HV 反馈上臂 2/2", S, pin_key="R")
    conn("R70", 1, "FB_MID"); conn("R70", 2, "FB_HV")
    add("R71", "22.1k", "22.1 kΩ 1%", "0603", "VERIFIED", "S17",
        "HV 反馈下臂 → Vout=172.2 V", S, pin_key="R")
    conn("R71", 1, "FB_HV"); conn("R71", 2, "GND")
    add("C54", "100nF/50V", "0.1 µF 50 V", "0603", "VERIFIED", "S17",
        "反馈滤波", S, pin_key="C")
    conn("C54", 1, "FB_HV"); conn("C54", 2, "GND")
    add("C55", "22uF/16V", "22 µF 16 V X5R", "0805", "VERIFIED", "S17",
        "COMP 软启动电容（≈50 ms）", S, pin_key="C")
    conn("C55", 1, "COMP_N"); conn("C55", 2, "GND")
    add("R72", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S17",
        "环路补偿零极点电阻", S, pin_key="R")
    conn("R72", 1, "COMP_N"); conn("R72", 2, "COMP_R")
    add("C56", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S17",
        "环路补偿电容", S, pin_key="C")
    conn("C56", 1, "COMP_R"); conn("C56", 2, "GND")

    # ---- 独立硬件过压保护（比较器 + 基准 + 分立 SCR 锁存）-------------
    add("U23", "LM393DR", "OVP 比较器", "SOIC-8", "VERIFIED", "S19",
        "独立于 MCU 的过压检测（门限 198.8 V）", S)
    conn("U23", 8, "EXT12"); conn("U23", 4, "GND")
    conn("U23", 3, "OVP_SNS"); conn("U23", 2, "VREF_OVP"); conn("U23", 1, "OVP_SET")
    nc("U23", 5, 6, 7)
    add("U24", "TL431", "2.5 V 基准", "SOT-23", "VERIFIED", "S17",
        "OVP 基准（2.5 V），DBZ 1=C/2=REF/3=A", S)
    # DBZ: 1=CATHODE, 2=REF, 3=ANODE；REF 与 CATHODE 短接 = 2.5 V
    conn("U24", 1, "VREF_OVP"); conn("U24", 2, "VREF_OVP"); conn("U24", 3, "GND")
    add("R74", "4.7k", "4.7 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP 基准偏置（(12-2.5)/4.7k≈2 mA）", S, pin_key="R")
    conn("R74", 1, "EXT12"); conn("R74", 2, "VREF_OVP")
    add("C57", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S19",
        "OVP 基准旁路", S, pin_key="C")
    conn("C57", 1, "VREF_OVP"); conn("C57", 2, "GND")
    add("R75", "750k", "750 kΩ 1%", "1206", "VERIFIED", "S19",
        "OVP 取样上臂 1/2", S, pin_key="R")
    conn("R75", 1, "HV_BUS"); conn("R75", 2, "OVP_MID")
    add("R76", "750k", "750 kΩ 1%", "1206", "VERIFIED", "S19",
        "OVP 取样上臂 2/2", S, pin_key="R")
    conn("R76", 1, "OVP_MID"); conn("R76", 2, "OVP_SNS")
    add("R77", "19.1k", "19.1 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP 取样下臂 → 触发电压 2.5 V*(1519.1/19.1)=198.8 V", S, pin_key="R")
    conn("R77", 1, "OVP_SNS"); conn("R77", 2, "GND")
    add("C58", "100nF/50V", "0.1 µF 50 V", "0603", "VERIFIED", "S19",
        "OVP 取样滤波（响应 τ≈2 ms）", S, pin_key="C")
    conn("C58", 1, "OVP_SNS"); conn("C58", 2, "GND")
    add("R78", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP_SET 上拉", S, pin_key="R")
    conn("R78", 1, "OVP_SET"); conn("R78", 2, "EXT12")
    add("C59", "100nF/25V", "0.1 µF 25 V", "0603", "VERIFIED", "S19",
        "OVP 比较器旁路", S, pin_key="C")
    conn("C59", 1, "EXT12"); conn("C59", 2, "GND")

    # 分立 SCR 锁存：Q21(PNP) + Q22(NPN)
    add("Q21", "MMBT3906", "PNP 40 V", "SOT-23", "VERIFIED", "S19",
        "锁存 SCR 上半（PNP）", S, pin_key="PNP")
    conn("Q21", 1, "LATCH_B"); conn("Q21", 2, "EXT12"); conn("Q21", 3, "OVP_LATCH")
    add("Q22", "MMBT3904", "NPN 40 V", "SOT-23", "VERIFIED", "S19",
        "锁存 SCR 下半（NPN）", S, pin_key="NPN")
    conn("Q22", 1, "OVP_LATCH"); conn("Q22", 2, "GND"); conn("Q22", 3, "LATCH_B")
    add("R79", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S19",
        "锁存初始关断偏置", S, pin_key="R")
    conn("R79", 1, "LATCH_B"); conn("R79", 2, "EXT12")
    add("R80", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP_SET → 锁存置位注入", S, pin_key="R")
    conn("R80", 1, "OVP_SET"); conn("R80", 2, "LATCH_B")
    add("R81", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP_LATCH 关断偏置", S, pin_key="R")
    conn("R81", 1, "OVP_LATCH"); conn("R81", 2, "GND")
    add("C60", "100nF/25V", "0.1 µF 25 V", "0603", "VERIFIED", "S19",
        "锁存抗干扰", S, pin_key="C")
    conn("C60", 1, "OVP_LATCH"); conn("C60", 2, "GND")

    # 锁存动作：拉低 COMP（关断升压）+ 输出故障
    add("Q23", "MMBT3904", "NPN 40 V", "SOT-23", "VERIFIED", "S19",
        "锁存 → 拉低 COMP，强制占空比 0", S, pin_key="NPN")
    conn("Q23", 1, "Q23_B"); conn("Q23", 2, "GND"); conn("Q23", 3, "COMP_N")
    add("R82", "47k", "47 kΩ 1%", "0603", "VERIFIED", "S19",
        "Q23 基极电阻", S, pin_key="R")
    conn("R82", 1, "OVP_LATCH"); conn("R82", 2, "Q23_B")
    add("Q24", "MMBT3904", "NPN 40 V", "SOT-23", "VERIFIED", "S19",
        "锁存 → 拉低 HV_FAULT_N（低有效故障）", S, pin_key="NPN")
    conn("Q24", 1, "Q24_B"); conn("Q24", 2, "GND"); conn("Q24", 3, "HV_FAULT_OD")
    add("R83", "47k", "47 kΩ 1%", "0603", "VERIFIED", "S19",
        "Q24 基极电阻", S, pin_key="R")
    conn("R83", 1, "OVP_LATCH"); conn("R83", 2, "Q24_B")
    add("R84", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S19",
        "HV_FAULT_OD 上拉至 DRV_VDD（失电时被下拉为故障态）", S, pin_key="R")
    conn("R84", 1, "HV_FAULT_OD"); conn("R84", 2, "DRV_VDD")

    # 受控恢复：MCU 脉冲 OVP_RST 拉低 OVP_LATCH
    add("Q25", "2N7002", "N-MOSFET 60 V", "SOT-23", "VERIFIED", "S19",
        "锁存复位开关（MCU GPIO18 脉冲高有效）", S, pin_key="N-FET")
    conn("Q25", 1, "OVP_RST_G"); conn("Q25", 2, "GND"); conn("Q25", 3, "OVP_LATCH")
    add("R85", "1k", "1 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP_RST 栅极串联电阻", S, pin_key="R")
    conn("R85", 1, "OVP_RST"); conn("R85", 2, "OVP_RST_G")
    add("R86", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S19",
        "OVP_RST 栅极下拉 → 默认不复位", S, pin_key="R")
    conn("R86", 1, "OVP_RST_G"); conn("R86", 2, "GND")
    add("C61", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S19",
        "OVP_RST 抗干扰", S, pin_key="C")
    conn("C61", 1, "OVP_RST_G"); conn("C61", 2, "GND")

    # =====================================================================
    # SHEET 06  测试点与扩展接口
    # =====================================================================
    S = "06_TP"
    tps = [
        ("EXT12", "12 V 保护后输入"), ("EXT5", "12V->5V 输出"),
        ("5V_SYS", "5 V 电源选择输出"), ("3V3", "3.3 V 主电源"),
        ("DRV_VDD", "HV5622 逻辑电源 12 V"), ("HV_BUS", "170 V 高压母线"),
        ("GND", "地"), ("EN_MCU", "模组 EN"), ("BOOT_N", "GPIO0/BOOT"),
        ("UART0_TX", "UART0 TX"), ("UART0_RX", "UART0 RX"),
        ("HV_SENSE_ADC", "HV 分压 ADC 节点"), ("HVF_NODE", "故障检测节点"),
        ("EXT12_PG", "12 V 电源良好"), ("P3V3_PG", "3.3 V 电源良好"),
        ("DRV_PG", "DRV_VDD 电源良好"), ("HV_EN", "高压使能（门控后）"),
        ("DRV_HV_EN_REQ", "12 V 域高压请求"), ("OVP_LATCH", "过压锁存状态"),
        ("DRV2_DOUT", "HV5622 级联数据输出"),
    ]
    for i, (net, desc) in enumerate(tps, 1):
        add(f"TP{i}", f"TP-{net}", f"测试点 {net}", "1.0mm pad",
            "VERIFIED", "S20", desc, S, pin_key="TP")
        conn(f"TP{i}", 1, net)
    add("J4", "HDR-1x6-2.54", "扩展接口 1x6", "2.54mm", "VERIFIED", "S3",
        "3V3/GND/IO13/IO21/I2C（未承诺接口）", S, pin_key="HDR-6")
    conn("J4", 1, "3V3"); conn("J4", 2, "GND"); conn("J4", 3, "EXP_IO13")
    conn("J4", 4, "EXP_IO21"); conn("J4", 5, "I2C_SDA"); conn("J4", 6, "I2C_SCL")
    return


if __name__ == "__main__":
    build()
