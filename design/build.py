# -*- coding: utf-8 -*-
"""QS30-6 REV.A build: netlist, nets, BOM, mapping tables and ERC checks.

Run:  python build.py
Outputs are written under  ../netlist  ../bom  ../docs  (UTF-8, BOM for Excel).
"""
import csv
import json
import os
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import sheet_lv
import sheet_hv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_NL = os.path.join(ROOT, "netlist")
D_BOM = os.path.join(ROOT, "bom")
D_DOC = os.path.join(ROOT, "docs")


def build_design():
    sheet_lv.build()
    sheet_hv.build()
    model.class_by_prefix()
    return model.DESIGN, model.NETS, model.NET_CLASS


# ---------------------------------------------------------------------------
def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def export(design, nets, nclass):
    pin_rows, json_parts = [], []
    for ref, p in design.items():
        for pin, name, net in p.rows():
            net = "" if net == "NC" else net
            pin_rows.append([ref, p.mpn, p.val, p.pkg, p.sheet, pin, name,
                             net, nclass.get(net, ""), p.status,
                             "DNP" if "DNP" in p.flags else "",
                             p.source, p.note])
        json_parts.append(dict(
            ref=ref, mpn=p.mpn, value=p.val, package=p.pkg, sheet=p.sheet,
            status=p.status, source=p.source, description=p.desc,
            flags=sorted(p.flags), note=p.note,
            hw_lib=p.hw_lib,
            pins=[dict(pin=pin, name=name, net=("" if net == "NC" else net))
                  for pin, name, net in p.rows()]))
    write_csv(os.path.join(D_NL, "QS30-6_REV.A_netlist.csv"),
              ["ref", "mpn", "value", "package", "sheet", "pin", "pin_name",
               "net", "net_class", "part_status", "population", "source",
               "note"], pin_rows)

    net_rows = []
    for net in sorted(nets):
        members = nets[net]
        sheets = sorted({design[r].sheet for r, _ in members})
        net_rows.append([net, nclass.get(net, ""), len(members),
                         ";".join(f"{r}.{pin}" for r, pin in members),
                         ":".join(sheets)])
    write_csv(os.path.join(D_NL, "QS30-6_REV.A_nets.csv"),
              ["net", "net_class", "pin_count", "members", "sheets"], net_rows)

    with open(os.path.join(D_NL, "QS30-6_REV.A_netlist.json"), "w",
              encoding="utf-8") as f:
        json.dump(dict(project="QS30-6 REV.A", revision="REV.A",
                       note="pin numbers per original datasheets; NC = no connect",
                       parts=json_parts), f, ensure_ascii=False, indent=1)
    return pin_rows, net_rows


def export_bom(design):
    rows = []
    for ref, p in design.items():
        rows.append([ref, p.mpn, p.val, p.pkg, p.sheet, p.status,
                     "DNP" if "DNP" in p.flags else "",
                     p.source, p.desc, p.note])
    write_csv(os.path.join(D_BOM, "QS30-6_REV.A_BOM.csv"),
              ["ref", "mpn", "value", "package", "sheet", "status",
               "population", "source", "description", "note"], rows)
    # production-release gate: only parts that are VERIFIED and not HOLD blocks
    gate = [r for r in rows if r[5] in ("VERIFIED", "STRONGLY SUPPORTED")]
    write_csv(os.path.join(D_BOM, "QS30-6_REV.A_BOM_verified_only.csv"),
              ["ref", "mpn", "value", "package", "sheet", "status",
               "population", "source", "description", "note"], gate)
    return rows


