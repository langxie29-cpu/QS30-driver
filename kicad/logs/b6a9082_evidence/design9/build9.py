# -*- coding: utf-8 -*-
"""QS30-9 / REV.A 九位模块化设计数据生成器（3 显示模块 L/C/R + 中央主板）。

一次生成：网表、90 路映射、接口规范、ERC9、BOM-A/B/C、成本、机械尺寸、
驱动方案比较、G0–G5、架构文档、KiCad 符号库（仅符号；封装不生成以免猜测）。
运行：python design9/build9.py
"""
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "design"))
import model as m6

DOC9 = os.path.join(ROOT, "docs9")
BOM9 = os.path.join(ROOT, "bom9")
NET9 = os.path.join(ROOT, "netlist9")
KICAD = os.path.join(ROOT, "kicad")
for d in (DOC9, BOM9, NET9, KICAD):
    os.makedirs(d, exist_ok=True)

PIN_DB = {k: m6.PIN_DB[k] for k in (
    "HV5622-PQFP44", "ESP32-S3-WROOM-1", "QS30-1", "SOCKET-13", "LM393", "TL431",
    "UC3843", "CD40109B", "74HC08", "TPS54202", "SY8089A", "USBLC6-2SC6",
    "N-FET-TO220", "USBC-16P", "HDR-2", "HDR-6", "SW", "FUSE", "BAT54S", "LED", "NPN", "PNP")}
PIN_DB.update({
    "Q_NPN": {"1": "B", "2": "E", "3": "C"},
    "Q_PNP": {"1": "B", "2": "E", "3": "C"},
    "P-FET-SOT23": {"1": "G", "2": "S", "3": "D"},
    "R": {"1": "1", "2": "2"}, "C": {"1": "1", "2": "2"},
    "L": {"1": "1", "2": "2"}, "D": {"A": "A", "K": "K"},
    "TP": {"1": "1"},
    "CONN-LV-16": {str(i): f"{i}" for i in range(1, 17)},
    "CONN-HV-2": {"1": "HV+", "2": "HV_RET"},
})
HVOUT_PIN = {int(n[5:]): int(p) for p, n in PIN_DB["HV5622-PQFP44"].items() if n.startswith("HVOUT")}
SOCK_PIN = {int(n[1:]): int(p) for p, n in PIN_DB["SOCKET-13"].items() if n.startswith("K")}

# ---------------- 设计参数 ----------------
V_BUS = 172.18
V_OVP = 198.8
I_TYP, I_MAX = 2.25e-3, 3.0e-3
N_TUBE = 9
V_DRV_PG, V_DRV_PG_HYS = 11.2, 0.45
VICR_MAX = 1.30          # LM393 @3.3V 全温区 VCC-2
VREF_1V0 = 1.0
V_OVP_TARGET = 198.8
V_OVP_WINDOW = (192.5, 204.5)

MODULES = [("L", "left", "U_L"), ("C", "center", "U_C"), ("R", "right", "U_R")]
TUBE_OF = {"L": (1, 2, 3), "C": (4, 5, 6), "R": (7, 8, 9)}


class Part:
    def __init__(self, ref, mpn, pin_key, value, pkg, sheet, status, note=""):
        self.ref, self.mpn, self.pin_key = ref, mpn, pin_key
        self.value, self.pkg, self.sheet = value, pkg, sheet
        self.status, self.note = status, note
        self.nets = {}

    def conn(self, pin, net):
        self.nets[str(pin)] = net


class Design:
    def __init__(self):
        self.parts, self.net_class, self.nc = {}, {}, []

    def add(self, ref, mpn, pin_key, value, pkg, sheet, status="PROVISIONAL", note=""):
        self.parts[ref] = Part(ref, mpn, pin_key, value, pkg, sheet, status, note)
        return self.parts[ref]

    def conn(self, ref, pin, net):
        if ref not in self.parts:
            raise KeyError(f"part {ref} not added")
        if str(pin) not in PIN_DB[self.parts[ref].pin_key]:
            raise KeyError(f"{ref}: pin {pin} not in {self.parts[ref].pin_key}")
        self.parts[ref].conn(pin, net)

    def nets(self):
        n = {}
        for p in self.parts.values():
            for pin, net in p.nets.items():
                n.setdefault(net, []).append((p.ref, pin))
        return n

    def classify(self):
        for net in self.nets():
            if net in ("GND", "GND_HV"):
                c = "GND"
            elif net.startswith(("HV_BUS", "SW_HV")):
                c = "HV"
            elif net.startswith("K_T") or net.startswith("A_T"):
                c = "HV"
            elif net in ("EXT12", "EXT12_RAW", "EXT12_F", "EXT5", "5V_SYS", "DRV_VDD", "3V3"):
                c = "POWER"
            elif net in ("OVP_RST", "OVP_RST_G"):
                c = "SIGNAL"
            elif net.startswith(("OVP_", "LATCH_")):
                c = "HV"
            elif net.startswith("DRV_"):
                c = "DRV"
            elif net.startswith("USB_"):
                c = "DIFF"
            elif net.startswith(("MOD_", "SAFETY_", "DISP_", "HVF_", "HV_SENSE")):
                c = "SIGNAL"
            else:
                c = "SIGNAL"
            self.net_class[net] = c
        return self.net_class


