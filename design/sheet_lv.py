# -*- coding: utf-8 -*-
"""QS30-6 REV.A low-voltage sheets (01, 02, 03) and tube sheet (05).

Every connection below is expressed as (ref, datasheet pin, net).
Pin numbers are verified against the original datasheets (see PIN_DB).
"""
from model import add, conn, nc, net_class


def build():
    # =====================================================================
    # SHEET 01  电源输入与保护 / 12 V -> 5 V -> 3.3 V / DRV_VDD 负载开关
    # =====================================================================
    S = "01_PWR"
    add("J1", "DC-005-5.08-2P", "DC12 IN 5.08mm 2P", "TERM-2",
        "PROVISIONAL", "D4", "12 V DC 输入端子（机械形式待结构确认）", S,
        pin_key="HDR-2", note="H05/H07")
    conn("J1", 1, "EXT12_RAW"); conn("J1", 2, "GND")

    add("F1", "PPTC-1.5A-1812", "1.5 A 自恢复保险丝", "1812",
        "PROVISIONAL", "D4", "输入过流保护（保持电流 1.5 A）", S,
        pin_key="FUSE", note="H05")
    conn("F1", 1, "EXT12_RAW"); conn("F1", 2, "EXT12_F")

    add("D1", "SMBJ16A", "TVS 16 V 单向", "SMB",
        "PROVISIONAL", "D4", "12 V 输入端瞬态抑制（Standoff 16 V）", S,
        pin_key="TVS", note="H05")
    conn("D1", 1, "EXT12_F"); conn("D1", 2, "GND")

    add("D2", "SS54", "40 V 5 A 肖特基", "SMB",
        "VERIFIED", "D4", "输入反接保护 + 反向阻断（Vf≈0.45 V @1 A）", S,
        pin_key="D", note="H05：如需低压降可改理想二极管")
    conn("D2", 1, "EXT12"); conn("D2", 2, "EXT12_F")

    add("C1", "100uF/25V", "100 µF 25 V 电解", "8x10.5 SMD",
        "VERIFIED", "D4", "输入储能", S, pin_key="C")
    conn("C1", 1, "EXT12"); conn("C1", 2, "GND")
    add("C2", "1uF/50V", "1 µF 50 V X7R", "1206", "VERIFIED", "D4",
        "输入高频旁路", S, pin_key="C")
    conn("C2", 1, "EXT12"); conn("C2", 2, "GND")
    add("C3", "100nF/50V", "0.1 µF 50 V X7R", "0603", "VERIFIED", "D4",
        "输入高频旁路", S, pin_key="C")
    conn("C3", 1, "EXT12"); conn("C3", 2, "GND")

    # ---- 12 V -> 5.0 V   TPS54202 (Vref = 0.596 V) ----------------------
    add("U1", "TPS54202DDCR", "TPS54202 12V->5.0V 2A", "SOT-23-6",
        "VERIFIED", "S8", "同步降压 12 V -> 5.08 V / 2 A, 500 kHz, 内置软启动", S,
        note="H05：纹波/温升/EMI 待测")
    conn("U1", 3, "EXT12"); conn("U1", 1, "GND"); conn("U1", 5, "EN_U1")
    conn("U1", 6, "BOOT_U1"); conn("U1", 2, "SW_U1"); conn("U1", 4, "FB_U1")
    add("R1", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S8",
        "EN 分压上臂（UVLO≈4.8 V）", S, pin_key="R")
    conn("R1", 1, "EXT12"); conn("R1", 2, "EN_U1")
    add("R2", "33k", "33 kΩ 1%", "0603", "VERIFIED", "S8",
        "EN 分压下臂", S, pin_key="R")
    conn("R2", 1, "EN_U1"); conn("R2", 2, "GND")
    add("C4", "10uF/25V", "10 µF 25 V X5R", "1206", "VERIFIED", "S8",
        "U1 输入旁路", S, pin_key="C")
    conn("C4", 1, "EXT12"); conn("C4", 2, "GND")
    add("C5", "100nF/50V", "0.1 µF 50 V X7R", "0603", "VERIFIED", "S8",
        "BOOT 自举电容", S, pin_key="C")
    conn("C5", 1, "BOOT_U1"); conn("C5", 2, "SW_U1")
    add("L1", "10uH/3A", "10 µH 3 A 屏蔽功率电感", "0630", "PROVISIONAL", "S8",
        "U1 储能电感，Isat≥3 A", S, pin_key="L")
    conn("L1", 1, "SW_U1"); conn("L1", 2, "EXT5")
    add("R3", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S8",
        "5 V 反馈上臂", S, pin_key="R")
    conn("R3", 1, "EXT5"); conn("R3", 2, "FB_U1")
    add("R4", "13.3k", "13.3 kΩ 1%", "0603", "VERIFIED", "S8",
        "5 V 反馈下臂 → Vout=0.596*(1+100/13.3)=5.08 V", S, pin_key="R")
    conn("R4", 1, "FB_U1"); conn("R4", 2, "GND")
    add("C6", "22uF/10V", "22 µF 10 V X5R", "0805", "VERIFIED", "S8",
        "5 V 输出电容", S, pin_key="C")
    conn("C6", 1, "EXT5"); conn("C6", 2, "GND")
    add("C7", "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S8",
        "5 V 输出高频旁路", S, pin_key="C")
    conn("C7", 1, "EXT5"); conn("C7", 2, "GND")

    # ---- 5V_SYS 双肖特基 OR（反向阻断）--------------------------------
    add("D3", "SS14", "40 V 1 A 肖特基", "SMA", "VERIFIED", "S9",
        "外部 5 V 理想二极管/肖特基 OR（反向阻断）", S, pin_key="D",
        note="H05：候选 B 为理想二极管 IC，本图为参考实现")
    conn("D3", 1, "5V_SYS"); conn("D3", 2, "EXT5")
    add("D4", "SS14", "40 V 1 A 肖特基", "SMA", "VERIFIED", "S9",
        "USB VBUS OR 支路（反向阻断）", S, pin_key="D")
    conn("D4", 1, "5V_SYS"); conn("D4", 2, "VBUS")
    add("C8", "22uF/10V", "22 µF 10 V X5R", "0805", "VERIFIED", "S9",
        "5V_SYS 储能（Wi-Fi 瞬态）", S, pin_key="C")
    conn("C8", 1, "5V_SYS"); conn("C8", 2, "GND")
    add("C9", "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S9",
        "5V_SYS 高频旁路", S, pin_key="C")
    conn("C9", 1, "5V_SYS"); conn("C9", 2, "GND")

    # ---- 5V_SYS -> 3.3 V   SY8089A (2.7-5.5 V, 2 A) ---------------------
    add("U2", "SY8089AAAC", "SY8089A 5V->3.3V 2A", "SOT-23-5",
        "VERIFIED", "S10", "同步降压 5V_SYS -> 3.315 V / 2 A, 1 MHz", S,
        note="H05：3.3 V 容量按 800 mA 分配实测")
    conn("U2", 4, "5V_SYS"); conn("U2", 2, "GND"); conn("U2", 1, "EN_U2")
    conn("U2", 3, "SW_U2"); conn("U2", 5, "FB_U2")
    add("R5", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S10",
        "U2 EN 上拉（默认开启）", S, pin_key="R")
    conn("R5", 1, "5V_SYS"); conn("R5", 2, "EN_U2")
    add("C10", "10uF/10V", "10 µF 10 V X5R", "0805", "VERIFIED", "S10",
        "U2 输入旁路", S, pin_key="C")
    conn("C10", 1, "5V_SYS"); conn("C10", 2, "GND")
    add("L2", "2.2uH/3A", "2.2 µH 3 A 屏蔽功率电感", "0520", "PROVISIONAL", "S10",
        "U2 储能电感", S, pin_key="L")
    conn("L2", 1, "SW_U2"); conn("L2", 2, "3V3")
    add("R6", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S10",
        "3.3 V 反馈上臂", S, pin_key="R")
    conn("R6", 1, "3V3"); conn("R6", 2, "FB_U2")
    add("R7", "22.1k", "22.1 kΩ 1%", "0603", "VERIFIED", "S10",
        "3.3 V 反馈下臂 → Vout=0.6*(1+100/22.1)=3.315 V", S, pin_key="R")
    conn("R7", 1, "FB_U2"); conn("R7", 2, "GND")
    add("C11", "22uF/6.3V", "22 µF 6.3 V X5R", "0805", "VERIFIED", "S10",
        "3.3 V 输出电容", S, pin_key="C")
    conn("C11", 1, "3V3"); conn("C11", 2, "GND")
    add("C12", "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S10",
        "3.3 V 高频旁路", S, pin_key="C")
    conn("C12", 1, "3V3"); conn("C12", 2, "GND")

    # ---- DRV_VDD 12 V 负载开关（默认关断）-----------------------------
    add("Q1", "DMP3098L", "P-MOSFET 30 V/3.8 A", "SOT-23",
        "PROVISIONAL", "S11", "DRV_VDD 高边开关（±20 V Vgs，无需钳位）", S,
        pin_key="P-FET", note="H04")
    conn("Q1", 1, "Q1_G"); conn("Q1", 2, "EXT12"); conn("Q1", 3, "DRV_VDD")
    add("R8", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S11",
        "Q1 栅极上拉至源极 → 默认关断", S, pin_key="R")
    conn("R8", 1, "EXT12"); conn("R8", 2, "Q1_G")
    add("Q2", "2N7002", "N-MOSFET 60 V", "SOT-23", "VERIFIED", "S11",
        "Q1 栅极下拉驱动（低电平有效）", S, pin_key="N-FET")
    conn("Q2", 1, "Q2_G"); conn("Q2", 2, "GND"); conn("Q2", 3, "Q1_G")
    add("R9", "100Ω", "100 Ω 1%", "0603", "VERIFIED", "S11",
        "Q2 栅极串联电阻", S, pin_key="R")
    conn("R9", 1, "DRV_VDD_EN"); conn("R9", 2, "Q2_G")
    add("R10", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S11",
        "Q2 栅极下拉 → 上电默认关断", S, pin_key="R")
    conn("R10", 1, "Q2_G"); conn("R10", 2, "GND")
    add("C13", "10uF/25V", "10 µF 25 V X5R", "1206", "VERIFIED", "S11",
        "DRV_VDD 储能", S, pin_key="C")
    conn("C13", 1, "DRV_VDD"); conn("C13", 2, "GND")
    add("C14", "100nF/50V", "0.1 µF 50 V X7R", "0603", "VERIFIED", "S11",
        "DRV_VDD 高频旁路", S, pin_key="C")
    conn("C14", 1, "DRV_VDD"); conn("C14", 2, "GND")

    # =====================================================================
    # SHEET 02  ESP32-S3-WROOM-1-N8 + USB-C + UART0 + 按键/接口
    # =====================================================================
    S = "02_MCU"
    add("U10", "ESP32-S3-WROOM-1-N8", "ESP32-S3 8MB Flash 无 PSRAM",
        "WROOM-1 41pad", "VERIFIED", "S1",
        "主控模组，板载 PCB 天线，焊盘编号按 Espressif 数据手册表 3-1", S,
        note="S1 焊盘表；H08 天线/整机 RF")
    m = {1: "GND", 2: "3V3", 3: "EN_MCU", 4: "KEY_SET", 5: "KEY_PLUS",
         6: "KEY_MINUS", 7: "HVF_NODE", 8: "DISP_ALLOW", 9: "HV_EN_REQ",
         10: "STATUS_LED", 11: "OVP_RST", 12: "I2C_SDA", 13: "USB_DM_MCU",
         14: "USB_DP_MCU", 15: "NC", 16: "GPIO46_STRAP", 17: "I2C_SCL",
         18: "NC", 19: "DISP_DIN", 20: "DISP_CLK", 21: "EXP_IO13",
         22: "DISP_LAT", 23: "EXP_IO21", 24: "NC", 25: "NC", 26: "NC",
         27: "BOOT_N", 28: "NC", 29: "NC", 30: "NC", 31: "NC",
         32: "NC", 33: "NC", 34: "NC", 35: "NC", 36: "UART0_RX",
         37: "UART0_TX", 38: "NC", 39: "HV_SENSE_ADC", 40: "GND",
         41: "GND"}
    for pin, net in m.items():
        if net == "NC":
            nc("U10", pin)
        else:
            conn("U10", pin, net)
    for ref, val in (("C16", "22uF/6.3V"), ("C17", "1uF/16V"),
                     ("C18", "100nF/16V")):
        add(ref, val.split("/")[0], val.replace("/", " "), "0805" if "22uF" in val else "0603",
            "VERIFIED", "S3", "模组 3V3 去耦", S, pin_key="C")
        conn(ref, 1, "3V3"); conn(ref, 2, "GND")
    # EN / BOOT / strapping
    add("R11", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S3",
        "EN 上拉（Espressif 推荐 10 kΩ）", S, pin_key="R")
    conn("R11", 1, "3V3"); conn("R11", 2, "EN_MCU")
    add("C19", "1uF/16V", "1 µF 16 V X7R", "0603", "VERIFIED", "S3",
        "EN RC 延时电容（Espressif 推荐 10k/1µF）", S, pin_key="C")
    conn("C19", 1, "EN_MCU"); conn("C19", 2, "GND")
    add("SW1", "TS-1187A", "复位按键", "4P 6x6 SMD", "PROVISIONAL", "S3",
        "RESET 按键（EN 拉低）", S, pin_key="SW_PUSH")
    conn("SW1", 1, "EN_MCU"); conn("SW1", 2, "GND")
    add("SW2", "TS-1187A", "BOOT 按键", "4P 6x6 SMD", "PROVISIONAL", "S4",
        "强制下载（GPIO0 拉低后释放 RESET）", S, pin_key="SW_PUSH")
    conn("SW2", 1, "BOOT_N"); conn("SW2", 2, "GND")
    add("R12", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S4",
        "GPIO0 上拉（Espressif 推荐）", S, pin_key="R")
    conn("R12", 1, "3V3"); conn("R12", 2, "BOOT_N")
    add("R13", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S3",
        "GPIO46 下拉（保持官方默认启动条件）", S, pin_key="R")
    conn("R13", 1, "GPIO46_STRAP"); conn("R13", 2, "GND")

    # ---- USB-C 原生 USB Serial/JTAG ------------------------------------
    add("J2", "USB-C-16P-2.0", "USB-C 母座 16P USB2.0", "SMD 16P",
        "PROVISIONAL", "S2", "USB-C 设备端（USB 2.0 only）", S,
        pin_key="USBC-16P", note="H05：封装/沉板形式待确认")
    for pin in ("A4", "A9", "B4", "B9"):
        conn("J2", pin, "VBUS")
    for pin in ("A1", "A12", "B1", "B12"):
        conn("J2", pin, "GND")
    for pin in ("A6", "B6"):
        conn("J2", pin, "USB_DP_CON")
    for pin in ("A7", "B7"):
        conn("J2", pin, "USB_DM_CON")
    conn("J2", "A5", "CC1"); conn("J2", "B5", "CC2")
    nc("J2", "A8", "B8")
    for pin in ("S1", "S2", "S3", "S4"):
        conn("J2", pin, "SHIELD")
    add("R14", "5.1k", "5.1 kΩ 1%", "0603", "VERIFIED", "S2",
        "CC1 下拉（UFP 5.1 kΩ）", S, pin_key="R")
    conn("R14", 1, "CC1"); conn("R14", 2, "GND")
    add("R15", "5.1k", "5.1 kΩ 1%", "0603", "VERIFIED", "S2",
        "CC2 下拉（UFP 5.1 kΩ）", S, pin_key="R")
    conn("R15", 1, "CC2"); conn("R15", 2, "GND")
    add("R16", "1M", "1 MΩ 1%", "0603", "VERIFIED", "S2",
        "屏蔽层泄放（RC 并联到 GND）", S, pin_key="R")
    conn("R16", 1, "SHIELD"); conn("R16", 2, "GND")
    add("C20", "4.7nF/50V", "4.7 nF 50 V X7R", "0603", "VERIFIED", "S2",
        "屏蔽层高频接地", S, pin_key="C")
    conn("C20", 1, "SHIELD"); conn("C20", 2, "GND")
    add("C21", "1uF/16V", "1 µF 16 V X7R", "0603", "VERIFIED", "S2",
        "VBUS 旁路（连接器侧）", S, pin_key="C")
    conn("C21", 1, "VBUS"); conn("C21", 2, "GND")
    add("C22", "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S2",
        "VBUS 高频旁路", S, pin_key="C")
    conn("C22", 1, "VBUS"); conn("C22", 2, "GND")
    add("U11", "USBLC6-2SC6", "USB ESD 保护", "SOT-23-6",
        "VERIFIED", "S12", "USB D+/D- ESD（I/O1: 1-6, I/O2: 3-4, VBUS:5）", S)
    conn("U11", 1, "USB_DP_CON"); conn("U11", 6, "USB_DP_ESD")
    conn("U11", 3, "USB_DM_CON"); conn("U11", 4, "USB_DM_ESD")
    conn("U11", 2, "GND"); conn("U11", 5, "VBUS")
    add("R17", "22Ω", "22 Ω 1%", "0402", "PROVISIONAL", "S2",
        "USB D+ 串联电阻（Espressif 建议 22/33 Ω，实测调整）", S, pin_key="R")
    conn("R17", 1, "USB_DP_ESD"); conn("R17", 2, "USB_DP_MCU")
    add("R18", "22Ω", "22 Ω 1%", "0402", "PROVISIONAL", "S2",
        "USB D- 串联电阻", S, pin_key="R")
    conn("R18", 1, "USB_DM_ESD"); conn("R18", 2, "USB_DM_MCU")
    add("C23", "10pF/50V", "10 pF 50 V", "0402", "PROVISIONAL", "S2",
        "USB D+ 对地预留电容（默认不装）", S, pin_key="C", flags=("DNP",))
    conn("C23", 1, "USB_DP_MCU"); conn("C23", 2, "GND")
    add("C24", "10pF/50V", "10 pF 50 V", "0402", "PROVISIONAL", "S2",
        "USB D- 对地预留电容（默认不装）", S, pin_key="C", flags=("DNP",))
    conn("C24", 1, "USB_DM_MCU"); conn("C24", 2, "GND")

    # ---- UART0 恢复/日志接口 -------------------------------------------
    add("J3", "HDR-1x6-2.54", "UART0 恢复排针 1x6", "2.54mm",
        "VERIFIED", "S3", "GND/3V3参考/TX/RX/EN/BOOT", S, pin_key="HDR-6",
        note="3V3 参考点经 0Ω(DNP) 连接，不默认向外供电")
    conn("J3", 1, "GND"); conn("J3", 2, "UART_3V3_REF")
    conn("J3", 3, "UART0_TX_H"); conn("J3", 4, "UART0_RX")
    conn("J3", 5, "EN_MCU"); conn("J3", 6, "BOOT_N")
    add("R19", "499Ω", "499 Ω 1%", "0603", "VERIFIED", "S3",
        "U0TXD 串联电阻（Espressif 建议 499 Ω 抑制谐波）", S, pin_key="R")
    conn("R19", 1, "UART0_TX"); conn("R19", 2, "UART0_TX_H")
    add("R20", "0Ω", "0 Ω", "0603", "VERIFIED", "S3",
        "3V3 参考点限流/隔离（默认不装）", S, pin_key="R", flags=("DNP",))
    conn("R20", 1, "3V3"); conn("R20", 2, "UART_3V3_REF")

    # ---- 按键（按交接表 GPIO4/5/6）------------------------------------
    for ref, net, desc in (("SW3", "KEY_SET", "SET"), ("SW4", "KEY_PLUS", "PLUS"),
                           ("SW5", "KEY_MINUS", "MINUS")):
        add(ref, "TS-1187A", f"{desc} 按键", "4P 6x6 SMD", "PROVISIONAL", "S3",
            f"{desc} 键（按下拉低）", S, pin_key="SW_PUSH")
        conn(ref, 1, net); conn(ref, 2, "GND")
    for ref, net in (("R21", "KEY_SET"), ("R22", "KEY_PLUS"), ("R23", "KEY_MINUS")):
        add(ref, "10k", "10 kΩ 1%", "0603", "VERIFIED", "S3",
            "按键上拉", S, pin_key="R")
        conn(ref, 1, net); conn(ref, 2, "3V3")
    for ref, net in (("C25", "KEY_SET"), ("C26", "KEY_PLUS"), ("C27", "KEY_MINUS")):
        add(ref, "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S3",
            "按键硬件去抖", S, pin_key="C")
        conn(ref, 1, net); conn(ref, 2, "GND")

    # ---- 状态 LED / I2C 预留 -------------------------------------------
    add("LED1", "LTST-C190KRKT", "红色 LED", "0603", "VERIFIED", "S3",
        "状态指示（GPIO17 高有效）", S, pin_key="LED")
    add("R24", "1k", "1 kΩ 1%", "0603", "VERIFIED", "S3",
        "LED 限流（约 1.3 mA @3.3 V）", S, pin_key="R")
    conn("R24", 1, "STATUS_LED"); conn("R24", 2, "LED1_A")
    conn("LED1", 2, "LED1_A"); conn("LED1", 1, "GND")
    add("R25", "4.7k", "4.7 kΩ 1%", "0603", "VERIFIED", "S3",
        "I2C SDA 上拉（预留，默认不装）", S, pin_key="R", flags=("DNP",))
    conn("R25", 1, "3V3"); conn("R25", 2, "I2C_SDA")
    add("R26", "4.7k", "4.7 kΩ 1%", "0603", "VERIFIED", "S3",
        "I2C SCL 上拉（预留，默认不装）", S, pin_key="R", flags=("DNP",))
    conn("R26", 1, "3V3"); conn("R26", 2, "I2C_SCL")

    # ---- HV 检测接口（H06 关闭前仅为接口占位）------------------------
    add("R27", "1M", "1 MΩ 1% 1206", "1206", "PROVISIONAL", "S3",
        "HV 分压上臂 1/2（170 V 下每只约 85 V）", S, pin_key="R", note="H06")
    conn("R27", 1, "HV_BUS"); conn("R27", 2, "HVS_MID")
    add("R28", "1M", "1 MΩ 1% 1206", "1206", "PROVISIONAL", "S3",
        "HV 分压上臂 2/2", S, pin_key="R", note="H06")
    conn("R28", 1, "HVS_MID"); conn("R28", 2, "HVS_NODE")
    add("R29", "20k", "20 kΩ 1%", "0805", "PROVISIONAL", "S3",
        "HV 分压下臂 → 172 V 对应 1.70 V（ADC1_CH0, ATTEN=3）", S,
        pin_key="R", note="H06：分压比/钳位/回灌待复核")
    conn("R29", 1, "HVS_NODE"); conn("R29", 2, "GND")
    add("R30", "1k", "1 kΩ 1%", "0603", "PROVISIONAL", "S3",
        "ADC 输入串联限流", S, pin_key="R")
    conn("R30", 1, "HVS_NODE"); conn("R30", 2, "HV_SENSE_ADC")
    add("C28", "100nF/16V", "0.1 µF 16 V X7R", "0603", "VERIFIED", "S3",
        "ADC 滤波电容（Espressif 建议 0.1 µF）", S, pin_key="C")
    conn("C28", 1, "HV_SENSE_ADC"); conn("C28", 2, "GND")
    add("D5", "BAT54", "肖特基 30 V", "SOD-323", "VERIFIED", "S3",
        "HV_SENSE 上限钳位到 3V3", S, pin_key="D")
    conn("D5", 1, "3V3"); conn("D5", 2, "HV_SENSE_ADC")
    add("D6", "BAT54", "肖特基 30 V", "SOD-323", "VERIFIED", "S3",
        "HV_SENSE 下限钳位到 GND", S, pin_key="D")
    conn("D6", 1, "HV_SENSE_ADC"); conn("D6", 2, "GND")

    # ---- HV 故障状态输入接口（12 V 域开漏 → 3.3 V）-------------------
    add("R31", "100k", "100 kΩ 1%", "0603", "PROVISIONAL", "S3",
        "故障开漏上拉分压上臂（DRV_VDD 11.5 V → 3.06 V）", S, pin_key="R",
        note="H04")
    conn("R31", 1, "HV_FAULT_OD"); conn("R31", 2, "HVF_NODE")
    add("R32", "36.5k", "36.5 kΩ 1%", "0603", "PROVISIONAL", "S3",
        "故障分压下臂 → 无故障时 3.06 V", S, pin_key="R")
    conn("R32", 1, "HVF_NODE"); conn("R32", 2, "GND")
    add("C29", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S3",
        "故障输入滤波", S, pin_key="C")
    conn("C29", 1, "HVF_NODE"); conn("C29", 2, "GND")
    add("D7", "BAT54", "肖特基 30 V", "SOD-323", "VERIFIED", "S3",
        "故障输入上限钳位", S, pin_key="D")
    conn("D7", 1, "3V3"); conn("D7", 2, "HVF_NODE")
    add("D8", "BAT54", "肖特基 30 V", "SOD-323", "VERIFIED", "S3",
        "故障输入下限钳位", S, pin_key="D")
    conn("D8", 1, "HVF_NODE"); conn("D8", 2, "GND")

    # =====================================================================
    # SHEET 03  驱动器（HV5622 x2）、3.3 V->DRV_VDD 电平转换、监控与门控
    # =====================================================================
    S = "03_DRV"
    # ---- 3.3 V -> 12 V 电平转换（CD40109B，VCC=3V3, VDD=DRV_VDD）-----
    add("U3", "CD40109B", "四路低→高电平转换 #1", "SOIC-16",
        "VERIFIED", "S13", "DIN/CLK/LAT/ALLOW → 12 V 域，输出三态", S)
    for pin, net in ((1, "3V3"), (16, "DRV_VDD"), (8, "GND"), (12, "NC"),
                     (2, "3V3"), (3, "DISP_DIN"), (4, "DRV_DIN"),
                     (7, "3V3"), (6, "DISP_CLK"), (5, "DRV_CLK"),
                     (9, "3V3"), (10, "DISP_LAT"), (11, "DRV_LAT"),
                     (15, "3V3"), (14, "DISP_ALLOW"), (13, "DRV_BL")):
        if net == "NC":
            nc("U3", pin)
        else:
            conn("U3", pin, net)
    add("U4", "CD40109B", "四路低→高电平转换 #2", "SOIC-16",
        "VERIFIED", "S13", "HV_EN_REQ → 12 V 域；其余通道接地", S)
    for pin, net in ((1, "3V3"), (16, "DRV_VDD"), (8, "GND"), (12, "NC"),
                     (2, "3V3"), (3, "HV_EN_REQ"), (4, "DRV_HV_EN_REQ"),
                     (7, "3V3"), (6, "GND"),
                     (9, "3V3"), (10, "GND"),
                     (15, "3V3"), (14, "GND")):
        if net == "NC":
            nc("U4", pin)
        else:
            conn("U4", pin, net)
    nc("U4", 5, 11, 13)
    add("C30", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S13",
        "U3/U4 VCC 旁路", S, pin_key="C")
    conn("C30", 1, "3V3"); conn("C30", 2, "GND")
    add("C31", "100nF/50V", "0.1 µF 50 V", "0603", "VERIFIED", "S13",
        "U3/U4 VDD 旁路", S, pin_key="C")
    conn("C31", 1, "DRV_VDD"); conn("C31", 2, "GND")
    for ref, net, val in (("R33", "DRV_DIN", "10k"), ("R34", "DRV_CLK", "10k"),
                          ("R35", "DRV_LAT", "10k"), ("R36", "DRV_BL", "10k"),
                          ("R37", "DRV_HV_EN_REQ", "10k")):
        add(ref, val, f"{val} 1%", "0603", "VERIFIED", "S3",
            "12 V 域下拉：驱动未上电/高阻时保持低电平（BL 低=消隐）", S,
            pin_key="R")
        conn(ref, 1, net); conn(ref, 2, "GND")

    # ---- 电源与故障监控 ------------------------------------------------
    add("U5", "LM393DR", "双比较器 #1（EXT12 / 3V3 监控）", "SOIC-8",
        "VERIFIED", "S14", "开漏输出，VCC=3V3", S)
    conn("U5", 8, "3V3"); conn("U5", 4, "GND")
    conn("U5", 3, "EXT12_SNS"); conn("U5", 2, "VREF_2V5"); conn("U5", 1, "EXT12_PG")
    conn("U5", 5, "P3V3_SNS"); conn("U5", 6, "VREF_2V5"); conn("U5", 7, "P3V3_PG")
    add("U8", "LM393DR", "双比较器 #2（DRV_VDD / 故障状态）", "SOIC-8",
        "VERIFIED", "S14", "开漏输出，VCC=3V3", S)
    conn("U8", 8, "3V3"); conn("U8", 4, "GND")
    conn("U8", 3, "DRV_SNS"); conn("U8", 2, "VREF_2V5"); conn("U8", 1, "DRV_PG")
    conn("U8", 5, "HVF_NODE"); conn("U8", 6, "VREF_2V5"); conn("U8", 7, "FAULT_OK")
    add("U6", "TL431", "2.5 V 并联基准", "SOT-23", "VERIFIED", "S17",
        "VREF=2.5 V 基准（Ika≈1.18 mA）；DBZ 引脚 1=C/2=REF/3=A", S)
    # DBZ: 1=CATHODE, 2=REF, 3=ANODE；REF 与 CATHODE 短接 = 2.5 V
    conn("U6", 1, "VREF_2V5"); conn("U6", 2, "VREF_2V5"); conn("U6", 3, "GND")
    add("R38", "680Ω", "680 Ω 1%", "0603", "VERIFIED", "S14",
        "TL431 偏置（(3.3-2.5)/680 = 1.18 mA）", S, pin_key="R")
    conn("R38", 1, "3V3"); conn("R38", 2, "VREF_2V5")
    add("C32", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "基准旁路", S, pin_key="C")
    conn("C32", 1, "VREF_2V5"); conn("C32", 2, "GND")
    add("C33", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "U5 旁路", S, pin_key="C")
    conn("C33", 1, "3V3"); conn("C33", 2, "GND")
    add("C34", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "U8 旁路", S, pin_key="C")
    conn("C34", 1, "3V3"); conn("C34", 2, "GND")
    add("R39", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S14",
        "EXT12 检测分压上臂 → 门限 10.80 V（=HV5622 VDD 下限）", S, pin_key="R")
    conn("R39", 1, "EXT12"); conn("R39", 2, "EXT12_SNS")
    add("R40", "30.1k", "30.1 kΩ 1%", "0603", "VERIFIED", "S14",
        "EXT12 检测分压下臂（2.5 V*(130.1/30.1)=10.80 V）", S, pin_key="R")
    conn("R40", 1, "EXT12_SNS"); conn("R40", 2, "GND")
    add("C35", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "EXT12_PG 滤波（约 3 ms）", S, pin_key="C")
    conn("C35", 1, "EXT12_SNS"); conn("C35", 2, "GND")
    add("R41", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S14",
        "EXT12_PG 上拉", S, pin_key="R")
    conn("R41", 1, "EXT12_PG"); conn("R41", 2, "3V3")
    add("R42", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S14",
        "3V3 检测分压上臂 → 门限 3.11 V", S, pin_key="R")
    conn("R42", 1, "3V3"); conn("R42", 2, "P3V3_SNS")
    add("R43", "41.2k", "41.2 kΩ 1%", "0603", "VERIFIED", "S14",
        "3V3 检测分压下臂（2.5 V*(51.2/41.2)=3.11 V）", S, pin_key="R")
    conn("R43", 1, "P3V3_SNS"); conn("R43", 2, "GND")
    add("C36", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "3V3_PG 滤波", S, pin_key="C")
    conn("C36", 1, "P3V3_SNS"); conn("C36", 2, "GND")
    add("R44", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S14",
        "3V3_PG 上拉", S, pin_key="R")
    conn("R44", 1, "P3V3_PG"); conn("R44", 2, "3V3")
    add("R45", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S14",
        "DRV_VDD 检测分压上臂 → 门限 10.4 V", S, pin_key="R")
    conn("R45", 1, "DRV_VDD"); conn("R45", 2, "DRV_SNS")
    add("R46", "31.6k", "31.6 kΩ 1%", "0603", "VERIFIED", "S14",
        "DRV_VDD 检测分压下臂（2.5 V*(131.6/31.6)=10.41 V）", S, pin_key="R")
    conn("R46", 1, "DRV_SNS"); conn("R46", 2, "GND")
    add("C37", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S14",
        "DRV_PG 滤波", S, pin_key="C")
    conn("C37", 1, "DRV_SNS"); conn("C37", 2, "GND")
    add("R47", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S14",
        "DRV_PG 上拉", S, pin_key="R")
    conn("R47", 1, "DRV_PG"); conn("R47", 2, "3V3")
    add("R48", "10k", "10 kΩ 1%", "0603", "VERIFIED", "S14",
        "FAULT_OK 上拉", S, pin_key="R")
    conn("R48", 1, "FAULT_OK"); conn("R48", 2, "3V3")

    # ---- 硬件使能门控（74HC08，默认关断）-----------------------------
    add("U7", "74HC08", "四路与门", "SOIC-14", "VERIFIED", "S15",
        "DRV_VDD_EN / HV_EN 硬件门控（EXT12_PG×3V3_PG×请求×DRV_PG×无故障）", S)
    for pin, net in ((14, "3V3"), (7, "GND"),
                     (1, "EXT12_PG"), (2, "P3V3_PG"), (3, "PG_12V3V"),
                     (4, "PG_12V3V"), (5, "HV_EN_REQ"), (6, "DRV_VDD_EN"),
                     (9, "DRV_PG"), (10, "FAULT_OK"), (8, "DRV_OK"),
                     (12, "DRV_OK"), (13, "HV_EN_REQ"), (11, "HV_EN")):
        conn("U7", pin, net)
    add("C38", "100nF/16V", "0.1 µF 16 V", "0603", "VERIFIED", "S15",
        "U7 旁路", S, pin_key="C")
    conn("C38", 1, "3V3"); conn("C38", 2, "GND")
    add("R49", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S15",
        "HV_EN 下拉 → 上电/复位默认关断", S, pin_key="R")
    conn("R49", 1, "HV_EN"); conn("R49", 2, "GND")
    add("R51", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S3",
        "HV_EN_REQ 外部下拉 → 上电/复位默认不请求升压", S, pin_key="R")
    conn("R51", 1, "HV_EN_REQ"); conn("R51", 2, "GND")
    add("R52", "100k", "100 kΩ 1%", "0603", "VERIFIED", "S3",
        "DISP_ALLOW 外部下拉 → 上电/复位默认消隐", S, pin_key="R")
    conn("R52", 1, "DISP_ALLOW"); conn("R52", 2, "GND")

    # ---- HV5622 高压驱动（44-pin PQFP）-------------------------------
    for ref, dout in (("U21", "DRV1_DOUT"), ("U22", "DRV2_DOUT")):
        add(ref, "HV5622PJ", "HV5622 32 路开漏高压驱动", "PQFP-44",
            "VERIFIED", "S5", "32-bit 移位寄存器 + 32 路 220 V 开漏输出", S,
            note="S5：VPP 推荐 ≤220 V，绝对最大 230 V；VDD 10.8–13.2 V")
        din = "DRV_DIN" if ref == "U21" else "DRV1_DOUT"
        conn(ref, 30, "DRV_VDD"); conn(ref, 29, "GND")
        conn(ref, 27, "DRV_VDD")          # POL 固定高电平（驱动域）
        conn(ref, 28, "DRV_CLK"); conn(ref, 32, din)
        conn(ref, 23, dout); conn(ref, 31, "DRV_LAT"); conn(ref, 33, "DRV_BL")
        nc(ref, 24, 25, 26, 34)
        add("C" + ("39" if ref == "U21" else "40"), "10uF/25V",
            "10 µF 25 V X5R", "1206", "VERIFIED", "S5",
            f"{ref} VDD 储能", S, pin_key="C")
        conn("C" + ("39" if ref == "U21" else "40"), 1, "DRV_VDD")
        conn("C" + ("39" if ref == "U21" else "40"), 2, "GND")
        add("C" + ("41" if ref == "U21" else "42"), "100nF/50V",
            "0.1 µF 50 V X7R", "0603", "VERIFIED", "S5",
            f"{ref} VDD 高频旁路", S, pin_key="C")
        conn("C" + ("41" if ref == "U21" else "42"), 1, "DRV_VDD")
        conn("C" + ("41" if ref == "U21" else "42"), 2, "GND")
    return
