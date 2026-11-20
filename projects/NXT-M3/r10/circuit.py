"""R10 engineering connectivity and package candidates. Pins are physical pad IDs."""
from pathlib import Path
import csv

HERE = Path(__file__).resolve().parent
G, V, F = "GND", "3V3", "5V_PROT"
R0603 = "Resistor_SMD:R_0603_1608Metric"
R2512 = "Resistor_SMD:R_2512_6332Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
SOT = "Package_TO_SOT_SMD:SOT-23"
SOT5 = "Package_TO_SOT_SMD:SOT-23-5"
SOT6 = "Package_TO_SOT_SMD:SOT-23-6"
DGK = "Package_SO:VSSOP-8_3x3mm_P0.65mm"
R8 = HERE.parent / "r8"
parts = []
kinds = {}
sheet = ""
hold = False

def kind(name, definition, fp="", url=""):
    types = dict(i="input", o="output", p="passive", v="power_in",
                 w="power_out", d="open_collector", b="bidirectional", t="tri_state")
    pins = {}
    for index, entry in enumerate(definition.split(), 1):
        signal, type_code = entry.split(":")
        pins[str(index)] = (signal, types[type_code])
    kinds[name] = (pins, fp, url)

def add(ref, name, value, nets, mpn="", *, fp=None, status=None):
    pins, package, url = kinds[name]
    items = nets.split() if isinstance(nets, str) else nets
    if len(items) != len(pins):
        raise ValueError(f"{ref}: {len(items)} nets, expected {len(pins)}")
    status = status or ("HOLD_DNP" if hold else "ENGINEERING_CANDIDATE")
    parts.append(dict(ref=ref, kind=name, value=value, fp=package if fp is None else fp,
                      url=url, mpn=mpn, sheet=sheet, status=status,
                      nets=dict(zip(pins, (None if net == "-" else net for net in items)))))

def r(ref, value, a, b, mpn="", fp=R0603, status=None):
    add(ref, "R", value, [a,b], mpn, fp=fp, status=status)

def c(ref, value, a, b=G, fp=C0603, mpn=""):
    add(ref, "C", value, [a,b], mpn, fp=fp)

def l(ref, value, a, b, mpn, fp):
    add(ref, "L", value, [a,b], mpn, fp=fp)

def tp(ref, net):
    add(ref, "TP", net, [net])

def ti(part):
    return f"https://www.ti.com/lit/ds/symlink/{part}.pdf"