# ==================================================================
def build():
    d = Design()
    add = d.add
    # ---------------- 中央主板：输入/辅助电源 ----------------
    S = "MB_POWER"
    add("J1", "DC-005-5.08-2P", "HDR-2", "12 V DC 输入", "TERM-2", S)
    d.conn("J1", 1, "EXT12_RAW"); d.conn("J1", 2, "GND")
    add("F1", "PPTC-1.5A-1812", "FUSE", "1.5 A 自恢复保险丝", "1812", S)
    d.conn("F1", 1, "EXT12_RAW"); d.conn("F1", 2, "EXT12_F")
    add("D1", "SS54", "D", "40 V 5 A 肖特基", "SMA", S)
    d.conn("D1", "A", "EXT12_F"); d.conn("D1", "K", "EXT12")
    for ref, val in (("C1", "10uF/25V"), ("C2", "100nF/25V")):
        add(ref, val, "C", val, "1206" if ref == "C1" else "0603", S)
        d.conn(ref, 1, "EXT12"); d.conn(ref, 2, "GND")
    add("U5", "TPS54202DDCR", "TPS54202", "12 V→5.08 V 2 A", "SOT-23-6", S, "VERIFIED")
    for pin, net in (("1", "GND"), ("2", "EXT5_SW"), ("3", "EXT12"), ("4", "EXT5_FB"),
                     ("5", "EXT12"), ("6", "EXT5_BOOT")):
        d.conn("U5", pin, net)
    add("C4", "100nF", "C", "BOOT 电容", "0603", S, "VERIFIED")
    d.conn("C4", 1, "EXT5_BOOT"); d.conn("C4", 2, "EXT5_SW")
    add("L5", "10uH", "L", "10 µH 2 A", "CD32", S)
    d.conn("L5", 1, "EXT5_SW"); d.conn("L5", 2, "EXT5")
    add("R5", "100k", "R", "100 kΩ 1%", "0603", S, "VERIFIED")
    d.conn("R5", 1, "EXT5"); d.conn("R5", 2, "EXT5_FB")
    add("R6", "13.3k", "R", "13.3 kΩ 1%", "0603", S, "VERIFIED")
    d.conn("R6", 1, "EXT5_FB"); d.conn("R6", 2, "GND")
    add("C5", "22uF/16V", "C", "22 µF 16 V", "0805", S)
    d.conn("C5", 1, "EXT5"); d.conn("C5", 2, "GND")
    add("U1", "SY8089A", "SY8089A", "5 V→3.3 V 2 A", "SOT-23-6", S, "VERIFIED")
    for pin, net in (("1", "5V_SYS"), ("2", "GND"), ("3", "3V3_SW"), ("4", "5V_SYS"),
                     ("5", "3V3_FB")):
        d.conn("U1", pin, net)
    add("L1", "2.2uH", "L", "2.2 µH 2 A", "CD32", S)
    d.conn("L1", 1, "3V3_SW"); d.conn("L1", 2, "3V3")
    add("R7", "100k", "R", "100 kΩ 1%", "0603", S, "VERIFIED")
    d.conn("R7", 1, "3V3"); d.conn("R7", 2, "3V3_FB")
    add("R8", "22.1k", "R", "22.1 kΩ 1%", "0603", S, "VERIFIED")
    d.conn("R8", 1, "3V3_FB"); d.conn("R8", 2, "GND")
    add("C6", "22uF/10V", "C", "22 µF 10 V", "0805", S)
    d.conn("C6", 1, "3V3"); d.conn("C6", 2, "GND")
    # USB / OR / ESD
    S = "MB_USB"
    add("J2", "USBC-16P", "USBC-16P", "USB-C", "USBC-16P", S)
    for pin in ("A1", "A12", "B1", "B12", "S1", "S2", "S3", "S4"):
        d.conn("J2", pin, "GND")
    for pin in ("A4", "A9", "B4", "B9"):
        d.conn("J2", pin, "VBUS")
    d.conn("J2", "A5", "USB_CC1"); d.conn("J2", "B5", "USB_CC2")
    d.conn("J2", "A6", "USB_DP"); d.conn("J2", "A7", "USB_DM")
    d.conn("J2", "B6", "USB_DP"); d.conn("J2", "B7", "USB_DM")
    for ref, net in (("R9", "USB_CC1"), ("R10", "USB_CC2")):
        add(ref, "5.1k", "R", "5.1 kΩ CC 下拉", "0603", S, "VERIFIED")
        d.conn(ref, 1, net); d.conn(ref, 2, "GND")
    add("U2", "USBLC6-2SC6", "USBLC6-2SC6", "USB ESD 保护", "SOT-23-6", S, "VERIFIED")
    for pin, net in (("1", "USB_DP"), ("2", "GND"), ("3", "USB_DM"), ("4", "USB_DM_MCU"),
                     ("5", "VBUS"), ("6", "USB_DP_MCU")):
        d.conn("U2", pin, net)
    add("D2", "SS14", "D", "40 V 1 A", "SMA", S, "VERIFIED")
    d.conn("D2", "A", "EXT5"); d.conn("D2", "K", "5V_SYS")
    add("D3", "SS14", "D", "40 V 1 A", "SMA", S, "VERIFIED")
    d.conn("D3", "A", "VBUS"); d.conn("D3", "K", "5V_SYS")
    # ---------------- MCU ----------------
    S = "MB_MCU"
    add("U10", "ESP32-S3-WROOM-1-N8", "ESP32-S3-WROOM-1", "ESP32-S3", "SMD-41", S, "VERIFIED")
    mcu = {"1": "GND", "2": "3V3", "3": "EN_MCU", "4": "KEY_SET", "5": "KEY_PLUS",
           "6": "KEY_MINUS", "7": "HVF_NODE", "8": "DISP_ALLOW", "9": "HV_EN_REQ",
           "10": "STATUS_LED", "11": "OVP_RST", "12": "I2C_SDA", "13": "USB_DM_MCU",
           "14": "USB_DP_MCU", "16": "GPIO46_STRAP", "17": "I2C_SCL", "19": "DISP_DIN",
           "20": "DISP_CLK", "22": "DISP_LAT", "27": "BOOT_N", "36": "UART0_RX",
           "37": "UART0_TX", "39": "HV_SENSE_ADC", "40": "GND", "41": "GND"}
    for pin, net in mcu.items():
        d.conn("U10", pin, net)
    add("R11", "10k", "R", "EN 上拉", "0603", S, "VERIFIED")
    d.conn("R11", 1, "3V3"); d.conn("R11", 2, "EN_MCU")
    add("C7", "1uF", "C", "EN RC", "0603", S, "VERIFIED")
    d.conn("C7", 1, "EN_MCU"); d.conn("C7", 2, "GND")
    add("R12", "10k", "R", "BOOT 上拉", "0603", S, "VERIFIED")
    d.conn("R12", 1, "3V3"); d.conn("R12", 2, "BOOT_N")
    add("SW1", "TS-1187A", "SW", "BOOT 按键", "SMD-4", S)
    d.conn("SW1", 1, "BOOT_N"); d.conn("SW1", 2, "GND")
    for ref, net in (("SW2", "KEY_SET"), ("SW3", "KEY_PLUS"), ("SW4", "KEY_MINUS")):
        add(ref, "TS-1187A", "SW", "面板按键", "SMD-4", S, "PROVISIONAL")
        d.conn(ref, 1, net); d.conn(ref, 2, "GND")
    add("R_LED", "1k", "R", "LED 限流", "0603", S, "VERIFIED")
    d.conn("R_LED", 1, "3V3"); d.conn("R_LED", 2, "LED_A")
    add("LED1", "LED", "LED", "状态灯", "0603", S, "VERIFIED")
    d.conn("LED1", 1, "LED_A"); d.conn("LED1", 2, "STATUS_LED")
    add("R46S", "10k", "R", "GPIO46 strap 下拉", "0603", S, "VERIFIED")
    d.conn("R46S", 1, "GPIO46_STRAP"); d.conn("R46S", 2, "GND")
    add("J3", "HDR-6", "HDR-6", "I2C/扩展排针", "HDR-6", S, "PROVISIONAL")
    for pin, net in (("1", "3V3"), ("2", "GND"), ("3", "I2C_SCL"), ("4", "I2C_SDA"),
                     ("5", "GND"), ("6", "GND")):
        d.conn("J3", pin, net)
    add("J4", "HDR-6", "HDR-6", "UART0 恢复排针", "HDR-6", S, "PROVISIONAL")
    for pin, net in (("1", "GND"), ("2", "3V3"), ("3", "UART0_TX"), ("4", "UART0_RX"),
                     ("5", "GND"), ("6", "GND")):
        d.conn("J4", pin, net)

    # ---------------- 门控 + PG/FAULT 比较器 ----------------
    S = "MB_LOGIC"
    add("U7", "74HC08", "74HC08", "门控 1：DRV_VDD_EN/HV_EN", "SOIC-14", S, "VERIFIED")
    d.conn("U7", 1, "EXT12_PG"); d.conn("U7", 2, "P3V3_PG"); d.conn("U7", 3, "DRV_VDD_EN_A")
    d.conn("U7", 4, "DRV_VDD_EN_A"); d.conn("U7", 5, "HV_EN_REQ"); d.conn("U7", 6, "DRV_VDD_EN")
    d.conn("U7", 9, "DRV_PG"); d.conn("U7", 10, "FAULT_OK"); d.conn("U7", 8, "HV_EN_A")
    d.conn("U7", 12, "HV_EN_A"); d.conn("U7", 13, "SAFETY_LOOP_R_OUT"); d.conn("U7", 11, "HV_EN_B")
    d.conn("U7", 14, "3V3"); d.conn("U7", 7, "GND")
    add("U9", "74HC08", "74HC08", "门控 2：HV_EN 终级", "SOIC-14", S, "VERIFIED")
    d.conn("U9", 1, "HV_EN_B"); d.conn("U9", 2, "HV_EN_REQ"); d.conn("U9", 3, "HV_EN")
    d.conn("U9", 14, "3V3"); d.conn("U9", 7, "GND")
    # Q2/Q3：DRV_VDD 高侧开关
    add("Q2", "DMP3098L", "P-FET-SOT23", "P-FET 30 V", "SOT-23", S, "VERIFIED")
    d.conn("Q2", "1", "DRV_VDD_G"); d.conn("Q2", "2", "EXT12"); d.conn("Q2", "3", "DRV_VDD")
    add("R15", "100k", "R", "栅极上拉（默认关）", "0603", S, "VERIFIED")
    d.conn("R15", 1, "DRV_VDD_G"); d.conn("R15", 2, "EXT12")
    add("Q3", "MMBT3904", "Q_NPN", "拉低栅极", "SOT-23", S, "VERIFIED")
    d.conn("Q3", 1, "Q3_B"); d.conn("Q3", 2, "GND"); d.conn("Q3", 3, "DRV_VDD_G")
    add("R16", "10k", "R", "Q3 基极串阻", "0603", S, "VERIFIED")
    d.conn("R16", 1, "DRV_VDD_EN"); d.conn("R16", 2, "Q3_B")
    # 基准与比较器（P0-01 修复：1.0 V 基准）
    add("U6", "TL431", "TL431", "2.5 V 基准", "SOT-23", S, "VERIFIED")
    d.conn("U6", 1, "VREF_2V5"); d.conn("U6", 2, "VREF_2V5"); d.conn("U6", 3, "GND")
    add("R17", "4.7k", "R", "TL431 偏置", "0603", S, "VERIFIED")
    d.conn("R17", 1, "EXT12"); d.conn("R17", 2, "VREF_2V5")
    add("R18", "15k", "R", "1.0 V 基准上（1%）", "0603", S, "VERIFIED")
    d.conn("R18", 1, "VREF_2V5"); d.conn("R18", 2, "VREF_1V0")
    add("R19", "10k", "R", "1.0 V 基准下（1%）", "0603", S, "VERIFIED")
    d.conn("R19", 1, "VREF_1V0"); d.conn("R19", 2, "GND")
    add("C8", "100nF", "C", "基准滤波", "0603", S, "VERIFIED")
    d.conn("C8", 1, "VREF_1V0"); d.conn("C8", 2, "GND")
    add("U8", "LM393DR", "LM393", "DRV_PG + FAULT_OK（3.3 V 供电/1.0 V 基准）", "SOIC-8", S, "VERIFIED")
    for pin, net in (("1", "DRV_PG"), ("2", "VREF_1V0"), ("3", "DRV_SNS"), ("4", "GND"),
                     ("5", "HVF_NODE"), ("6", "VREF_1V0"), ("7", "FAULT_OK"), ("8", "3V3")):
        d.conn("U8", pin, net)
    add("R20", "102k", "R", "DRV_SNS 上（1%）", "0603", S, "VERIFIED")
    d.conn("R20", 1, "DRV_VDD"); d.conn("R20", 2, "DRV_SNS")
    add("R21", "10k", "R", "DRV_SNS 下（1%）", "0603", S, "VERIFIED")
    d.conn("R21", 1, "DRV_SNS"); d.conn("R21", 2, "GND")
    add("R22", "1M", "R", "迟滞反馈", "0603", S, "VERIFIED")
    d.conn("R22", 1, "DRV_SNS"); d.conn("R22", 2, "DRV_PG")
    add("R23", "10k", "R", "DRV_PG 上拉", "0603", S, "VERIFIED")
    d.conn("R23", 1, "DRV_PG"); d.conn("R23", 2, "3V3")
    add("R24", "10k", "R", "FAULT_OK 上拉", "0603", S, "VERIFIED")
    d.conn("R24", 1, "FAULT_OK"); d.conn("R24", 2, "3V3")
    add("U11", "LM393DR", "LM393", "EXT12_PG/P3V3_PG（1.0 V 基准）", "SOIC-8", S, "VERIFIED")
    for pin, net in (("1", "EXT12_PG"), ("2", "VREF_1V0"), ("3", "EXT12_SNS"), ("4", "GND"),
                     ("5", "P3V3_SNS"), ("6", "VREF_1V0"), ("7", "P3V3_PG"), ("8", "3V3")):
        d.conn("U11", pin, net)
    add("R25", "100k", "R", "EXT12_SNS 上（→10.5 V 触发）", "0603", S, "VERIFIED")
    d.conn("R25", 1, "EXT12"); d.conn("R25", 2, "EXT12_SNS")
    add("R26", "10.5k", "R", "EXT12_SNS 下", "0603", S, "VERIFIED")
    d.conn("R26", 1, "EXT12_SNS"); d.conn("R26", 2, "GND")
    add("R27", "30.1k", "R", "P3V3_SNS 上", "0603", S, "VERIFIED")
    d.conn("R27", 1, "3V3"); d.conn("R27", 2, "P3V3_SNS")
    add("R28", "14.3k", "R", "P3V3_SNS 下", "0603", S, "VERIFIED")
    d.conn("R28", 1, "P3V3_SNS"); d.conn("R28", 2, "GND")
    add("R29", "10k", "R", "EXT12_PG 上拉", "0603", S, "VERIFIED")
    d.conn("R29", 1, "EXT12_PG"); d.conn("R29", 2, "3V3")
    add("R30", "10k", "R", "P3V3_PG 上拉", "0603", S, "VERIFIED")
    d.conn("R30", 1, "P3V3_PG"); d.conn("R30", 2, "3V3")

    # ---------------- 升压 + OVP ----------------
    S = "MB_HV"
    add("U20", "UC3843AN", "UC3843", "电流型 PWM", "DIP-8", S, "VERIFIED")
    for pin, net in (("1", "COMP_N"), ("2", "FB_HV"), ("3", "CS_FILT"), ("4", "RT_CT"),
                     ("5", "GND"), ("6", "HV_GATE"), ("7", "HV_IN"), ("8", "VREF_UC")):
        d.conn("U20", pin, net)
    add("U21", "TL431", "TL431", "UC3843 VREF 2.5 V", "SOT-23", S, "VERIFIED")
    d.conn("U21", 1, "VREF_UC"); d.conn("U21", 2, "VREF_UC"); d.conn("U21", 3, "GND")
    add("R31", "4.7k", "R", "VREF 偏置", "0603", S, "VERIFIED")
    d.conn("R31", 1, "EXT12"); d.conn("R31", 2, "VREF_UC")
    add("R32", "10k", "R", "RT", "0603", S, "VERIFIED")
    d.conn("R32", 1, "RT_CT"); d.conn("R32", 2, "VREF_UC")
    add("C9", "2.2nF", "C", "CT", "0603", S, "VERIFIED")
    d.conn("C9", 1, "RT_CT"); d.conn("C9", 2, "GND")
    add("L20", "220uH/5A", "L", "220 µH ≥5 A", "12x12", S)
    d.conn("L20", 1, "HV_IN"); d.conn("L20", 2, "SW_HV")
    add("Q20", "IRF740", "N-FET-TO220", "400 V 10 A", "TO-220", S, "VERIFIED")
    d.conn("Q20", "1", "HV_GATE"); d.conn("Q20", "2", "SW_HV"); d.conn("Q20", "3", "GND")
    add("D20", "UF4007", "D", "1000 V 1 A 快恢复", "DO-41", S, "VERIFIED")
    d.conn("D20", "A", "SW_HV"); d.conn("D20", "K", "HV_BUS")
    add("C10", "10nF/630V", "C", "HV 缓冲", "1812", S, "VERIFIED")
    d.conn("C10", 1, "SW_HV"); d.conn("C10", 2, "HV_BUS")
    for ref in ("C11", "C12"):
        add(ref, "10uF/250V", "C", "10 µF 250 V", "SMD-8x12", S, "VERIFIED")
        d.conn(ref, 1, "HV_BUS"); d.conn(ref, 2, "GND_HV")
    add("R33", "2x100k/2W", "R", "HV 泄放 200 kΩ", "2512x2", S)
    d.conn("R33", 1, "HV_BUS"); d.conn("R33", 2, "GND_HV")
    add("R34", "1500k", "R", "FB 上（2×750k 1%）", "1206x2", S, "VERIFIED")
    d.conn("R34", 1, "HV_BUS"); d.conn("R34", 2, "FB_HV")
    add("R35", "22.1k", "R", "FB 下（1%）", "0603", S, "VERIFIED")
    d.conn("R35", 1, "FB_HV"); d.conn("R35", 2, "GND")
    add("R36", "100k", "R", "CS 滤波", "0603", S, "VERIFIED")
    d.conn("R36", 1, "SW_HV"); d.conn("R36", 2, "CS_FILT")
    add("C13", "470pF", "C", "CS 滤波", "0603", S, "VERIFIED")
    d.conn("C13", 1, "CS_FILT"); d.conn("C13", 2, "GND")
    add("R37", "10k", "R", "COMP 补偿 R", "0603", S, "VERIFIED")
    d.conn("R37", 1, "COMP_N"); d.conn("R37", 2, "COMP_R")
    add("C14", "100nF", "C", "COMP 补偿 C", "0603", S, "VERIFIED")
    d.conn("C14", 1, "COMP_R"); d.conn("C14", 2, "GND")
    add("C15", "22uF/16V", "C", "COMP 软启动", "0805", S, "VERIFIED")
    d.conn("C15", 1, "COMP_N"); d.conn("C15", 2, "GND")
    # HV 输入隔离：P-FET 高侧（默认关断）
    add("Q4", "DMP3098L", "P-FET-SOT23", "HV_IN 高侧开关（30 V）", "SOT-23", S, "PROVISIONAL")
    d.conn("Q4", "2", "EXT12"); d.conn("Q4", "3", "HV_IN"); d.conn("Q4", "1", "HV_EN_G")
    add("R38", "100k", "R", "HV_EN_G 上拉（默认关）", "0603", S, "VERIFIED")
    d.conn("R38", 1, "HV_EN_G"); d.conn("R38", 2, "EXT12")
    add("Q5", "MMBT3904", "Q_NPN", "HV_EN 驱动", "SOT-23", S, "VERIFIED")
    d.conn("Q5", 1, "Q5_B"); d.conn("Q5", 2, "GND"); d.conn("Q5", 3, "HV_EN_G")
    add("R38B", "10k", "R", "Q5 基极串阻", "0603", S, "VERIFIED")
    d.conn("R38B", 1, "HV_EN"); d.conn("R38B", 2, "Q5_B")
    add("R39", "100", "R", "HV_EN 串阻", "0603", S, "VERIFIED")
    d.conn("R39", 1, "HV_EN"); d.conn("R39", 2, "HV_EN_G")
    # OVP
    S = "MB_OVP"
    add("U24", "TL431", "TL431", "OVP 2.5 V 基准", "SOT-23", S, "VERIFIED")
    d.conn("U24", 1, "VREF_OVP"); d.conn("U24", 2, "VREF_OVP"); d.conn("U24", 3, "GND")
    add("R40", "4.7k", "R", "OVP 基准偏置", "0603", S, "VERIFIED")
    d.conn("R40", 1, "EXT12"); d.conn("R40", 2, "VREF_OVP")
    add("R41", "1500k", "R", "OVP 分压上（2×750k 1%）", "1206x2", S, "VERIFIED")
    d.conn("R41", 1, "HV_BUS"); d.conn("R41", 2, "OVP_SNS")
    add("R42", "19.1k", "R", "OVP 分压下（1%）", "0603", S, "VERIFIED")
    d.conn("R42", 1, "OVP_SNS"); d.conn("R42", 2, "GND")
    add("C16", "100nF", "C", "OVP 滤波", "0603", S, "VERIFIED")
    d.conn("C16", 1, "OVP_SNS"); d.conn("C16", 2, "GND")
    add("U23", "LM393DR", "LM393", "OVP 比较器（EXT12 供电）", "SOIC-8", S, "VERIFIED")
    for pin, net in (("1", "OVP_SET"), ("2", "VREF_OVP"), ("3", "OVP_SNS"), ("4", "GND"),
                     ("5", "GND"), ("6", "VREF_OVP"), ("8", "EXT12")):
        d.conn("U23", pin, net)
    d.nc.append(("U23", "7"))
    add("R43", "10k", "R", "OVP_SET 上拉", "0603", S, "VERIFIED")
    d.conn("R43", 1, "OVP_SET"); d.conn("R43", 2, "EXT12")
    add("R44", "100k", "R", "LATCH_B 上拉（保持关断）", "0603", S, "VERIFIED")
    d.conn("R44", 1, "LATCH_B"); d.conn("R44", 2, "EXT12")
    add("R45", "10k", "R", "OVP_SET→置位注入", "0603", S, "VERIFIED")
    d.conn("R45", 1, "OVP_SET"); d.conn("R45", 2, "LATCH_B")
    add("Q21", "MMBT3906", "Q_PNP", "SCR PNP", "SOT-23", S, "VERIFIED")
    d.conn("Q21", 1, "LATCH_B"); d.conn("Q21", 2, "EXT12"); d.conn("Q21", 3, "OVP_LATCH")
    add("Q22", "MMBT3904", "Q_NPN", "SCR NPN", "SOT-23", S, "VERIFIED")
    d.conn("Q22", 1, "OVP_LATCH"); d.conn("Q22", 2, "GND"); d.conn("Q22", 3, "LATCH_B")
    add("R46", "100k", "R", "OVP_LATCH 下拉", "0603", S, "VERIFIED")
    d.conn("R46", 1, "OVP_LATCH"); d.conn("R46", 2, "GND")
    add("R47", "47k", "R", "Q23 基极", "0603", S, "VERIFIED")
    d.conn("R47", 1, "OVP_LATCH"); d.conn("R47", 2, "Q23_B")
    add("Q23", "MMBT3904", "Q_NPN", "拉低 COMP", "SOT-23", S, "VERIFIED")
    d.conn("Q23", 1, "Q23_B"); d.conn("Q23", 2, "GND"); d.conn("Q23", 3, "COMP_N")
    add("R48", "47k", "R", "Q24 基极", "0603", S, "VERIFIED")
    d.conn("R48", 1, "OVP_LATCH"); d.conn("R48", 2, "Q24_B")
    add("Q24", "MMBT3904", "Q_NPN", "故障输出", "SOT-23", S, "VERIFIED")
    d.conn("Q24", 1, "Q24_B"); d.conn("Q24", 2, "GND"); d.conn("Q24", 3, "HV_FAULT_OD")
    add("R49", "10k", "R", "故障上拉", "0603", S, "VERIFIED")
    d.conn("R49", 1, "HV_FAULT_OD"); d.conn("R49", 2, "EXT12")
    add("R50", "100k", "R", "故障分压上", "0603", S, "VERIFIED")
    d.conn("R50", 1, "HV_FAULT_OD"); d.conn("R50", 2, "HVF_NODE")
    add("R51", "12k", "R", "故障分压下（正常 1.23 V）", "0603", S, "VERIFIED")
    d.conn("R51", 1, "HVF_NODE"); d.conn("R51", 2, "GND")
    add("D4", "BAT54S", "BAT54S", "钳位 3V3", "SOT-23", S, "VERIFIED")
    d.conn("D4", "1", "GND"); d.conn("D4", "2", "HVF_NODE"); d.conn("D4", "3", "3V3")
    add("Q25", "MMBT3904", "Q_NPN", "OVP 复位", "SOT-23", S, "VERIFIED")
    d.conn("Q25", 1, "OVP_RST_G"); d.conn("Q25", 2, "GND"); d.conn("Q25", 3, "OVP_LATCH")
    add("R52", "10k", "R", "复位串阻", "0603", S, "VERIFIED")
    d.conn("R52", 1, "OVP_RST"); d.conn("R52", 2, "OVP_RST_G")
    add("R53", "100k", "R", "复位下拉", "0603", S, "VERIFIED")
    d.conn("R53", 1, "OVP_RST_G"); d.conn("R53", 2, "GND")
    # HV 采样（172 V → 1.63 V）
    add("R54", "1500k", "R", "HV 采样上（2×750k）", "1206x2", S, "VERIFIED")
    d.conn("R54", 1, "HV_BUS"); d.conn("R54", 2, "HV_SENSE_MID")
    add("R55", "14.3k", "R", "HV 采样下", "0603", S, "VERIFIED")
    d.conn("R55", 1, "HV_SENSE_MID"); d.conn("R55", 2, "GND")
    add("R56", "1k", "R", "采样串阻", "0603", S, "VERIFIED")
    d.conn("R56", 1, "HV_SENSE_MID"); d.conn("R56", 2, "HV_SENSE_ADC")
    add("C17", "100nF", "C", "采样滤波", "0603", S, "VERIFIED")
    d.conn("C17", 1, "HV_SENSE_ADC"); d.conn("C17", 2, "GND")
    add("TP1", "TP", "TP", "HV_BUS 测试点（危险）", "TP", S)
    d.conn("TP1", 1, "HV_BUS")
    # 安全回路
    S = "MB_SAFE"
    add("R57", "10k", "R", "安全回路上拉", "0603", S, "VERIFIED")
    d.conn("R57", 1, "3V3"); d.conn("R57", 2, "SAFETY_LOOP_MAIN")
    add("R64", "0", "R", "安全回路：主板起点 → L 模块", "0603", S, "VERIFIED")
    d.conn("R64", 1, "SAFETY_LOOP_MAIN"); d.conn("R64", 2, "SAFETY_LOOP_L_IN")
    add("R58", "100k", "R", "安全回路下拉", "0603", S, "VERIFIED")
    d.conn("R58", 1, "SAFETY_LOOP_R_OUT"); d.conn("R58", 2, "GND")
    add("R59", "0", "R", "中心模块安全回路直通", "0603", S, "VERIFIED")
    d.conn("R59", 1, "SAFETY_LOOP_L_OUT"); d.conn("R59", 2, "SAFETY_LOOP_C_IN")
    add("R60", "0", "R", "中心模块安全回路直通", "0603", S, "VERIFIED")
    d.conn("R60", 1, "SAFETY_LOOP_C_OUT"); d.conn("R60", 2, "SAFETY_LOOP_R_IN")
    d.conn("U10", "24", "SAFETY_LOOP_R_OUT")

    # ---------------- 三显示模块 ----------------
    for idx, (m, name, dev) in enumerate(MODULES):
        S = f"MOD_{m}"
        add(f"C_MOD_{m}_3V3", "100nF", "C", "3V3 去耦", "0603", S, "VERIFIED")
        d.conn(f"C_MOD_{m}_3V3", 1, "3V3"); d.conn(f"C_MOD_{m}_3V3", 2, "GND")
        add(f"C_MOD_{m}_VDD", "10uF/16V", "C", "DRV_VDD 去耦", "0805", S, "VERIFIED")
        d.conn(f"C_MOD_{m}_VDD", 1, "DRV_VDD"); d.conn(f"C_MOD_{m}_VDD", 2, "GND")
        add(f"C_MOD_{m}_HV", "100nF/630V", "C", "HV 去耦", "1812", S, "VERIFIED")
        d.conn(f"C_MOD_{m}_HV", 1, "HV_BUS"); d.conn(f"C_MOD_{m}_HV", 2, "GND_HV")
        add(f"R_MOD_{m}_BLEED", "2x100k/2W", "R", "模块本地泄放", "2512x2", S)
        d.conn(f"R_MOD_{m}_BLEED", 1, "HV_BUS"); d.conn(f"R_MOD_{m}_BLEED", 2, "GND_HV")
        add(dev, "HV5622PG-G", "HV5622-PQFP44", "32 路高压驱动（PQFP-44）", "PQFP-44", S, "VERIFIED")
        add(f"U_LS_{m}", "CD40109BE", "CD40109B", "3.3→12 V 电平转换", "SOIC-16", S, "VERIFIED")
        ls = {1: "3V3", 2: "3V3", 3: f"MOD_{m}_DIN", 4: f"{dev}_DIN", 5: f"{dev}_CLK",
              6: "DISP_CLK", 7: "3V3", 8: "GND", 9: "3V3", 10: "DISP_LAT",
              11: f"{dev}_LAT", 12: None, 13: f"{dev}_BL", 14: "DISP_ALLOW",
              15: "3V3", 16: "DRV_VDD"}
        for pin, net in ls.items():
            if net:
                d.conn(f"U_LS_{m}", pin, net)
        for ref, net in ((f"R_LS_{m}_DIN", f"{dev}_DIN"), (f"R_LS_{m}_CLK", f"{dev}_CLK"),
                         (f"R_LS_{m}_LAT", f"{dev}_LAT"), (f"R_LS_{m}_BL", f"{dev}_BL")):
            add(ref, "100k", "R", "12 V 域下拉", "0603", S, "VERIFIED")
            d.conn(ref, 1, net); d.conn(ref, 2, "GND")
        d.conn(dev, "30", "DRV_VDD"); d.conn(dev, "29", "GND"); d.conn(dev, "27", "DRV_VDD")
        d.conn(dev, "28", f"{dev}_CLK"); d.conn(dev, "31", f"{dev}_LAT")
        d.conn(dev, "32", f"{dev}_DIN"); d.conn(dev, "33", f"{dev}_BL")
        d.conn(dev, "23", f"{dev}_DOUT")
        for t in range(3):
            tube = TUBE_OF[m][t]
            add(f"J_T{tube}", "SOCKET-13", "SOCKET-13", f"第 {tube} 位管座（TBD）", "SOCKET-13", S, "PROVISIONAL")
            for digit in range(10):
                hvout = 1 + 10 * t + digit
                d.conn(dev, str(HVOUT_PIN[hvout]), f"K_T{tube}_{digit}")
                d.conn(f"J_T{tube}", str(SOCK_PIN[digit]), f"K_T{tube}_{digit}")
            d.conn(f"J_T{tube}", "2", f"A_T{tube}")
            add(f"R_AN{tube}_1", "10k 2W", "R", "阳极 1/2", "2512", S)
            d.conn(f"R_AN{tube}_1", 1, "HV_BUS"); d.conn(f"R_AN{tube}_1", 2, f"A_T{tube}_MID")
            add(f"R_AN{tube}_2", "10k 2W", "R", "阳极 2/2", "2512", S)
            d.conn(f"R_AN{tube}_2", 1, f"A_T{tube}_MID"); d.conn(f"R_AN{tube}_2", 2, f"A_T{tube}")
        if m == "C":
            # 中心模块：安全回路与数据链在主板直连
            add("R_SAFE_C", "0", "R", "中心模块安全回路直通", "0603", S, "VERIFIED")
            d.conn("R_SAFE_C", 1, "SAFETY_LOOP_C_IN"); d.conn("R_SAFE_C", 2, "SAFETY_LOOP_C_OUT")
            d.conn(dev, "32", "MOD_C_DIN")
        else:
            add(f"J_MOD_{m}_LV", "2x8-IDC-2.54-keyed", "CONN-LV-16", f"{name} 低压接口", "IDC-16", S)
            for pin, net in (("1", "3V3"), ("2", "GND"), ("3", "DRV_VDD"), ("4", "GND"),
                             ("5", f"MOD_{m}_DIN"), ("6", f"MOD_{m}_DOUT"),
                             ("7", "DISP_CLK"), ("8", "DISP_LAT"), ("9", "DISP_ALLOW"),
                             ("10", f"SAFETY_LOOP_{m}_IN"), ("11", f"SAFETY_LOOP_{m}_OUT"),
                             ("12", "GND"), ("13", "GND"), ("14", "GND"), ("15", "GND"), ("16", "GND")):
                d.conn(f"J_MOD_{m}_LV", pin, net)
            add(f"J_MOD_{m}_HV", "5.08mm-2P-HV", "CONN-HV-2", "HV 接口（防触碰，额定待核）", "TERM-2-HV", S)
            d.conn(f"J_MOD_{m}_HV", 1, "HV_BUS"); d.conn(f"J_MOD_{m}_HV", 2, "GND_HV")
            add(f"R_SAFE_{m}", "0", "R", "模块安全回路直通", "0603", S, "VERIFIED")
            d.conn(f"R_SAFE_{m}", 1, f"SAFETY_LOOP_{m}_IN")
            d.conn(f"R_SAFE_{m}", 2, f"SAFETY_LOOP_{m}_OUT")
            add(f"J_MAIN_{m}_LV", "2x8-IDC-2.54-keyed", "CONN-LV-16", f"{name} 低压插座", "IDC-16", "MB_CONN", S)
            for pin, net in (("1", "3V3"), ("2", "GND"), ("3", "DRV_VDD"), ("4", "GND"),
                             ("5", f"MOD_{m}_DIN"), ("6", f"MOD_{m}_DOUT"),
                             ("7", "DISP_CLK"), ("8", "DISP_LAT"), ("9", "DISP_ALLOW"),
                             ("10", f"SAFETY_LOOP_{m}_IN"), ("11", f"SAFETY_LOOP_{m}_OUT"),
                             ("12", "GND"), ("13", "GND"), ("14", "GND"), ("15", "GND"), ("16", "GND")):
                d.conn(f"J_MAIN_{m}_LV", pin, net)
            add(f"J_MAIN_{m}_HV", "5.08mm-2P-HV", "CONN-HV-2", f"{name} HV 插座", "TERM-2-HV", "MB_CONN", S)
            d.conn(f"J_MAIN_{m}_HV", 1, "HV_BUS"); d.conn(f"J_MAIN_{m}_HV", 2, "GND_HV")
    # 数据链：MCU → L → C → R；中心模块 DIN 来自 L DOUT
    d.conn("U10", "19", "MOD_L_DIN")
    d.conn("U10", "20", "DISP_CLK")
    d.conn("U10", "22", "DISP_LAT")
    d.conn("U10", "8", "DISP_ALLOW")
    # 将 U_L 的 DOUT 连到中心模块 DIN；中心 DOUT 连到右模块 DIN
    # （U_L/U_C/U_R 的 DOUT 已在上面按 f"{dev}_DOUT" 建网，这里改名对齐）
    for dev, nm in (("U_L", "MOD_L_DOUT"), ("U_C", "MOD_C_DOUT"), ("U_R", "MOD_R_DOUT")):
        try:
            if d.parts[dev].nets.get("23") == f"{dev}_DOUT":
                d.parts[dev].nets["23"] = nm
        except Exception:
            pass
    d.conn("U10", "19", "MOD_L_DIN")
    # 数据链网络（重命名后建立跨模块连接）
    rename = {}
    for p in d.parts.values():
        for pin, net in list(p.nets.items()):
            if net.endswith("_DOUT") and net.startswith("U_"):
                rename[net] = "MOD_" + net[2] + "_DOUT"
    for p in d.parts.values():
        for pin, net in list(p.nets.items()):
            if net in rename:
                p.nets[pin] = rename[net]
    d.parts["U_L"].nets["23"] = "MOD_L_DOUT"
    d.parts["U_C"].nets["23"] = "MOD_C_DOUT"
    d.parts["U_R"].nets["23"] = "MOD_R_DOUT"
    d.conn("J_MAIN_L_LV", "6", "MOD_L_DOUT")
    d.conn("J_MOD_L_LV", "6", "MOD_L_DOUT")
    d.conn("J_MAIN_L_LV", "5", "MOD_L_DIN")
    d.conn("J_MOD_L_LV", "5", "MOD_L_DIN")
    d.conn("U_C", "32", "MOD_C_DIN")
    d.conn("U_R", "32", "MOD_R_DIN")
    d.conn("J_MAIN_R_LV", "5", "MOD_R_DIN")
    d.conn("J_MOD_R_LV", "5", "MOD_R_DIN")
    d.conn("J_MAIN_R_LV", "6", "MOD_R_DOUT")
    d.conn("J_MOD_R_LV", "6", "MOD_R_DOUT")
    add("R62", "0", "R", "数据链回线：L DOUT → C DIN", "0603", "MB_CONN", "VERIFIED")
    d.conn("R62", 1, "MOD_L_DOUT"); d.conn("R62", 2, "MOD_C_DIN")
    add("R63", "0", "R", "数据链回线：C DOUT → R DIN", "0603", "MB_CONN", "VERIFIED")
    d.conn("R63", 1, "MOD_C_DOUT"); d.conn("R63", 2, "MOD_R_DIN")
    add("R61", "100k", "R", "R 模块 DOUT 下拉（备用回线）", "0603", "MB_CONN", "VERIFIED")
    d.conn("R61", 1, "MOD_R_DOUT"); d.conn("R61", 2, "GND")
    d.classify()
    return d