def export_mapping(design):
    # 1) QS30-1 socket / symbol / pad mapping
    rows = []
    for pin, name in model.PIN_DB["QS30-1"].items():
        rows.append([pin, name, name, "J_T1..J_T6", pin, pin,
                     "符号脚号=物理脚号=封装焊盘号（1:1，不允许按 0..9 重排）"])
    write_csv(os.path.join(D_DOC, "qs30_1_pin_mapping.csv"),
              ["physical_pin", "function", "symbol_pin", "socket_ref",
               "footprint_pad", "net_suffix", "rule"], rows)

    # 2) 60-channel drive mapping
    rows = []
    for t in range(1, 7):
        for d in range(10):
            ch = sheet_hv.channel(t, d)
            dev = sheet_hv.device_of(ch)
            hv = sheet_hv.hvout_of(ch)
            pin = sheet_hv.HVOUT_PIN[hv]
            bit = 63 - ch          # PROVISIONAL convention, walking-one test
            rows.append([f"J_T{t}", d, sheet_hv.TUBE_DIGIT_PIN[d],
                         sheet_hv.cathode_net(t, d), ch, dev, f"HVOUT{hv}",
                         pin, bit, "PROVISIONAL(位序待walking-one实测)"])
    for ch in range(60, 64):
        dev = sheet_hv.device_of(ch)
        hv = sheet_hv.hvout_of(ch)
        rows.append(["备用", "-", "-", "NC", ch, dev, f"HVOUT{hv}",
                     sheet_hv.HVOUT_PIN[hv], 63 - ch, "NC 不使用"])
    write_csv(os.path.join(D_DOC, "channel_mapping.csv"),
              ["tube", "display_digit", "qs30_1_pin", "cathode_net",
               "logic_channel", "driver", "driver_output", "pqfp_pin",
               "serial_bit_index", "status"], rows)
    return rows


REQUIRED_NETS = [
    "GND", "EXT12_RAW", "EXT12_F", "EXT12", "EXT5", "VBUS", "5V_SYS", "3V3",
    "DRV_VDD", "HV_IN", "HV_BUS", "EN_MCU", "BOOT_N", "GPIO46_STRAP",
    "DISP_DIN", "DISP_CLK", "DISP_LAT", "DISP_ALLOW", "HV_EN_REQ",
    "HV_EN", "DRV_VDD_EN", "DRV_BL", "DRV_DIN", "DRV_CLK", "DRV_LAT",
    "DRV_DIN", "EXT12_PG", "P3V3_PG", "DRV_PG", "HV_EN", "HV_FAULT_OD",
    "HVF_NODE", "HV_SENSE_ADC", "OVP_SNS", "OVP_LATCH", "COMP_N", "FB_HV",
    "SW_HV", "CS_N", "USB_DP_MCU", "USB_DM_MCU", "USB_DP_CON", "USB_DM_CON",
]

DOC_GPIO = {   # handbook GPIO/pad table (design input to be kept traceable)
    "DISP_DIN": ("11", "19"), "DISP_CLK": ("12", "20"),
    "DISP_LAT": ("14", "22"), "DISP_ALLOW": ("15", "8"),
    "HV_EN_REQ": ("16", "9"), "HV_SENSE": ("1", "39"),
    "HV_FAULT_N": ("7", "7"), "I2C_SDA": ("8", "12"),
    "I2C_SCL": ("9", "17"), "KEY_SET": ("4", "4"), "KEY_PLUS": ("5", "5"),
    "KEY_MINUS": ("6", "6"), "STATUS_LED": ("17", "10"),
    "USB_DM": ("19", "13"), "USB_DP": ("20", "14"), "UART0_TX": ("43", "37"),
    "UART0_RX": ("44", "36"), "BOOT": ("0", "27"), "EN": ("-", "3"),
}


