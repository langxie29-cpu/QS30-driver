# -*- coding: utf-8 -*-
"""补充工程构建材料（可复现）：

  bom/QS30-6_REV.A_BOM_qty.csv              按 型号/值/封装 汇总数量与位号（含 DNP 单列）
  netlist/by_sheet/P?_nets.csv              逐页网络清单（立创EDA 录入用）
  docs/symbol_footprint_mapping.csv         符号脚号 ↔ 封装焊盘号 ↔ 原厂脚号 总表（H09 证据）
  docs/pcb_rule_matrix.csv                  网络类别 → 走线/间距规则矩阵（H07 占位，待定稿）

运行：python design/export_extra.py
"""
import csv
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import sheet_lv
import sheet_hv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_BOM = os.path.join(ROOT, "bom")
D_NL = os.path.join(ROOT, "netlist")
D_DOC = os.path.join(ROOT, "docs")


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build():
    sheet_lv.build()
    sheet_hv.build()
    model.class_by_prefix()
    return model.DESIGN, model.NETS, model.NET_CLASS


# ---------------------------------------------------------------------------
def bom_qty(design):
    grouped = OrderedDict()
    for p in design.values():
        key = (p.mpn, p.val, p.pkg, p.status)
        g = grouped.setdefault(key, dict(qty=0, refs=[], dnp=[]))
        if "DNP" in p.flags:
            g["dnp"].append(p.ref)
        else:
            g["qty"] += 1
            g["refs"].append(p.ref)
    rows = []
    for (mpn, val, pkg, status), g in grouped.items():
        rows.append([mpn, val, pkg, status, g["qty"], " ".join(g["refs"]),
                     " ".join(g["dnp"])])
    rows.sort(key=lambda r: (-r[4], r[0]))
    write_csv(os.path.join(D_BOM, "QS30-6_REV.A_BOM_qty.csv"),
              ["mpn_or_value", "value", "package", "status", "qty_populated",
               "refs_populated", "refs_dnp"], rows)
    return rows


def by_sheet_nets(design, nets, nclass):
    sheets = OrderedDict()
    for net, members in nets.items():
        for ref, pin in members:
            sheets.setdefault(design[ref].sheet, set()).add(net)
    out = []
    for sid in sorted(sheets):
        rows = []
        for net in sorted(sheets[sid]):
            mem = [(r, p) for r, p in nets[net]]
            local = [f"{r}.{p}" for r, p in mem if design[r].sheet == sid]
            remote = [f"{r}.{p}" for r, p in mem if design[r].sheet != sid]
            rows.append([net, nclass.get(net, ""), len(local), " ".join(local),
                         " ".join(remote)])
        fn = os.path.join(D_NL, "by_sheet", f"{sid}_nets.csv")
        write_csv(fn, ["net", "net_class", "local_pins", "local_members",
                       "cross_sheet_members"], rows)
        out.append((sid, len(rows)))
    return out


PIN_TABLE = {
    "ESP32-S3-WROOM-1": ("S1", "VERIFIED"),
    "HV5622-PQFP44": ("S5", "VERIFIED"),
    "TPS54202": ("S8", "VERIFIED"),
    "SY8089A": ("S10", "VERIFIED"),
    "CD40109B": ("S13", "VERIFIED"),
    "USBLC6-2SC6": ("S12", "VERIFIED"),
    "LM393": ("S14", "VERIFIED"),
    "TL431": ("S17", "VERIFIED"),
    "74HC08": ("S15", "VERIFIED"),
    "UC3843": ("S16", "VERIFIED"),
    "QS30-1": ("S6", "VERIFIED"),
    "SOCKET-13": ("S6", "PROVISIONAL（封装尺寸 H03）"),
}


def mapping(design):
    rows = []
    for ref, p in design.items():
        pins = list(p.pins.items())
        if len(pins) <= 3:
            continue            # 两/三脚无源件不必逐脚列
        key = None
        if "SOCKET" in p.mpn.upper() or p.mpn.startswith("J13"):
            key = "SOCKET-13"
        elif p.mpn.startswith("ESP32-S3-WROOM"):
            key = "ESP32-S3-WROOM-1"
        elif p.mpn.startswith("HV5622"):
            key = "HV5622-PQFP44"
        for k in ([] if key else list(PIN_TABLE)):
            if k == p.mpn or p.mpn.startswith(k) or k == "HV5622-PQFP44":
                if k == "HV5622-PQFP44" and not p.mpn.startswith("HV5622"):
                    continue
                key = k
                break
        src, st = PIN_TABLE.get(key, ("-", "PROVISIONAL"))
        for num, name in pins:
            rows.append([ref, p.mpn, p.pkg, num, name, num,
                         "焊盘号=符号脚号（1:1）", src, st])
    write_csv(os.path.join(D_DOC, "symbol_footprint_mapping.csv"),
              ["ref", "mpn", "package", "symbol_pin", "pin_name",
               "footprint_pad", "mapping_rule", "pin_source", "verify_status"],
              rows)
    return rows


ZONES = [
    ["Z1", "ESP32-S3 模组 + USB-C", "天线禁布区（全层禁铜/禁线/禁孔/禁件）",
     "H08", "模组 18×25.5，天线端伸出板边；外壳净空 ≥15 mm 待实测"],
    ["Z2", "12V→5V→3.3V + 电源选择", "开关电源输入回路小、远离天线",
     "H05", "输入回路面积最小；5V_SYS 去耦靠近 U2"],
    ["Z3", "HV5622 ×2", "高压输出扇出区", "H07", "HVOUT 到管座走线短、不跨越地分割"],
    ["Z4", "升压 + OVP + DRV_VDD 开关", "高压功率回路", "H06/H07",
     "L20/Q20/D20/C50 环路最小；OVP 紧邻；隔离槽 2 mm"],
    ["Z5", "六组管座 + 阳极限流", "高压/可触及区", "H03/H07",
     "管座中心距 36 mm 占位；阳极电阻就近"],
    ["Z6", "测试点/扩展接口", "低压调试区", "H05", "TP1–TP20、J4"],
]


def rule_matrix(nclass):
    rows = []
    counts = {}
    for n, c in nclass.items():
        counts[c] = counts.get(c, 0) + 1
    for cls, r in model.CLASS_RULES.items():
        rows.append([cls, counts.get(cls, 0), r["clearance_mm"], r["trace_mm"],
                     r["note"], "H07 定稿前为占位，不得据此投板"])
    for z in ZONES:
        rows.append(["ZONE " + z[0], "-", "-", "-",
                     f"{z[1]}：{z[2]}（{z[3]}）", z[4]])
    write_csv(os.path.join(D_DOC, "pcb_rule_matrix.csv"),
              ["class_or_zone", "net_count", "clearance_mm", "trace_mm",
               "scope", "status"], rows)
    return rows


def main():
    design, nets, nclass = build()
    q = bom_qty(design)
    s = by_sheet_nets(design, nets, nclass)
    m = mapping(design)
    r = rule_matrix(nclass)
    print(f"BOM 汇总: {len(q)} 组（含 DNP 单列）")
    print("逐页网络清单:", ", ".join(f"{sid}={n}" for sid, n in s))
    print(f"符号/焊盘映射总表: {len(m)} 行（多脚器件逐脚）")
    print(f"规则矩阵: {len(r)} 行")


if __name__ == "__main__":
    main()