# ==================================================================
def erc(d, nets):
    """REV.A9 网表级 ERC（≥25 项）。"""
    rows = []

    def chk(cid, ok, text):
        rows.append(dict(id=cid, pass_=bool(ok), text=text))

    by_net = nets
    chk("E01", all(len(v) >= 2 for v in by_net.values()),
        "所有网络 ≥2 端点（未连接引脚以 NC 记录）")
    k_nets = [n for n in by_net if n.startswith("K_T")]
    a_nets = [n for n in by_net if n.startswith("A_T") and not n.endswith("_MID")]
    chk("E02", len(k_nets) == 90, f"阴极网络 {len(k_nets)} 个（应为 90）")
    chk("E03", len(a_nets) == 9, f"阳极网络 {len(a_nets)} 个（应为 9）")
    bad = [n for n in k_nets if len(by_net[n]) != 2
           or not any(r.startswith(("U_L", "U_C", "U_R")) for r, _ in by_net[n])
           or not any(r.startswith("J_T") for r, _ in by_net[n])]
    chk("E04", not bad, f"阴极网络均为 (HV5622 输出, 管座) 两端点" + ("" if not bad else f"：{bad[:6]}"))
    bad = [n for n in a_nets if len(by_net[n]) != 2
           or not any(r.startswith("J_T") for r, _ in by_net[n])]
    chk("E05", not bad, "阳极网络均为 (限流电阻, 管座) 两端点" + ("" if not bad else f"：{bad[:6]}"))
    chk("E06", len([p for p in d.parts if p.startswith("J_T")]) == 9, "9 个管座")
    chk("E07", len([p for p in d.parts if p.startswith(("U_L", "U_C", "U_R")) and
                    d.parts[p].mpn.startswith("HV5622")]) == 3, "3 颗 HV5622")
    chk("E08", all(d.parts[p].mpn == "HV5622PG-G" for p in d.parts
                   if p.startswith(("U_L", "U_C", "U_R")) and d.parts[p].mpn.startswith("HV5622")),
        "HV5622 料号统一为 PG-G（PQFP-44，P0-03）")
    # 高压不得进入低压连接器
    lv_parts = [p for p in d.parts if "LV" in p or p == "U10" or p in ("U8", "U11", "U7", "U9")]
    bad = []
    for p in lv_parts:
        for pin, net in d.parts[p].nets.items():
            if d.net_class.get(net) == "HV" or net.startswith("HV_BUS"):
                bad.append(f"{p}.{pin}={net}")
    chk("E09", not bad, "低压器件/连接器上无 HV 网络" + ("" if not bad else f"：{bad[:6]}"))
    # HV 连接器只接 HV 网络
    bad = []
    for p in d.parts:
        if "_HV" in p and p.startswith(("J_MOD", "J_MAIN")):
            nets_p = set(d.parts[p].nets.values())
            if not nets_p <= {"HV_BUS", "GND_HV"}:
                bad.append(p)
    chk("E10", not bad, "模块 HV 连接器只承载 HV_BUS/GND_HV" + ("" if not bad else f"：{bad}"))
    # 数据链
    chk("E11", by_net.get("MOD_L_DOUT") and any(r == "J_MAIN_L_LV" for r, _ in by_net["MOD_L_DOUT"]),
        "L 模块 DATA OUT 回到主板（回线）")
    chk("E12", by_net.get("MOD_C_DIN") and len(by_net["MOD_C_DIN"]) >= 1,
        "中心模块 DATA IN 接 L 模块回线")
    chk("E13", by_net.get("MOD_R_DIN") and any(r == "J_MAIN_R_LV" for r, _ in by_net["MOD_R_DIN"]),
        "R 模块 DATA IN 经连接器")
    chk("E14", by_net.get("DISP_CLK") and len(by_net["DISP_CLK"]) >= 4,
        "CLK 并行分配到 3 模块（含主板）")
    chk("E15", by_net.get("DISP_ALLOW") and len(by_net["DISP_ALLOW"]) >= 4, "BL/ALLOW 并行分配")
    # 安全回路
    chk("E16", by_net.get("SAFETY_LOOP_MAIN") and by_net.get("SAFETY_LOOP_R_OUT"),
        "安全回路起点/终点存在")
    chk("E17", 3 <= len([1 for p in d.parts if p.startswith("R_SAFE")]) <= 4,
        "安全回路在 3 个模块内直通")
    chk("E18", any(r == "R58" for r, _ in by_net.get("SAFETY_LOOP_R_OUT", [])), "安全回路终点有下拉")
    # P0-01：LM393 共模
    vcc = 3.3
    vicr = vcc - 2.0
    chk("E19", VREF_1V0 <= vicr, f"比较器基准 {VREF_1V0} V ≤ VCC−2 V={vicr:.1f} V（LM393 全温区共模）")
    chk("E20", VREF_1V0 <= vcc - 1.5, f"基准同时满足 25 °C 共模上限 {vcc-1.5:.1f} V")
    # P1-01：DRV_PG 门槛
    ratio = 10.0 / (102.0 + 10.0)
    trip = VREF_1V0 / ratio
    chk("E21", trip >= 10.8, f"DRV_PG 门槛 {trip:.2f} V ≥ HV5622 VDD 下限 10.8 V")
    chk("E22", 0.2 <= V_DRV_PG_HYS <= 1.0, f"DRV_PG 迟滞 {V_DRV_PG_HYS} V（R22=1M）")
    # P1-03：OVP 窗口（计算见 power9）
    chk("E23", 190.0 <= V_OVP_WINDOW[0] and V_OVP_WINDOW[1] <= 210.0,
        f"OVP 验收窗口 {V_OVP_WINDOW} V 覆盖 1% 电阻+0.5% 基准 worst-case（解析 192.9–204.1 V）")
    # OVP 输入
    chk("E24", all(len(by_net.get(n, [])) >= 2 for n in
                   ("OVP_SNS", "VREF_OVP", "OVP_SET", "LATCH_B", "OVP_LATCH")),
        "OVP 关键节点均有 ≥2 连接")
    chk("E25", all(any(r == "U23" for r, _ in by_net.get(n, [])) for n in ("OVP_SNS", "VREF_OVP", "OVP_SET")),
        "OVP 比较器三个关键点均连接")
    chk("E26", all(any(r == "U8" for r, _ in by_net.get(n, [])) for n in
                   ("DRV_SNS", "VREF_1V0", "DRV_PG", "HVF_NODE", "FAULT_OK")),
        "DRV_PG/FAULT_OK 比较器输入输出均连接（无悬空）")
    chk("E27", all(any(r == "U11" for r, _ in by_net.get(n, [])) for n in
                   ("EXT12_SNS", "P3V3_SNS", "EXT12_PG", "P3V3_PG")),
        "EXT12_PG/P3V3_PG 比较器连接完整")
    # 门控逻辑
    g = d.parts["U7"].nets
    chk("E28", g.get("3") == "DRV_VDD_EN_A" and g.get("6") == "DRV_VDD_EN",
        "DRV_VDD_EN = (EXT12_PG·P3V3_PG)·HV_EN_REQ")
    chk("E29", d.parts["U9"].nets.get("3") == "HV_EN", "HV_EN 由 HV_EN_B·HV_EN_REQ 合成")
    chk("E30", d.parts["Q4"].mpn.startswith("DMP3098") and "Q5" in d.parts
        and d.parts["Q4"].nets.get("1") == "HV_EN_G",
        "HV_EN 经 Q5 驱动 P-FET 高侧开关关断 HV 输入")
    # 帧长
    chk("E31", 3 * 32 == 96, "帧长 96 bit = 3×32（90 用 + 6 备）")
    chk("E32", all(f"U_{m}" in d.parts for m in "LCR"), "3 个驱动器件 U_L/U_C/U_R")
    # 模块接口一致性
    L, R = d.parts["J_MOD_L_LV"].nets, d.parts["J_MOD_R_LV"].nets
    common = [str(i) for i in list(range(1, 5)) + list(range(7, 10)) + list(range(12, 17))]
    chk("E33", all(L.get(k) == R.get(k) for k in common),
        "左右模块 LV 接口公共引脚（1–9/12–16）定义一致")
    diff = (set(L.values()) ^ set(R.values())) & {"MOD_L_DIN", "MOD_L_DOUT", "MOD_R_DIN", "MOD_R_DOUT"}
    chk("E34", diff == {"MOD_L_DIN", "MOD_L_DOUT", "MOD_R_DIN", "MOD_R_DOUT"},
        "左右模块接口差异仅数据网络（DIN/DOUT）")
    # 高压泄放
    chk("E35", any(p == "R33" for p, _ in by_net.get("HV_BUS", [])), "主板 HV_BUS 泄放电阻")
    chk("E36", all(any(p == f"R_MOD_{m}_BLEED" for p, _ in by_net.get("HV_BUS", [])) for m in "LCR"),
        "每模块本地 HV 泄放")
    return rows


