# -*- coding: utf-8 -*-
"""QS30-6 REV.A design model: part database + netlist primitives.

All pin-numbers below were taken from the ORIGINAL manufacturer datasheets
(see source_register.md). The PIN_DB is the single point of truth used by the
netlist generators and by the ERC/consistency checks.
"""
from collections import OrderedDict


class Part:
    __slots__ = ("ref", "mpn", "val", "pkg", "status", "source", "desc",
                 "sheet", "pins", "nets", "flags", "note", "hw_lib")

    def __init__(self, ref, mpn, val, pkg, status, source, desc, sheet,
                 pins, nets=None, flags=(), note="", hw_lib=""):
        self.ref = ref
        self.mpn = mpn
        self.val = val
        self.pkg = pkg
        self.status = status          # VERIFIED / STRONGLY SUPPORTED / PROVISIONAL / HOLD
        self.source = source          # source-register ids
        self.desc = desc
        self.sheet = sheet
        self.pins = OrderedDict(pins)  # pin number -> pin name (from datasheet)
        self.nets = nets or {}         # pin number -> net name (filled by conn())
        self.flags = set(flags)        # DNP / NC_ALLOWED / TESTPOINT ...
        self.note = note
        self.hw_lib = hw_lib

    def connect(self, pin, net):
        pin = str(pin)
        if pin not in self.pins:
            raise KeyError(f"{self.ref}: pin {pin} not in datasheet pin map "
                           f"{list(self.pins)} (mpn={self.mpn})")
        if pin in self.nets and self.nets[pin] != net:
            raise ValueError(f"{self.ref} pin {pin} assigned twice: "
                             f"{self.nets[pin]} vs {net}")
        self.nets[pin] = net

    def rows(self):
        for pin, name in self.pins.items():
            yield pin, name, self.nets.get(pin, "")


