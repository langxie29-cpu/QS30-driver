"""Write the native 5 V Type-C ECO using the preserved R10 symbol generator."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"r10"))
import build_schematic as sch
import circuit as ck

G = "GND"
VBUS = "5V_RAW"
SHEET = "Input_and_3V3"
PROJECT = "NXT-M3-R11"
LIB = sch.LIB
ST = "https://www.st.com/resource/en/datasheet/stusb4500l.pdf"
GCT = "https://gct.co/files/drawings/usb4125.pdf"
USB_FP = "Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal"
ST_FP = "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm"


def define():
    ck.sheet, ck.hold = SHEET, False
    ck.kinds["TypeC6"] = ({pin: (name, "passive") for pin,name in (
        ("A9","VBUS"),("B9","VBUS"),("A12","GND"),("B12","GND"),
        ("A5","CC1"),("B5","CC2"),("SH","SHIELD"))}, USB_FP,GCT)
    ck.kind("TypeCSink5V",
            "CC1DB:b CC1:b NU:p CC2:b CC2DB:b RESET:i SCL:i SDA:b DISCH:b GND:v ATTACH:d "
            "ADDR0:i ADDR1:i RP_1A5:d GPIO:d VBUS_EN_SNK:d A_B_SIDE:d VBUS_VS_DISCH:p ALERT:d "
            "RP_3A:d VREG_1V2:w VSYS:v VREG_2V7:w VDD:v EP:p",ST_FP,ST)
    ck.kind("CC_ESD","CC1:p CC2:p GND:p",ck.SOT,"https://www.st.com/resource/en/datasheet/esdal.pdf")
    ck.parts[:] = [item for item in ck.parts if item["ref"]!="J1"]
    ck.add("J1","TypeC6","USB-C 5 V power only","5V_RAW 5V_RAW GND GND USBC_CC1 USBC_CC2 GND","USB4125-GF-A")
    ck.add("U26","TypeCSink5V","STUSB4500L 5 V sink",
           "USBC_CC1 USBC_CC1 GND USBC_CC2 USBC_CC2 GND - - - GND - GND GND - - "
           "USBC_VALID_N - USBC_VS - USBC_3A_N USBC_1V2 GND USBC_2V7 5V_RAW GND","STUSB4500LQTR")
    ck.add("D5","CC_ESD","ESDA25L","USBC_CC1 USBC_CC2 GND","ESDA25L")
    ck.r("R230","100k",VBUS,"USBC_VALID_N")
    ck.r("R231","180k","USBC_VALID_N",G)
    ck.r("R232","100k",VBUS,"USBC_3A_N")
    ck.r("R233","180k","USBC_3A_N",G)
    ck.r("R234","1k",VBUS,"USBC_VS")
    ck.c("C52","1u 16V",VBUS)
    ck.c("C53","1u 10V","USBC_1V2")
    ck.c("C54","1u 10V","USBC_2V7")
    for ref, flag in (("Q33","USBC_VALID_N"),("Q34","USBC_3A_N")):
        ck.add(ref,"MOS","2N7002BK / EN clamp",[flag,G,"FRONT_EN"],"2N7002BK,215")
    ck.add("#FLG06","Flag","PWR_FLAG",[VBUS])
    return {p["ref"]:p for p in ck.parts if p["sheet"]==SHEET}


def write():
    sch.PROJECT = PROJECT
    parts = define()
    original = (HERE.parent/"r10/eda"/f"{SHEET}.kicad_sch").read_text(encoding="utf-8").splitlines()
    path = HERE/"eda"/f"{SHEET}.kicad_sch"
    contents = [line.replace("NXT-M3-R10", PROJECT).replace("R10 engineering HOLD","R11 engineering HOLD")
                for line in original[:-1]]
    start = next(i for i,line in enumerate(contents) if line.startswith('(symbol (lib_id "R10_R10:Header2")'))
    end = next(i for i,line in enumerate(contents) if line.startswith('(symbol (lib_id "R10_R10:Fuse")'))
    del contents[start:end]
    kinds = sorted({p["kind"] for p in parts.values()})
    contents[2] = "(lib_symbols " + " ".join(sch.symbol(name, True)[0] for name in kinds) + ")"
    positions = {
        "J1":(48.26,52.07),"U26":(92.71,252.73),"D5":(188,245),
        "R230":(239,229),"R231":(239,251),"R232":(239,273),"R233":(314,273),
        "R234":(314,229),"C52":(314,251),"C53":(388,229),"C54":(388,251),
        "Q33":(188,272),"Q34":(330,193),"#FLG06":(388,273),
    }
    ids = sch.uid("sheet-"+SHEET)
    contents.extend([sch.note("5 V Type-C sink. Source attach and 3 A Rp hardware permission required for U1.",16,219)])
    for ref,(x,y) in positions.items():
        contents.extend(sch.place(parts[ref],x,y,ids))
    sch.write(path,[*contents,")"])
    lib = HERE/"eda"/f"{LIB}.kicad_sym"
    base = (HERE.parent/"r10/eda"/lib.name).read_text(encoding="utf-8").splitlines()
    extra = [sch.symbol(kind)[0] for kind in ("TypeC6","TypeCSink5V","CC_ESD")]
    sch.write(lib, [*base[:-1],*extra,")"])


if __name__ == "__main__":
    write()