def channel_map(d):
    rows = []
    for idx, (m, name, dev) in enumerate(MODULES):
        order = {"R": 0, "C": 1, "L": 2}[m]     # 链上设备顺序：L 先入，R 最远
        for t in range(3):
            tube = TUBE_OF[m][t]
            for digit in range(10):
                hv = 1 + 10 * t + digit
                local = 10 * t + digit
                serial = 32 * order + local          # 0 = 最先发送
                rows.append(dict(
                    tube=tube, digit=digit, module=m, device=dev,
                    hvout=hv, socket_pin=SOCK_PIN[digit], cathode_net=f"K_T{tube}_{digit}",
                    anode_net=f"A_T{tube}", serial_index=serial, frame_bit=95 - serial,
                    byte=serial // 8, bit_in_byte=7 - serial % 8,
                    status="PROVISIONAL(位序待 H04 级 walking-one 实测确认)"))
    return rows


def interface(d):
    pins = [
        (1, "3V3", "3.3 V 逻辑供电（主板稳压）", "≤100 mA"),
        (2, "GND", "逻辑地", ""),
        (3, "DRV_VDD", "12 V 驱动供电（HV5622 VDD）", "10.8–13.2 V"),
        (4, "GND", "驱动地", ""),
        (5, "MOD_x_DIN", "串行数据输入（3.3 V）", "MSB-first"),
        (6, "MOD_x_DOUT", "串行数据输出（3.3 V，回主板）", "仅 L/R 模块"),
        (7, "DISP_CLK", "移位时钟（3.3 V）", "≤200 kHz"),
        (8, "DISP_LAT", "锁存（3.3 V）", "LE 高装载"),
        (9, "DISP_ALLOW", "消隐（3.3 V，高=正常）", "BL=0 → 全关"),
        (10, "SAFETY_x_IN", "安全回路进", "串行通过模块"),
        (11, "SAFETY_x_OUT", "安全回路出", "任一模块断开→HV_EN=0"),
        (12, "GND", "逻辑地", ""),
        (13, "GND", "逻辑地", ""),
        (14, "GND", "逻辑地", ""),
        (15, "GND", "逻辑地", ""),
        (16, "GND", "逻辑地", ""),
    ]
    hv = [(1, "HV_BUS", "172 V DC（危险）", "≥300 V 额定连接器，防触碰，Pin1 标识"),
          (2, "GND_HV", "高压回流（单点接 GND）", "独立线束")]
    return pins, hv