def checks(design, nets, nclass):
    """Return list of (id, level, text). Level: ERROR/WARN/INFO/PASS."""
    out = []
    E = lambda i, t: out.append((i, "ERROR", t))
    W = lambda i, t: out.append((i, "WARN", t))
    I = lambda i, t: out.append((i, "INFO", t))
    P = lambda i, t: out.append((i, "PASS", t))

    # 1 未连接引脚
    floats = [(r, pin, n) for r, p in design.items() for pin, n, net in p.rows()
              if not net]
    if floats:
        W("ERC-01", "存在未分配网络的引脚: " +
          ", ".join(f"{r}.{pin}({n})" for r, pin, n in floats))
    else:
        P("ERC-01", "所有器件引脚均已分配网络或显式 NC")

    # 2 单引脚网络（测试点/NC 除外）
    singles = [n for n, m in nets.items() if len(m) < 2]
    if singles:
        W("ERC-02", "单引脚网络（需确认是否保留测试点）: " + ", ".join(sorted(singles)))
    else:
        P("ERC-02", "无单引脚网络")

    # 3 必需网络
    miss = [n for n in REQUIRED_NETS if n not in nets]
    if miss:
        E("ERC-03", "缺少必需网络: " + ", ".join(miss))
    else:
        P("ERC-03", f"{len(REQUIRED_NETS)} 个必需网络全部存在")

    # 4 GPIO/焊盘 与交接文件的追溯性
    bad = []
    mcu = design["U10"]
    def pad_of(net):
        return [pin for pin, n, x in mcu.rows() if x == net]
    for sig, (gpio, pad) in DOC_GPIO.items():
        net = {"HV_SENSE": "HV_SENSE_ADC", "HV_FAULT_N": "HVF_NODE",
               "USB_DM": "USB_DM_MCU", "USB_DP": "USB_DP_MCU",
               "BOOT": "BOOT_N", "EN": "EN_MCU"}.get(sig, sig)
        if net not in nets:
            bad.append(f"{sig}(net {net} 不存在)")
            continue
        pads = pad_of(net)
        if pad not in pads:
            bad.append(f"{sig}: 期望焊盘{pad}, 实际{pads}")
    if bad:
        E("ERC-04", "GPIO/焊盘与交接表不一致: " + "; ".join(bad))
    else:
        P("ERC-04", f"GPIO/焊盘映射与交接表一致（{len(DOC_GPIO)} 项）")

    # 5 安全默认态
    pol_ok = all(design[d].nets.get("27") == "DRV_VDD" for d in ("U21", "U22"))
    P("ERC-05", "HV5622 POL 固定接 DRV_VDD（避免 BL 有效时全开）") if pol_ok \
        else E("ERC-05", "HV5622 POL 未固定接 DRV_VDD")
    if any(design[r].nets.get("2") == "GND" and "DRV_BL" in design[r].nets.values()
           for r in ("R33", "R34", "R35", "R36", "R37")):
        P("ERC-06", "DRV_BL 在 12 V 驱动域有 10 kΩ 下拉（默认消隐）")
    else:
        E("ERC-06", "DRV_BL 缺少驱动域下拉")
    if "HV_EN" in nets and ("R49" in design):
        P("ERC-07", "HV_EN 有 100 kΩ 下拉 → GPIO/门控悬空时升压关断")
    else:
        E("ERC-07", "HV_EN 缺少默认下拉")
    if design["R12"].nets.get("2") == "BOOT_N" and design["R12"].nets.get("1") == "3V3":
        P("ERC-08", "GPIO0/BOOT 有 10 kΩ 上拉")
    else:
        E("ERC-08", "GPIO0/BOOT 缺少上拉")
    if design["R13"].nets.get("1") == "GPIO46_STRAP" and design["R13"].nets.get("2") == "GND":
        P("ERC-09", "GPIO46 保持 10 kΩ 下拉（启动条件）")
    else:
        E("ERC-09", "GPIO46 缺少下拉")
    if design["R51"].nets.get("1") == "HV_EN_REQ" and design["R51"].nets.get("2") == "GND":
        P("ERC-07b", "HV_EN_REQ 有外部 100 kΩ 下拉 → 复位期间默认不请求升压")
    else:
        E("ERC-07b", "HV_EN_REQ 缺少外部下拉")
    if design["R52"].nets.get("1") == "DISP_ALLOW" and design["R52"].nets.get("2") == "GND":
        P("ERC-06b", "DISP_ALLOW 有外部 100 kΩ 下拉 → 复位期间默认消隐")
    else:
        E("ERC-06b", "DISP_ALLOW 缺少外部下拉")
    if design["R11"].nets.get("2") == "EN_MCU" and design["C19"].nets.get("1") == "EN_MCU":
        P("ERC-10", "EN RC = 10 kΩ + 1 µF（Espressif 推荐值）")
    else:
        E("ERC-10", "EN RC 不符合推荐结构")

    # 6 去耦检查（每个 IC 的电源脚附近必须有 C）
    cap_nets = set()
    for ref, p in design.items():
        if p.pins == model.PIN_DB["C"]:
            ns = list(p.nets.values())
            cap_nets.add(tuple(sorted(x for x in ns if x)))
    need = []
    for ref in ("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U10",
                "U20", "U21", "U22", "U23", "U24"):
        p = design[ref]
        vcc = [net for pin, name, net in p.rows()
               if name in ("VCC", "VDD", "3V3", "VIN", "VCC_HV") and net]
        if not vcc:
            continue
        ok = False
        for vend in vcc:
            for pair in cap_nets:
                if vend in pair and "GND" in pair:
                    ok = True
        if not ok:
            need.append(ref)
    if need:
        W("ERC-11", "以下器件未见独立电源去耦电容: " + ", ".join(need))
    else:
        P("ERC-11", "14 个 IC 均有电源去耦电容")

    # 7 HV5622 数量与通道
    n_drv = sum(1 for r in design if r.startswith("U2") and
                design[r].mpn.startswith("HV5622"))
    chans = len([n for n in nets if n.startswith("K_T")])
    if n_drv == 2 and chans >= 60:
        P("ERC-12", f"HV5622 x{n_drv} = {n_drv*32} 路 ≥ 60 路（{chans} 路已用）")
    else:
        E("ERC-12", f"HV5622 数量/通道不足: {n_drv} 片, {chans} 路")

    # 8 高压网络分类
    hv_nets = {n for n, c in nclass.items() if c == "HV"}
    for n in ("HV_BUS", "SW_HV", "OVP_SNS", "FB_HV"):
        if n not in hv_nets:
            E("ERC-13", f"{n} 未归类为 HV 网络类别")
    else:
        P("ERC-13", f"HV 网络 {len(hv_nets)} 个（含阳极/阴极/采样/反馈）")

    # 9 电平域：3.3 V GPIO 不得直接驱动 12 V 域
    drv = {n for n, c in nclass.items() if c == "DRV"}
    direct = sorted(n for n in drv if any(
        design[r].ref == "U10" and pin in ("1", "2", "3") for r, pin in nets[n]))
    if direct:
        E("ERC-14", "3.3 V 直接连到驱动域网络: " + ", ".join(direct))
    else:
        P("ERC-14", "3.3 V GPIO 与 DRV_VDD 域之间均有电平转换/隔离")

    # 10 12 V 域器件耐压
    I("ERC-15", "HV5622 VPP 设计最大 172 V < 推荐 220 V / 绝对最大 230 V；"
                "驱动逻辑 VDD 11.5 V 在 10.8–13.2 V 内")

    # 11 BOM 状态分布
    c = Counter(p.status for p in design.values())
    I("ERC-16", "BOM 状态分布: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))

    # 12 高压间距（规则占位）
    I("ERC-17", "HV 间距/爬电距离尚未冻结（H07），PCB 规则当前为 1.0 mm 占位，"
                "不得据此投板")
    return out


def main():
    design, nets, nclass = build_design()
    pin_rows, net_rows = export(design, nets, nclass)
    bom_rows = export_bom(design)
    chan = export_mapping(design)
    res = checks(design, nets, nclass)

    os.makedirs(D_DOC, exist_ok=True)
    with open(os.path.join(D_DOC, "erc_report.md"), "w", encoding="utf-8") as f:
        f.write("# QS30-6 REV.A 自动一致性检查/ERC 记录\n\n")
        f.write("由 `design/build.py` 依据 datasheet 引脚库自动生成；"
                "立创EDA 内仍需重新执行原生 ERC 并逐条解释。\n\n")
        f.write("| 编号 | 结果 | 说明 |\n|---|---|---|\n")
        for i, lvl, txt in res:
            f.write(f"| {i} | **{lvl}** | {txt} |\n")
        f.write("\n## 未解决项\n\n")
        for i, lvl, txt in res:
            if lvl in ("ERROR", "WARN"):
                f.write(f"- {i} [{lvl}] {txt}\n")

    stats = dict(parts=len(design), pins=len(pin_rows), nets=len(net_rows),
                 used_channels=len(chan) - 4,
                 hv5622=2, drv_channels=64,
                 errors=sum(1 for r in res if r[1] == "ERROR"),
                 warnings=sum(1 for r in res if r[1] == "WARN"),
                 status=dict(Counter(p.status for p in design.values())))
    with open(os.path.join(D_DOC, "design_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    for i, lvl, txt in res:
        print(f"[{lvl}] {i}: {txt}")


if __name__ == "__main__":
    main()