# ---------------------------------------------------------------------------
# verified pin databases (datasheet pin-out, no guessing)
# ---------------------------------------------------------------------------
PIN_DB = {
    # Espressif ESP32-S3-WROOM-1 / -1U datasheet table 3-1 (41 pads incl. thermal)
    "ESP32-S3-WROOM-1": {
        "1": "GND", "2": "3V3", "3": "EN", "4": "IO4", "5": "IO5", "6": "IO6",
        "7": "IO7", "8": "IO15", "9": "IO16", "10": "IO17", "11": "IO18",
        "12": "IO8", "13": "IO19", "14": "IO20", "15": "IO3", "16": "IO46",
        "17": "IO9", "18": "IO10", "19": "IO11", "20": "IO12", "21": "IO13",
        "22": "IO14", "23": "IO21", "24": "IO47", "25": "IO48", "26": "IO45",
        "27": "IO0", "28": "IO35", "29": "IO36", "30": "IO37", "31": "IO38",
        "32": "IO39", "33": "IO40", "34": "IO41", "35": "IO42", "36": "IO44/RXD0",
        "37": "IO43/TXD0", "38": "IO2", "39": "IO1", "40": "GND", "41": "GND/EP",
    },
    # Microchip HV5622 DS20005854A Table 2-1 (44-lead PQFP)
    "HV5622-PQFP44": {
        "1": "HVOUT22", "2": "HVOUT21", "3": "HVOUT20", "4": "HVOUT19",
        "5": "HVOUT18", "6": "HVOUT17", "7": "HVOUT16", "8": "HVOUT15",
        "9": "HVOUT14", "10": "HVOUT13", "11": "HVOUT12", "12": "HVOUT11",
        "13": "HVOUT10", "14": "HVOUT9", "15": "HVOUT8", "16": "HVOUT7",
        "17": "HVOUT6", "18": "HVOUT5", "19": "HVOUT4", "20": "HVOUT3",
        "21": "HVOUT2", "22": "HVOUT1", "23": "DATA OUT", "24": "NC",
        "25": "NC", "26": "NC", "27": "POL", "28": "CLK", "29": "VSS",
        "30": "VDD", "31": "LE", "32": "DATA IN", "33": "BL", "34": "NC",
        "35": "HVOUT32", "36": "HVOUT31", "37": "HVOUT30", "38": "HVOUT29",
        "39": "HVOUT28", "40": "HVOUT27", "41": "HVOUT26", "42": "HVOUT25",
        "43": "HVOUT24", "44": "HVOUT23",
    },
    # TI TPS54202 SOT-23-6 (DDC), datasheet section 4 pin functions
    "TPS54202": {"1": "GND", "2": "SW", "3": "VIN", "4": "FB", "5": "EN",
                 "6": "BOOT"},
    # Silergy SY8089A SOT-23-5, datasheet pin description
    "SY8089A": {"1": "EN", "2": "GND", "3": "LX", "4": "IN", "5": "FB"},
    # TI/Harris CD40109B, 16-lead (Fig.1 logic diagram note + VCC/VDD/VSS)
    "CD40109B": {
        "1": "VCC", "2": "ENABLE A", "3": "A", "4": "E", "5": "F",
        "6": "B", "7": "ENABLE B", "8": "VSS", "9": "ENABLE C", "10": "C",
        "11": "G", "12": "NC", "13": "H", "14": "D", "15": "ENABLE D",
        "16": "VDD",
    },
    # ST/UMW USBLC6-2SC6 SOT-23-6
    "USBLC6-2SC6": {"1": "I/O1", "2": "GND", "3": "I/O2", "4": "I/O2",
                    "5": "VBUS", "6": "I/O1"},
    # TI LM393 SOIC-8
    "LM393": {"1": "OUT1", "2": "IN1-", "3": "IN1+", "4": "GND",
              "5": "IN2+", "6": "IN2-", "7": "OUT2", "8": "VCC"},
    # TI TL431, DBZ (SOT-23-3), datasheet SLVS543S Table 5-1:
    # 1 = CATHODE, 2 = REF, 3 = ANODE
    "TL431": {"1": "CATHODE", "2": "REF", "3": "ANODE"},
    # TI 74HC08 SOIC-14 (quad 2-input AND)
    "74HC08": {
        "1": "1A", "2": "1B", "3": "1Y", "4": "2A", "5": "2B", "6": "2Y",
        "7": "GND", "8": "3Y", "9": "3A", "10": "3B", "11": "4Y", "12": "4A",
        "13": "4B", "14": "VCC",
    },
    # ON Semi UC3843 current-mode controller, DIP-8 / SOIC-8
    "UC3843": {"1": "COMP", "2": "FB", "3": "CS", "4": "RT/CT", "5": "GND",
               "6": "OUT", "7": "VCC", "8": "VREF"},
    # QS30-1 13-pin tube, Nanchang factory datasheet (电极接线图)
    "QS30-1": {
        "1": "IC_KEEP_OPEN", "2": "A", "3": "K0", "4": "K9", "5": "K8",
        "6": "K7", "7": "K6", "8": "IC8_KEEP_OPEN", "9": "K5", "10": "K4",
        "11": "K3", "12": "K2", "13": "K1",
    },
    # 13-pin tube socket (J13-1A style) -- pin numbering mirrors the tube
    "SOCKET-13": {
        "1": "IC_KEEP_OPEN", "2": "A", "3": "K0", "4": "K9", "5": "K8",
        "6": "K7", "7": "K6", "8": "IC8_KEEP_OPEN", "9": "K5", "10": "K4",
        "11": "K3", "12": "K2", "13": "K1",
    },
    # USB-C 16-pin USB2.0-only receptacle, pads named per USB-IF receptacle
    "USBC-16P": {
        "A1": "GND", "A4": "VBUS", "A5": "CC1", "A6": "D+", "A7": "D-",
        "A8": "SBU1", "A9": "VBUS", "A12": "GND", "B1": "GND", "B4": "VBUS",
        "B5": "CC2", "B6": "D+", "B7": "D-", "B8": "SBU2", "B9": "VBUS",
        "B12": "GND", "S1": "SHIELD", "S2": "SHIELD", "S3": "SHIELD",
        "S4": "SHIELD",
    },
    # two-pin passives / discretes
    "R": {"1": "1", "2": "2"},
    "C": {"1": "1", "2": "2"},
    "L": {"1": "1", "2": "2"},
    "D": {"1": "K", "2": "A"},            # diode: pin1 cathode, pin2 anode
    "LED": {"1": "K", "2": "A"},
    "ZENER": {"1": "K", "2": "A"},
    "BAT54S": {"1": "A1", "2": "K2", "3": "C"},   # dual series, C = common
    "SW": {"1": "1", "2": "2"},
    "SW_PUSH": {"1": "1", "2": "2"},
    "TP": {"1": "1"},
    "FUSE": {"1": "1", "2": "2"},
    "TVS": {"1": "K", "2": "A"},
    "P-FET": {"1": "G", "2": "S", "3": "D"},
    "N-FET": {"1": "G", "2": "S", "3": "D"},
    # IRF740 / TO-220: 1 = Gate, 2 = Drain, 3 = Source
    "N-FET-TO220": {"1": "G", "2": "D", "3": "S"},
    "NPN": {"1": "B", "2": "E", "3": "C"},
    "PNP": {"1": "B", "2": "E", "3": "C"},
    "HDR-6": {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6"},
    "HDR-2": {"1": "1", "2": "2"},
    "HDR-6P": {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6"},
}

# The QS30-1 symbol pin numbers equal physical pin numbers (symbol must NOT be
# renumbered).  Socket pad numbers equal tube pin numbers, 1:1, no re-ordering.

# ---------------------------------------------------------------------------
# net classes (LCEDA "网络类别"): every net carries exactly one class
# ---------------------------------------------------------------------------
NET_CLASS = {}          # net -> class, filled by add_net()

CLASS_RULES = {
    "HV":      dict(clearance_mm="1.0 (TBD by H07)", trace_mm="0.5 min, HV 回路尽量短",
                    note="170 V 高压：HV_BUS / 阳极 / 阴极"),
    "DRV":     dict(clearance_mm="0.25", trace_mm="0.2", note="DRV_VDD=12 V 逻辑域"),
    "POWER":   dict(clearance_mm="0.25", trace_mm="0.5/1.0", note="12 V/5 V/3.3 V 电源"),
    "DIFF":    dict(clearance_mm="0.2", trace_mm="0.15/90 Ω 差分", note="USB D+/D-"),
    "SIGNAL":  dict(clearance_mm="0.2", trace_mm="0.2", note="低压信号"),
    "GND":     dict(clearance_mm="0.25", trace_mm="—", note="地"),
}

DESIGN = OrderedDict()   # ref -> Part
NETS = {}                # net -> list of (ref, pin)


ALIAS = {
    "HV5622PJ": "HV5622-PQFP44",
    "HV5622": "HV5622-PQFP44",
    "CD40109BE": "CD40109B",
}


def resolve_pin_key(ref, mpn, pin_key):
    key = pin_key or mpn
    if key in PIN_DB:
        return key
    if key in ALIAS:
        return ALIAS[key]
    cands = [k for k in PIN_DB if len(k) >= 4 and mpn.startswith(k)]
    if len(cands) == 1:
        return cands[0]
    raise KeyError(f"no verified pin DB for {ref} ({mpn})")


def add(ref, mpn, val, pkg, status, source, desc, sheet,
        flags=(), note="", hw_lib="", pin_key=None):
    if ref in DESIGN:
        raise ValueError(f"duplicate ref {ref}")
    key = resolve_pin_key(ref, mpn, pin_key)
    p = Part(ref, mpn, val, pkg, status, source, desc, sheet,
             PIN_DB[key], flags=flags, note=note, hw_lib=hw_lib)
    DESIGN[ref] = p
    return p


def conn(ref, pin, net):
    p = DESIGN[ref]
    p.connect(pin, net)
    NETS.setdefault(net, []).append((ref, str(pin)))


def nc(ref, *pins):
    for pin in pins:
        p = DESIGN[ref]
        pin = str(pin)
        if pin not in p.pins:
            raise KeyError(f"{ref}: no pin {pin}")
        if pin in p.nets:
            raise ValueError(f"{ref} pin {pin} already connected")
        p.nets[pin] = "NC"      # explicit no-connect


def net_class(net, cls):
    if net in NET_CLASS and NET_CLASS[net] != cls:
        raise ValueError(f"net {net} class conflict {NET_CLASS[net]} vs {cls}")
    NET_CLASS[net] = cls


HV_NETS = {
    # 真正可能出现高压的节点（按 HV 网络类别布线）
    "HV_BUS", "SW_HV", "CLAMP_N", "CS_N", "COMP_N", "FB_HV", "FB_MID",
    "OVP_MID", "OVP_SNS", "HVS_MID", "HVS_NODE", "BLEED_MID", "VREF_OVP",
    "OVP_LATCH", "OVP_SET", "LATCH_B",
}
# HV_ 前缀但并非高压的网络（3.3 V 逻辑 / 12 V 信号 / 12 V 电源）
HV_PREFIX_NOT_HV = {
    "HV_EN_REQ": "SIGNAL", "HV_EN": "SIGNAL", "HV_EN_G": "SIGNAL",
    "HV_FAULT_OD": "SIGNAL", "HV_SENSE_ADC": "SIGNAL", "HVF_NODE": "SIGNAL",
    "HV_IN": "POWER",
}


def class_by_prefix():
    for n in NETS:
        if n in NET_CLASS:
            continue
        if n in HV_PREFIX_NOT_HV:
            net_class(n, HV_PREFIX_NOT_HV[n])
        elif n in ("GND",):
            net_class(n, "GND")
        elif n in HV_NETS or n.startswith("HV_") or n.startswith("K_") \
                or n.startswith("A_T") or n.startswith("A_MID"):
            net_class(n, "HV")
        elif n in ("DRV_VDD_EN", "DRV_PG", "DRV_OK", "DRV_SNS"):
            net_class(n, "SIGNAL")          # 3.3 V 侧逻辑/检测节点
        elif n.startswith("DRV_"):
            net_class(n, "DRV")             # 12 V 驱动域
        elif n in ("EXT12_RAW", "EXT12_F", "EXT12", "EXT5", "VBUS", "5V_SYS",
                   "3V3", "DRV_VDD", "HV_IN"):
            net_class(n, "POWER")
        elif n in ("USB_DP_CON", "USB_DM_CON", "USB_DP_MCU", "USB_DM_MCU"):
            net_class(n, "DIFF")
        else:
            net_class(n, "SIGNAL")