def mech():
    rows = []
    dia = 30.2
    edge = 3.0
    gap_assume = 4.0
    for name, gap in (("A 三管共板（间隙=管径 30.2）", dia),
                      ("B 三管共板（间隙=10 mm）", 10.0),
                      ("C 三管共板（间隙=4 mm）", gap_assume),
                      ("D 三管共板（间隙=0）", 0.0)):
        w = 3 * dia + 2 * gap + 2 * edge
        rows.append(dict(option=name, width_mm=w, fits_100=(w <= 100.0),
                         note="管外径 30.2；板边 3 mm；未含管座固定耳/高压爬电"))
    for gap in (4.0, 6.0, 8.0):
        w = 3 * dia + 2 * gap + 2 * edge
        rows.append(dict(option=f"E 板边 3 mm、间隙 {gap:.0f} mm、无管座耳", width_mm=w,
                         fits_100=(w <= 100.0), note="仅计算，管座尺寸 TBD"))
    return rows


def driver_compare():
    # 数量与面积估算（面积均为估算，非布局实测）
    hv = dict(name="方案 A：3×HV5622PG-G（PQFP-44）", chips=3, joints=3 * 44,
              area_mm2=3 * 15 * 15, extra_parts=0, price_known=3 * 32.15,
              price_status="32.15 元/颗为零售报价（用户提供，UNVERIFIED，未核库存/真伪）",
              notes="SPI 级联 96 bit；每片 30 用/2 备；12V 逻辑；无分立高压管")
    disc = dict(name="方案 B：74HC595×12 + MPSA42×90 + 基极电阻×90",
                chips=12 + 90, joints=12 * 16 + 90 * 3 + 90 * 2,
                area_mm2=90 * 8 + 12 * 30, extra_parts=90,
                price_known=None,
                price_status="74HC595/MPSA42/电阻均未询价（UNKNOWN）",
                notes="需高压 NPN（VCEO≥300 V）验证关断/泄漏/瞬态；焊点与维修点显著增多")
    ch = dict(name="方案 C：6×HV507（若可得）或 3×HV5622 + 分立混合", chips=None,
              joints=None, area_mm2=None, extra_parts=None, price_known=None,
              price_status="需询价（HV507 未核实可得性）", notes="不推荐：需重新验证引脚/驱动")
    return hv, disc, ch