kind("R","1:p 2:p",R0603)
kind("C","1:p 2:p",C0603)
kind("L","1:p 2:p")
kind("Flag","PWR:w")
kind("TP","Probe:p","TestPoint:TestPoint_Pad_D1.5mm")
kind("Header2","1:p 2:p","Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
kind("UARTBuffer","OE_N:i A:i GND:v Y:o VCC:v",SOT5,ti("sn74lvc1g125"))
kind("UART4","GND:p TX_to_target:p RX_from_target:p EN_open_drain:p",
     "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical")
kind("OLED4","GND:p VDD:p SCL:p SDA:p",
     "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical")
kind("Switch","1:p 2:p","Button_Switch_SMD:SW_SPST_TL3342")
kind("Fuse","1:p 2:p","Fuse:Fuse_1206_3216Metric")
kind("Diode","K:p A:p")
kind("MOS","G:i S:p D:p",SOT)
kind("NPN","B:i E:p C:p",SOT,
     "https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf")
kind("eFuse","EN:i OVLO:i PG:d PGTH:i IN:v OUT:w DVDT:p GND:v ILM:p ITIMER:p",
     "R10_R10:TI_RPW0010A",ti("tps25947"))
kind("Buck","PGND:v VIN:v EN:i AGND:v FB:i VOS:i SW:o PG:d EP:p",
     "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",ti("tps62162"))
kind("Supervisor","RESET_N:d GND:v MR_N:i CT:p SENSE:i VDD:v",SOT6,ti("tps3808"))
kind("HC595","QB:t QC:t QD:t QE:t QF:t QG:t QH:t GND:v QH_SER:o SRCLR_N:i SRCLK:i RCLK:i OE_N:i SER:i QA:t VCC:v",
     "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",ti("sn74hc595"))
kind("AND","A:i B:i GND:v Y:o VCC:v",SOT5,ti("sn74lvc1g08"))
kind("FF","CLK:i D:i Q_N:o GND:v Q:o CLR_N:i PRE_N:i VCC:v",
     "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",ti("sn74lvc1g74"))
kind("LoadSwitch","VIN:v GND:v ON:i CT:p QOD:p VOUT:w",SOT6,ti("tps22918"))
kind("I2C","VCCA:v SCLA:b SDAA:b GND:v EN:i SDAB:b SCLB:b VCCB:v",DGK,ti("tca9517a"))
kind("TVS2","IO1:p IO2:p GND:p","Package_TO_SOT_SMD:SOT-323_SC-70",ti("tpd2e2u06"))
kind("Watchdog","VDD1:v CWD:p SET0:i CRST:p GND:v SET1:i WDI:i WDO:d NC:p VDD2:v EP:p","Package_SON:Texas_DRC0010J",ti("tps3430"))
kind("Reference","IN:v OUT:w GND:v",SOT,ti("ref33"))
kind("Compare","OUT1:d N1:i P1:i GND:v P2:i N2:i OUT2:d VCC:v",DGK,ti("tlv1701"))
kind("BoostBias","SW:o GND:v FB:i EN:i VIN:v",SOT5,ti("tps61040"))
kind("BoostHV","BIAS:v VCC:w GATE:o PGND:v CS:i COMP:p AGND:v FB:i SS:p RT:p PGOOD:d UVLO:i EP:p",
     "Package_SON:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65.kicad_mod".removesuffix(".kicad_mod"),ti("lm5155"))
kind("GateDriver","VDD:v OUTH:o OUTL:o GND:v IN_MINUS:i IN_PLUS:i",SOT6,ti("ucc27511"))
kind("PowerMOS","G:i D:p S:p","Package_TO_SOT_SMD:TO-252-2",
     "https://www.st.com/resource/en/datasheet/std13n60m2.pdf")
kind("Socket","A:p UNUSED_2:p K0:p K9:p K8:p K7:p K6:p UNUSED_8:p K5:p K4:p K3:p K2:p K1:p")
kind("ESP32",
     "GND:v 3V3:v EN:i IO4:b IO5:b IO6:b IO7:b IO15:b IO16:b IO17:b IO18:b IO8:b "
     "IO19_USB_DM:b IO20_USB_DP:b IO3:b IO46:i IO9:b IO10:b IO11:b IO12:b IO13:b IO14:b "
     "IO21:b IO47:b IO48:b IO45:b IO0:b IO35:b IO36:b IO37:b IO38:b IO39:b IO40:b "
     "IO41:b IO42:b RXD0:i TXD0:o IO2:b IO1:b GND:v GND_EP:v",
     "RF_Module:ESP32-S3-WROOM-1",
     "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf")

sheet = "Input_and_3V3"
add("J1","Header2","5 V IN JST XH harness candidate",["5V_RAW",G],"B2B-XH-A(LF)(SN)",fp="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical")
add("F1","Fuse","2 A candidate","5V_RAW 5V_FUSED","0467002.NR")
add("U1","eFuse","TPS259474LRPWR","FRONT_EN FRONT_OVLO - FRONT_PGTH 5V_FUSED 5V_PROT FRONT_DVDT GND FRONT_ILM FRONT_TIMER","TPS259474LRPWR")
r("R1","360k","5V_FUSED","FRONT_EN")
r("R2","150k","FRONT_EN",G)
r("R3","390k","5V_FUSED","FRONT_OVLO")
r("R4","110k","FRONT_OVLO",G)
r("R5","1.65k","FRONT_ILM",G)
r("R6","10k","FRONT_PGTH",G)
c("C1","100n 25V","5V_FUSED")
add("D4","Diode","SMBJ6.0CA bidirectional","5V_FUSED GND","SMBJ6.0CA",fp="Diode_SMD:D_SMB")
c("C2","4.7n","FRONT_DVDT")
c("C3","10n","FRONT_TIMER")
c("C4","22u 16V",F,fp=C1206)
c("C5","100u 10V",F,fp="Capacitor_SMD:CP_Elec_6.3x5.8")
add("U2","Buck","TPS62162DSGR","GND 5V_PROT 5V_PROT GND GND 3V3 LV_SW BUCK_PG GND","TPS62162DSGR")
l("L1","2.2uH","LV_SW",V,"SRN4018-2R2M","Inductor_SMD:L_Bourns-SRN4018")
c("C6","10u 16V",F,fp=C0805)
c("C7","22u 10V",V,fp=C1206)
c("C8","22u 10V",V,fp=C1206)
r("R7","10k",V,"BUCK_PG")
tp("TP1","BUCK_PG")
for ref, net in (("#FLG01",G),("#FLG02","5V_FUSED"),("#FLG03",V)):
    add(ref,"Flag","PWR_FLAG",[net])

sheet = "ESP32"
esp = {1:G, 2:V, 3:"MCU_EN",4:"SR_SER",5:"SR_CLK",6:"SR_LATCH",
       7:"DIGITS_REQ",8:"OLED_REQ",9:"FAULT_N",10:"MCU_SDA",11:"MCU_SCL",
       12:"ARMED",15:"STRAP3",16:"STRAP46",17:"WDI",26:"STRAP45",27:"BOOT_N",
       36:"UART_RX",37:"UART_TX",40:G,41:G}
add("U3","ESP32","ESP32-S3-WROOM-1-N8",[esp.get(n,"-") for n in range(1,42)],"ESP32-S3-WROOM-1-N8")
c("C9","100n",V)
c("C10","10u 10V",V,fp=C0805)
r("R8","10k",V,"MCU_EN")
c("C11","1u","MCU_EN")
add("U4","Supervisor","TPS3808G33DBVR","MCU_EN GND RST_REQ_N - 3V3 3V3","TPS3808G33DBVR")
r("R9","10k",V,"RST_REQ_N")
c("C12","100n",V)
r("R10","10k",V,"BOOT_N")
for idx, strap in enumerate(("STRAP3","STRAP45","STRAP46"),11):
    r(f"R{idx}","10k",strap,G)
add("SW1","Switch","Hidden recovery GPIO0","BOOT_N GND","TL3342F160QG")
r("R14","1k","UART_RX_BUF","UART_HDR_TX")
add("U24","UARTBuffer","SN74LVC1G125DBVR","GND UART_RX_BUF GND UART_RX 3V3","SN74LVC1G125DBVR")
r("R54","47k",V,"UART_RX_BUF")
c("C50","100n",V)
r("R15","330R","UART_TX","UART_HDR_RX")
add("J2","UART4","3V3 UART ROM service / no power","GND UART_HDR_TX UART_HDR_RX RST_REQ_N")
r("R16","47k","DIGITS_REQ",G)
r("R17","47k","OLED_REQ",G)
for idx, net in enumerate(("SR_SER","SR_CLK","SR_LATCH","DIGITS_REQ","MCU_EN"),2):
    tp(f"TP{idx}",net)

sheet = "OLED"
add("U5","LoadSwitch","TPS22918DBVR","3V3 GND OLED_ON OLED_CT OLED_QOD OLED_3V3","TPS22918DBVR")
add("U6","I2C","TCA9517ADGKR","OLED_3V3 OLED_SCL OLED_SDA GND OLED_ON MCU_SDA MCU_SCL 3V3","TCA9517ADGKR")
add("U7","AND","SN74LVC1G08DBVR","OLED_REQ MCU_EN GND OLED_ON 3V3","SN74LVC1G08DBVR")
r("R18","100R","OLED_QOD","OLED_3V3")
c("C13","1n","OLED_CT")
c("C14","100n",V)
c("C15","1u","OLED_3V3")
c("C16","100n","OLED_3V3")
c("C17","100n",V)
for idx, (v,n) in enumerate(((V,"MCU_SDA"),(V,"MCU_SCL"),("OLED_3V3","OLED_SDA"),("OLED_3V3","OLED_SCL")),19):
    r(f"R{idx}","4.7k",v,n,status="HOLD_DNP" if idx>20 else None)
add("D1","TVS2","TPD2E2U06DCKR","OLED_SDA OLED_SCL GND","TPD2E2U06DCKR")
add("J3","OLED4","0.91 inch OLED harness TBD","GND OLED_3V3 OLED_SCL OLED_SDA")

sheet = "Hardware_inhibit"
add("U8","FF","SN74LVC1G74DCUR","ARM_STROBE RESIDUAL_OK - GND ARMED LATCH_CLR_N 3V3 3V3","SN74LVC1G74DCUR")
add("J4","Header2","Service ARM contacts momentary","3V3 ARM_STROBE")
r("R23","47k","ARM_STROBE",G)
add("U9","AND","SN74LVC1G08DBVR","MCU_EN FAULT_N GND LATCH_CLR_N 3V3","SN74LVC1G08DBVR")
add("U10","AND","SN74LVC1G08DBVR","DRIVE_OK DIGITS_REQ GND OE_SINK 3V3","SN74LVC1G08DBVR")
add("Q31","MOS","2N7002BK","OE_SINK GND HC_OE_N","2N7002BK,215")
r("R24","10k",V,"HC_OE_N")
r("R25","100k","OE_SINK",G)
r("R26","47k","ARMED",G)
r("R27","10k",V,"FAULT_N")
r("R28","10k",V,"RESIDUAL_OK")
r("R30","0R","MCU_EN","HC_CLEAR_N")
add("U19","AND","SN74LVC1G08DBVR","PWM_PERMIT HV_READY GND DRIVE_OK 3V3","SN74LVC1G08DBVR")
c("C49","100n",V)
add("U25","Watchdog","TPS3430WDRCR","3V3 - 3V3 - GND 3V3 WDI FAULT_N - 3V3 GND","TPS3430WDRCR")
r("R55","47k","WDI",G)
c("C51","100n",V)
for idx in range(18,21):
    c(f"C{idx}","100n",V)
tp("TP7","HC_OE_N")
tp("TP8","FAULT_N")
tp("TP9","ARMED")

sheet = "Shift_registers"
for idx,(raw,damped) in enumerate((("SR_SER","SER0"),("SR_CLK","SR_CLK_BUS"),
                                   ("SR_LATCH","SR_LATCH_BUS")),31):
    r(f"R{idx}","33R",raw,damped)
    r(f"R{idx+3}","47k",damped,G)
for bank in range(4):
    q = [f"DRV_{n:02}" if n<30 else "-" for n in range(bank*8,bank*8+8)]
    add(f"U{20+bank}","HC595","SN74HC595PWR",
        q[1:] + [G,f"SER{bank+1}" if bank<3 else "-","HC_CLEAR_N","SR_CLK_BUS",
                "SR_LATCH_BUS","HC_OE_N",f"SER{bank}",q[0],V],"SN74HC595PWR")
    c(f"C{21+bank}","100n",V)

mapping = []
for row in csv.DictReader((R8 / "30_CHANNEL_PIN_MAPPING.csv").open(encoding="utf-8")):
    bit = int(row["frame_bit"])
    shift = f"U{20+bit//8}"
    output = f"DRV_{bit:02}"
    if bit >= 30:
        mapping.append([bit,31-bit,shift,row["register_pin"],"NC","","","","","GUARD_ZERO"])
        continue
    tube, digit = divmod(bit,10)
    sheet = f"Cathodes_{tube+1}"
    base = f"BASE_{bit:02}"
    qref = f"Q{bit+1}"
    cnet = row["cathode_net"]
    add(qref,"NPN","Jingdao MMBTA42"," ".join([base,G,cnet]),"MMBTA42 / C4749118")
    r(f"R{100+bit}","3.0k 1%",output,base,"RC0603FR-073KL")
    r(f"R{200+bit}","10k 1%",base,G,"RC0603FR-0710KL")
    mapping.append([bit,31-bit,shift,row["register_pin"],output,f"{qref}.1/.2/.3",
                    base,cnet,f"V{tube+1}.{row['R7_socket_pin']}","BASELINE_NUMBERING_SOCKET_TBD"])

sheet = "Tube_interfaces"
for tube in range(1,4):
    cathodes = [None]*13
    cathodes[0] = f"ANODE_{tube}"
    for digit, pin in enumerate((3,13,12,11,10,9,7,6,5,4)):
        cathodes[pin-1] = f"K{tube}_{digit}"
    add(f"V{tube}","Socket","QS30-1 / socket geometry TBD",[n or "-" for n in cathodes],
        "QS30-1 / used socket TBD",status="SOCKET_GEOMETRY_TBD")
    r(f"R{300+tube*2}","10k 1% HV 1W","HV_BUS",f"ALIM_{tube}","CRCW251210K0FKEG",R2512)
    r(f"R{301+tube*2}","10k 1% HV 1W",f"ALIM_{tube}",f"ANODE_{tube}","CRCW251210K0FKEG",R2512)

sheet = "HV_cutoff"
hold = True
add("R40","R","DNP power-link open","5V_PROT HV_ISOLATE_IN",fp="Resistor_SMD:R_1206_3216Metric")
add("#FLG04","Flag","PWR_FLAG",["HV_ISOLATE_IN"])
add("U11","eFuse","TPS259474LRPWR","ARMED CUT_OVLO - CUT_PGTH HV_ISOLATE_IN 5V_HV CUT_DVDT GND CUT_ILM CUT_TIMER","TPS259474LRPWR")
r("R41","36.5k","HV_ISOLATE_IN","CUT_OVLO")
r("R42","10k","CUT_OVLO",G)
r("R43","2.00k","CUT_ILM",G)
r("R44","10k","CUT_PGTH",G)
c("C25","4.7n","CUT_DVDT")
c("C26","10n","CUT_TIMER")
c("C27","100n 25V","HV_ISOLATE_IN")
c("C28","22u 16V","5V_HV",fp=C1206)
r("R45","10k","5V_HV",G)

sheet = "Analog_protection"
# Keep the low-voltage reference, latch inputs and comparators installed for LV review.
hold = False
add("U12","Reference","REF3312AIDBZR","3V3 REF_1V25 GND","REF3312AIDBZR")
c("C29","100n",V)
c("C30","100n","REF_1V25")
add("U13","Compare","TLV1702DGKR","FAULT_N HV_OVP_S REF_1V25 GND OCP_REF CS_FILT FAULT_N 3V3","TLV1702DGKR")
add("U14","Compare","TLV1702DGKR","RESIDUAL_OK HV_RES_S REF_1V25 GND BIAS_S REF_1V25 BIAS_OK 3V3","TLV1702DGKR")
add("U15","AND","SN74LVC1G08DBVR","ARMED BIAS_OK GND PWM_PERMIT 3V3","SN74LVC1G08DBVR")
r("R46","10k",V,"BIAS_OK")
r("R47","93.1k","REF_1V25","OCP_REF")
r("R48","10k","OCP_REF",G)
r("R49","470R","HV_ISENSE","CS_FILT")
c("C31","100p","CS_FILT")
r("R50","64.9k","GATE_BIAS","BIAS_S")
r("R51","10k","BIAS_S",G)
r("R52","47k","PWM_PERMIT",G)
r("R53","10k",V,"HV_READY")
c("C32","100n",V)
c("C33","100n",V)
c("C34","100n",V)
for idx,(net,total,low) in enumerate((("HV_OVP_S","499k","13.3k"),("HV_RES_S","453k","42.2k"))):
    last = "HV_BUS"
    for stage in range(4):
        next_net = net if stage==3 else f"{net}_{stage+1}"
        r(f"R{60+idx*5+stage}",total+" 1% HV",last,next_net,fp=R2512,status="HOLD_DNP")
        last = next_net
    r(f"R{64+idx*5}",low+" 1%",net,G)
c("C35","100p","HV_OVP_S")
c("C36","100p","HV_RES_S")

sheet = "Gate_bias"
hold = True
add("U16","BoostBias","TPS61040DBVR","BIAS_SW GND BIAS_FB 5V_HV 5V_HV","TPS61040DBVR")
l("L2","10uH","5V_HV","BIAS_SW","SRN4018-100M","Inductor_SMD:L_Bourns-SRN4018")
add("D2","Diode","SS14","GATE_BIAS BIAS_SW","SS14",fp="Diode_SMD:D_SMA")
add("#FLG05","Flag","PWR_FLAG",["GATE_BIAS"])
r("R70","845k","GATE_BIAS","BIAS_FB")
r("R71","100k","BIAS_FB",G)
c("C37","4.7u 16V","5V_HV",fp=C0805)
c("C38","4.7u 25V","GATE_BIAS",fp=C1206)
c("C39","100n","GATE_BIAS")

sheet = "HV_boost"
add("U17","BoostHV","LM5155DSSR","5V_HV HV_VCC PWM_RAW GND HV_CS HV_COMP GND HV_FB HV_SS HV_RT HV_READY HV_UVLO GND","LM5155DSSR")
add("U18","GateDriver","UCC27511DBVR","GATE_BIAS GATE_SRC GATE_SNK GND GND PWM_RAW","UCC27511DBVR")
add("Q32","PowerMOS","STD13N60M2","GATE_HV SW_HV HV_ISENSE","STD13N60M2")
add("D3","Diode","ES1G-13-F","HV_BUS SW_HV","ES1G-13-F",fp="Diode_SMD:D_SMA")
l("L3","22uH","5V_HV","SW_HV","MSS1278-223MLD","Inductor_SMD:L_Coilcraft_MSS1278-XXX")
r("R72","100R","HV_ISENSE","HV_CS")
r("R73","50mR Kelvin candidate","HV_ISENSE",G,"WSL2512R0500FEA",R2512)
r("R74","10R","GATE_SRC","GATE_HV")
r("R75","4.7R","GATE_SNK","GATE_HV")
r("R76","10k","GATE_HV","HV_ISENSE")
r("R77","10k","PWM_PERMIT","HV_UVLO")
r("R78","47k","HV_UVLO",G)
r("R79","220k RT candidate","HV_RT",G)
r("R80","10k COMP candidate","HV_COMP","COMP_Z")
c("C40","2.2u 16V","HV_VCC",fp=C0805)
c("C41","100n","HV_SS")
c("C42","100p","HV_CS")
c("C43","10n COMP candidate","COMP_Z")
c("C44","100p COMP candidate","HV_COMP")
c("C45","1u 25V","GATE_BIAS",fp=C0805)
c("C46","100n 16V","5V_HV")
c("C47","3.3u 450V 10%","HV_BUS",fp="R10_R10:TDK_B32774M4335K000",mpn="B32774M4335K000")
last = "HV_BUS"
for stage in range(4):
    nxt = "HV_FB" if stage==3 else f"HV_FB_{stage+1}"
    r(f"R{81+stage}","422k 0.1% HV",last,nxt,fp=R2512)
    last = nxt
r("R85","10k 0.1%","HV_FB",G)
r("R86","100R snubber TBD","SW_HV","SNUB",fp=R2512)
c("C48","100p 630V snubber TBD","SNUB",fp=C1206)

sheet = "HV_bleeders"
hold = False
for branch in range(2):
    last = "HV_BUS"
    for stage in range(4):
        nxt = G if stage==3 else f"BLEED_{branch+1}_{stage+1}"
        r(f"R{400+branch*4+stage}","124k 1% HV",last,nxt,fp=R2512)
        last = nxt

gpio = [
    ("4",4,"SR_SER","OUT","47k after 33R, normally low"),
    ("5",5,"SR_CLK","OUT","47k after 33R, normally low"),
    ("6",6,"SR_LATCH","OUT","47k after 33R, normally low"),
    ("7",7,"DIGITS_REQ","OUT","47k low, hardware AND with ARMED"),
    ("15",8,"OLED_REQ","OUT","47k low, hardware AND with MCU_EN"),
    ("16",9,"FAULT_N","IN","Active low hardware fault, open drain"),
    ("17",10,"MCU_SDA","OD","4.7k pull-up on MCU side"),
    ("18",11,"MCU_SCL","OD","4.7k pull-up on MCU side"),
    ("8",12,"ARMED","IN","Hardware latch state"),
    ("9",17,"WDI","OUT","Watchdog candidate falling edge every 1.1 s, no hardware PWM"),
    ("3",15,"STRAP3","STRAP","10k low, ROM JTAG policy verify"),
    ("46",16,"STRAP46","STRAP","10k low for UART download with GPIO0 low"),
    ("45",26,"STRAP45","STRAP","10k low for default flash supply"),
    ("0",27,"BOOT_N","STRAP","10k high, hold SW1 while asserting J2 EN"),
    ("44",36,"UART_RX","IN","Use 3.3V UART only, no adapter power pin"),
    ("43",37,"UART_TX","OUT","ROM serial recovery"),
    ("EN",3,"MCU_EN","RESET","TPS3808 supervisor, pull-up and C11"),
]