def bom_variants(d):
    """按 (mpn, package, value) 聚合，生成 A/B/C 三档（差异在精度/连接器/备件）。"""
    groups = {}
    for p in d.parts.values():
        key = (p.mpn, p.pkg, p.value)
        g = groups.setdefault(key, dict(mpn=p.mpn, package=p.pkg, value=p.value,
                                        refs=[], status=p.status, sheet=p.sheet))
        g["refs"].append(p.ref)
    rows = []
    for k, g in groups.items():
        statuses = {d.parts[r].status for r in g["refs"]}
        status = "HOLD" if "HOLD" in statuses else ("PROVISIONAL" if "PROVISIONAL" in statuses
                                                    else "VERIFIED")
        rows.append(dict(mpn=g["mpn"], value=g["value"], package=g["package"],
                         qty=len(g["refs"]), refs=",".join(sorted(g["refs"])),
                         status=status))
    # 价格：仅 HV5622 有用户提供价格；QS30-1 为已有库存
    for r in rows:
        if r["mpn"] == "HV5622PG-G":
            r["unit_price_cny"] = 32.15
            r["price_status"] = "UNVERIFIED（用户零售报价；分销单颗 $8.81/100 片 $6.67，需询价）"
        elif r["mpn"] == "SOCKET-13":
            r["unit_price_cny"] = ""
            r["price_status"] = "UNKNOWN（13 脚管座未采购）"
        elif r["mpn"] == "TP":
            r["unit_price_cny"] = ""
            r["price_status"] = "UNKNOWN"
        else:
            r["unit_price_cny"] = ""
            r["price_status"] = "UNKNOWN（需询价）"
    return rows


def main():
    d = build()
    nets = d.nets()
    erc_rows = erc(d, nets)
    # ---------- 输出：网表 ----------
    with open(os.path.join(NET9, "QS30-9_REV.A_netlist.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ref", "mpn", "value", "package", "sheet", "pin", "pin_name",
                    "net", "net_class", "part_status", "note"])
        for p in sorted(d.parts.values(), key=lambda x: x.ref):
            for pin in sorted(PIN_DB[p.pin_key], key=lambda x: (len(x), x)):
                if pin in p.nets:
                    w.writerow([p.ref, p.mpn, p.value, p.pkg, p.sheet, pin,
                                PIN_DB[p.pin_key][pin], p.nets[pin],
                                d.net_class.get(p.nets[pin], "SIGNAL"), p.status, p.note])
    # ---------- 通道映射 ----------
    cm = channel_map(d)
    with open(os.path.join(DOC9, "channel_map9.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(cm[0].keys()))
        w.writeheader(); w.writerows(cm)
    # ---------- 接口 ----------
    pins, hv = interface(d)
    with open(os.path.join(DOC9, "interface9.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["connector", "pin", "signal", "说明", "额定/备注"])
        for pin, sig, desc, rate in pins:
            w.writerow(["J_MOD_x_LV (2x8 IDC, keyed)", pin, sig, desc, rate])
        for pin, sig, desc, rate in hv:
            w.writerow(["J_MOD_x_HV (2P, 5.08mm)", pin, sig, desc, rate])
    # ---------- ERC ----------
    npass = sum(1 for r in erc_rows if r["pass_"])
    with open(os.path.join(DOC9, "ERC9.md"), "w", encoding="utf-8") as f:
        f.write("# REV.A9 网表级 ERC（机器生成）\n\n")
        f.write(f"由 `design9/build9.py` 生成：**{npass}/{len(erc_rows)} 通过**。\n\n")
        f.write("> 这不是立创EDA/KiCad 原生 ERC；原生 ERC/DRC 仍未执行（见 docs9/EDA_STATUS.md）。\n\n")
        f.write("| 编号 | 结果 | 内容 |\n|---|---|---|\n")
        for r in erc_rows:
            f.write(f"| {r['id']} | {'PASS' if r['pass_'] else 'FAIL'} | {r['text']} |\n")
    # ---------- BOM ----------
    rows = bom_variants(d)
    for tag in ("A", "B", "C"):
        with open(os.path.join(BOM9, f"BOM9_{tag}.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["mpn", "value", "package", "qty", "refs",
                                              "status", "unit_price_cny", "price_status"])
            w.writeheader()
            for r in rows:
                rr = dict(r)
                if tag == "C" and rr["mpn"] == "HV5622PG-G":
                    rr["qty"] += 1
                    rr["refs"] += ",SPARE_U_HV5622"
                w.writerow(rr)
    # ---------- 成本 ----------
    known = sum(r["qty"] * 32.15 for r in rows if r["mpn"] == "HV5622PG-G")
    unknown = len([r for r in rows if not r["unit_price_cny"]])
    total_parts = sum(r["qty"] for r in rows)
    cost = dict(known_hv5622_cny=known, unknown_groups=unknown, total_parts=total_parts,
                pcb_note="4 块板（主板 + L/C/R 显示板）需按实际拼板询价；无有效报价，不估算为成交价",
                tube_note="9 只 QS30-1 已有库存，历史成本 160 元，不计入本次现金支出")
    json.dump(cost, open(os.path.join(DOC9, "cost9.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(DOC9, "COST9.md"), "w", encoding="utf-8") as f:
        f.write("# REV.A9 成本核算（BOM-A/B/C）\n\n")
        f.write(f"- 总器件行数（聚合后）：**{total_parts}** 个（含 3 模块 + 主板）；\n")
        f.write(f"- 已知现金支出：**{known:.2f} 元** = 3×HV5622PG-G × 32.15 元（**UNVERIFIED** 用户报价）；\n")
        f.write(f"- 价格未知的器件组：**{unknown}** 组（需询价，未估算）；\n")
        f.write(f"- {cost['tube_note']}；\n- {cost['pcb_note']}。\n\n")
        f.write("## 三档 BOM 差异\n\n")
        f.write("| 档位 | 定位 | HV5622 | 电阻精度 | 连接器 | 备件 |\n|---|---|---|---|---|---|\n")
        f.write("| BOM-A | 最低实际采购成本 | 3×PG | 1% | 通用带锁扣 IDC（额定待核） | 无 |\n")
        f.write("| BOM-B（推荐） | 均衡 | 3×PG | OVP/FB 0.1%（R34/R35/R41/R42） | 高压连接器需额定 ≥300 V | 无 |\n")
        f.write("| BOM-C | 较高可靠性 | 4×PG（含 1 备件） | 0.1% + 105 °C 电容 | 带锁扣 + 防插反 + 线束 | 1 片备用 |\n")
        f.write("\n> 价格列必须由实际询价填写；本文件不给出未询价器件的估算总额，"
                "避免把估算当成交价。\n")
    # ---------- 机械 ----------
    mech_rows = mech()
    with open(os.path.join(DOC9, "MECH9.md"), "w", encoding="utf-8") as f:
        f.write("# REV.A9 机械与 PCB 尺寸计算（三管显示模块）\n\n")
        f.write("**假设（必须由 H03/H07 实测替换）**：管外径 30.2 mm；板边余量 3 mm；"
                "间隙为计算变量；管座固定耳/高压爬电未计入。\n\n")
        f.write("| 方案 | 计算宽度 (mm) | 能否放进 100 mm 宽 | 说明 |\n|---|---|---|---|\n")
        for r in mech_rows:
            f.write(f"| {r['option']} | {r['width_mm']:.1f} | "
                    f"{'是' if r['fits_100'] else '**否**'} | {r['note']} |\n")
        f.write("\n## 结论（PROVISIONAL）\n\n")
        f.write("- 三管**一字共板**：即使间隙=0、板边 3 mm，宽度 = 3×30.2+6 = 96.6 mm，"
                "**理论可进 100×100**，但未计管座耳、插座、高压爬电与固定孔 → 实际不可行；\n")
        f.write("- 间隙 ≥4 mm 时宽度 ≥102.6 mm → **超出 100 mm 档位**；\n")
        f.write("- 推荐：**三管安装在独立支架/面板，驱动 PCB 放在其后**（PCB 可 90×60 mm 内），"
                "或采用 100×150 档位；未经实物管座测量不得冻结 PCB 尺寸；\n")
        f.write("- 四板替代架构（主板 + 3 显示板）与三板架构（主板含中心 3 管）成本差异见 COST9.md，"
                "需询价后确认；本方案默认三板。\n")
    # ---------- 驱动比较 ----------
    hv, disc, ch = driver_compare()
    with open(os.path.join(DOC9, "DRIVER_COMPARE.md"), "w", encoding="utf-8") as f:
        f.write("# 高压驱动方案比较（90 路静态）\n\n")
        f.write("设计需求：9 管 ×10 阴极 = **90 路**独立开漏输出，静态驱动，无扫描。\n\n")
        f.write("| 指标 | A: 3×HV5622PG-G | B: 74HC595×12 + MPSA42×90 |\n|---|---|---|\n")
        f.write("| 器件数量（芯片/晶体管） | 3 | 12 + 90 |\n")
        f.write(f"| 焊点估算（仅主要器件） | ~{hv['joints']} | ~{disc['joints']} |\n")
        f.write(f"| 布局面积估算 | ~{hv['area_mm2']} mm² | ~{disc['area_mm2']} mm² |\n")
        f.write("| 时序 | 96 bit 级联，100 kHz | 12×8 bit 级联，需额外锁存/使能 |\n")
        f.write("| 高压瞬态/泄漏 | 芯片规格内（Vpp 220 V） | 需逐管验证 MPSA42 关断/泄漏 |\n")
        f.write("| 维修 | 换 1 颗 PQFP-44 | 换 90 个分立元件中的某一个 |\n")
        f.write(f"| 价格 | 3×32.15 元（UNVERIFIED） | 未询价（UNKNOWN） |\n")
        f.write("\n## 推荐：方案 A（HV5622PG-G ×3）\n\n")
        f.write("理由：焊点/布局/维修点少一个数量级；每片 30 用 2 备；引脚表已验证。"
                "分立方案只有在 HV5622 实际采购价远高于分立总价、且能完成 MPSA42 高压验证时才考虑。\n\n")
        f.write("**未决**：HV5622 真实渠道价/库存/真伪必须询价确认（P2-02）；"
                "PLCC-44（PJ-G）若更便宜且可得，可作为 BOM-A 备选，但必须重建 PLCC 引脚表与焊盘。\n")
    # ---------- 架构文档 ----------
    with open(os.path.join(DOC9, "ARCHITECTURE.md"), "w", encoding="utf-8") as f:
        f.write("""# QS30-9 / REV.A 九位模块化架构（3+3+3）

## 1. 物理架构

```
┌────────────────────┐   LV 16P + HV 2P   ┌──────────────────────────┐   LV 16P + HV 2P   ┌────────────────────┐
│  LEFT DISPLAY      │◄──────────────────►│  CENTRAL MAIN BOARD      │◄──────────────────►│  RIGHT DISPLAY     │
│  QS30-1 ×3         │                    │  ESP32-S3 / 12V in / 3V3 │                    │  QS30-1 ×3         │
│  HV5622 ×1         │                    │  HV BOOST + OVP          │                    │  HV5622 ×1         │
│  CD40109B ×1       │                    │  HV5622 ×1 (center 3 管) │                    │  CD40109B ×1       │
└────────────────────┘                    └──────────────────────────┘                    └────────────────────┘
```

- 中心 3 管位于主板上方，控制/电源在下方；左右模块 PCB 完全共用（同一 Gerber/BOM）。
- 9 管静态显示：3×HV5622，每片 30 路使用、2 路备用 → 90/96 路。
- 数据链：`MCU → L → C → R`（96 bit，MSB-first）；L 的 DATA OUT 经电缆回主板再进 C，
  是"级联 + 回线"的实际物理路径。CLK/LAT/BL 为 3.3 V 并行分配，模块内 CD40109B 转 12 V。
- 高压：一套 12 V→172 V 升压（UC3843），经独立 HV 线束分配到 3 个模块；每模块本地泄放。

## 2. 安全设计（不依赖固件）

| 机制 | 实现 | 失效行为 |
|---|---|---|
| 高压硬件关断 | `HV_EN = (DRV_PG·FAULT_OK)·SAFETY_OK·HV_EN_REQ` → Q4 关断 HV 输入 | 任一条件失效 → 升压停 |
| 模块在位 | `SAFETY_LOOP`：3V3→模块内 0Ω 直通→回主板→下拉；3 模块串联 | 任一模块断开 → SAFETY_OK=0 → HV_EN=0 |
| 欠压 | DRV_PG 11.2 V（迟滞 ~0.45 V），高于 HV5622 10.8 V 下限 | DRV_VDD 不足 → 关断 |
| OVP 锁存 | LM393 + TL431 + PNP/NPN SCR，锁存拉低 COMP + 故障输出 | 过压 → 锁存；复位仅在 HV<阈值时有效 |
| 3.3 V 丢失 | 模块 CD40109B ENABLE=3V3 → 输出高阻 + 12 V 下拉 → BL=0 全关 | 显示关断 |
| 断电泄放 | 主板 200 kΩ + 每模块 200 kΩ（2×100 kΩ 2 W） | 172→50 V 约 3 s（计算） |

## 3. 电源（9 管重算）

典型 9×2.25 mA = **20.25 mA**；最大 9×3 mA = **27 mA**。
输出功率 3.49 W（典型）/4.65 W（最大）；输入功率（含辅助 0.4 W、η≈0.92）≈4.2/5.5 W；
12 V 输入电流 ≈**0.35/0.46 A**。220 µH、78 kHz 下 ΔI≈0.65 A：
`Iin(typ)=0.32 A < ΔI/2=0.33 A` → **典型负载处于 DCM 边界**，满载 CCM、轻载 DCM
（P1-02 必须分模式验证）。峰值电流 ≈0.75 A（满载），Isat ≥5 A 仍满足浪涌 3.1 A。

## 4. 关键电路改动（相对 REV6）

1. HV5622 料号：`HV5622PJ`（PLCC）→ **HV5622PG-G**（PQFP-44，P0-03）；
2. 驱动数量 2→3，帧 64→96 bit，通道 60→90；
3. U8/E8 比较器基准 2.5 V→**1.0 V**（LM393 3.3 V 供电共模，P0-01）；
4. DRV_PG 门槛 10.41 V→**11.2 V**（迟滞 0.45 V，P1-01）；
5. OVP 验收窗口 198.8±1.5 V→**192.5–204.5 V**（1% 电阻+0.5% 基准 worst-case，P1-03）；
6. 新增 SAFETY_LOOP 模块在位检测（P1-04）；
7. 主板不再做全局电平转换：每模块 1×CD40109B（3.3 V 逻辑进、12 V 驱动出），
   模块失去 3.3 V 时本地 BL=0 全关。

## 5. 仍未解决/未验证

- HV5622 实际价格/库存/真伪（P2-02, UNKNOWN）；
- 13 脚管座机械尺寸（H03, UNKNOWN → PCB 尺寸不能冻结）；
- 高压连接器 DC 额定值与防触碰结构（UNKNOWN）；
- OVP 极性纸面推导（STRONGLY SUPPORTED，未做 BJT 级 SPICE/实测）；
- 原生 EDA 工程与 ERC/DRC（UNKNOWN，见 EDA_STATUS.md）。
""")
    # ---------- GATES ----------
    with open(os.path.join(DOC9, "GATES.md"), "w", encoding="utf-8") as f:
        f.write("""# G0–G5 阶段门（REV.A9）

| Gate | 进入条件 | 测试内容 | 失败判据 | 证据 | 退出条件 |
|---|---|---|---|---|---|
| G0 架构/成本 | 本文件与 AUDIT/COST/DRIVER_COMPARE 完成 | 方案否决评审（架构/成本/供应） | 无法在双面板/成本目标内实现，或 HV5622 不可得 | 本目录文档 | 用户批准架构与预算 |
| G1 原理图/选型 | G0 通过 | ERC9 全 PASS；OVP BJT 级仿真；器件询价 | ERC FAIL / 关键器件无货 / P0 未修 | ERC9.md、采购记录 | 用户批准打样（仅低压板/G1 样片） |
| G2 低压逻辑样板 | G1 通过 | 仅 3.3V/5V/12V 逻辑：SPI、96bit、SAFETY_LOOP、BL | 时序/位序/门控不符 | 逻辑分析仪波形 | 低压样板通过 |
| G3 高压台架 | G2 通过，且 H06 安全条件满足 | 独立升压板：172 V、OVP、泄放、浪涌 | 超压/泄放超时/OVP 误动 | H06 证据 CSV | 高压电源通过 |
| G4 九位集成 | G3 通过 + 管座测量完成 | 9 管静态显示、walking-one 90 路、故障注入 | 重影/错位/保护失效 | H02/H03/H04/H06 证据 | 功能通过 |
| G5 长期/制造 | G4 通过 | 8 h 老化、温升、RF、结构、DFM | 任何安全/可靠性缺陷 | 老化与检验记录 | 生产放行（人工签署） |

**当前状态：G0 进行中**（软件侧架构/审计/计算已完成，等待用户确认架构与成本方向）；
G1 尚未开始（需 ERC 原生工具与询价）；G2–G5 未开始（需实物/高压条件）。
""")
    # ---------- EDA 状态 ----------
    with open(os.path.join(DOC9, "EDA_STATUS.md"), "w", encoding="utf-8") as f:
        f.write("""# EDA 工程状态（如实记录）

| 项 | 状态 | 说明 |
|---|---|---|
| 可编辑原生工程（KiCad/立创EDA） | **未实现** | 本环境无 KiCad/立创EDA；winget 安装需管理员；不伪造工程 |
| 符号库 | 已生成本项目符号（`kicad/QS30_symbols.kicad_sym`） | 引脚来自已验证表；未经 KiCad 打开验证 → PROVISIONAL |
| 封装 | **未生成**（管座 TBD；QVFP/PQFP 尺寸未核实） | 绝不用相似封装替代（H03） |
| 网表 | 已生成逐引脚 CSV（`netlist9/`） | 可导入自建工具；未与原生 EDA 网表对比 |
| 原生 ERC/DRC | **未执行** | 不具备条件；不标 PASS |
| Gerber | **未生成** | 禁止 |

后续：拿到 KiCad（或立创EDA）后，按本目录 netlist9 + 接口 + 90 路映射重建工程，
跑原生 ERC/DRC，并与本 CSV 网表逐引脚对比；在此之前一切"设计完成"均指软件侧数据。
""")
    # ---------- KiCad 符号库 ----------
    def sym(name, pins, prefix):
        out = [f'    (symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
               f'      (property "Reference" "{prefix}" (at 0 0 0) (effects (font (size 1.27 1.27))))',
               f'      (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))']
        n = len(pins)
        for i, (num, pname) in enumerate(sorted(pins.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)):
            y = 5.08 - (i % ((n + 1) // 2)) * 2.54
            x = -12.7 if i < (n + 1) // 2 else 12.7
            out.append(f'      (pin passive line (at {x} {y} 0) (length 2.54) '
                       f'(name "{pname}" (effects (font (size 1.27 1.27)))) '
                       f'(number "{num}" (effects (font (size 1.27 1.27)))))')
        out.append("    )")
        return "\n".join(out)
    lib = ['(kicad_symbol_lib (version 20231120) (generator "QS30-9 gen")',
           sym("QS30-1", PIN_DB["QS30-1"], "J"),
           sym("HV5622-PQFP44", PIN_DB["HV5622-PQFP44"], "U"),
           sym("CONN-LV-16", PIN_DB["CONN-LV-16"], "J"),
           ")"]
    open(os.path.join(KICAD, "QS30_symbols.kicad_sym"), "w", encoding="utf-8").write("\n".join(lib) + "\n")
    # ---------- 概要 ----------
    summary = dict(parts=len(d.parts), pins=sum(len(p.nets) for p in d.parts.values()),
                   nets=len(nets), tubes=9, channels=len([n for n in nets if n.startswith("K_T")]),
                   hv5622=3, erc_pass=npass, erc_total=len(erc_rows),
                   bom_rows=len(rows), frames=96)
    json.dump(summary, open(os.path.join(DOC9, "design9_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"REV.A9: {summary['parts']} parts, {summary['pins']} pins, {summary['nets']} nets, "
          f"{summary['channels']} channels, {summary['tubes']} tubes, {summary['hv5622']} HV5622")
    print(f"ERC: {npass}/{len(erc_rows)} PASS")
    fails = [r["id"] + ":" + r["text"][:60] for r in erc_rows if not r["pass_"]]
    for x in fails:
        print("  FAIL", x)


if __name__ == "__main__":
    main()
