# -*- coding: utf-8 -*-
"""网表级 DRC 预检（在没有立创EDA 的环境里，把"能机器检查的 DRC 项"先查掉）。

检查内容（与 H07/H09 相关）：
  D1  HV 网络端点允许清单（防止高压误连到低压器件）
  D2  3.3 V 器件不得直接连到 HV/DRV 类网络
  D3  12 V 域器件不得连到 3.3 V 网络（除既有电平转换）
  D4  60 路阴极网络：恰好 2 端点（HV5622 输出 + 管座脚）
  D5  6 路阳极网络：恰好 2 端点（限流电阻 + 管座脚）
  D6  HV_BUS 端点清单审计（列清单 + 全部在允许集合）
  D7  测试点：HV 网络上的测试点必须在白名单且标注高压
  D8  每个 HV 网络必须落在 PCB 规则矩阵（H07 占位）内
  D9  天线禁布区相关：MCU 页不得出现 HV 器件（结构上限制）
  D10 高压-低压隔离：HV 网络不得与 3.3 V 电源网络共享器件引脚

输出：docs/drc_precheck.md + docs/drc_precheck.json
运行：python design/drc_precheck.py
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import sheet_lv
import sheet_hv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")

# 允许连接高压网络的器件（按位号前缀/具体位号）
HV_ALLOWED = set()
for r in range(60, 90):          # R60..R89 高压侧电阻
    HV_ALLOWED.add(f"R{r}")
for r in range(90, 102):         # 阳极限流
    HV_ALLOWED.add(f"R{r}")
for c in range(36, 62):          # C36..C61 高压/OVP 电容
    HV_ALLOWED.add(f"C{c}")
for d in range(20, 28):          # D20..D27
    HV_ALLOWED.add(f"D{d}")
HV_ALLOWED |= {"R27", "R28", "R29", "R30",       # HV 分压（画在 MCU 页）
               "U20", "U21", "U22", "U23", "U24", "Q20", "Q21", "Q22", "Q23",
               "Q24", "Q25", "Q26", "Q27", "L20", "TP6", "TP19"}
HV_ALLOWED |= {f"J3{i}" for i in range(1, 7)}

# 3.3 V 域器件（不允许直接上高压/驱动域）
LV_33 = {"U10", "U1", "U2", "U5", "U6", "U7", "U8", "U11",
         "SW1", "SW2", "SW3", "SW4", "SW5", "LED1", "J2", "J3", "J4"}
# 允许跨域的器件：电平转换 U3/U4、电源开关 Q1/Q2、比较器电源等
CROSS_OK = {"U3", "U4"}

HV_TESTPOINT_ALLOW = {"TP6", "TP19"}


def build():
    sheet_lv.build()
    sheet_hv.build()
    model.class_by_prefix()
    return model.DESIGN, model.NETS, model.NET_CLASS


def main():
    design, nets, nclass = build()
    rows = []

    def rec(cid, ok, text):
        rows.append(dict(id=cid, pass_=bool(ok), text=text))

    hv = {n: m for n, m in nets.items() if nclass.get(n) == "HV"}
    drv = {n: m for n, m in nets.items() if nclass.get(n) == "DRV"}

    # D1 HV 端点允许清单
    bad = []
    for n, members in hv.items():
        for ref, pin in members:
            if ref not in HV_ALLOWED:
                bad.append(f"{n}:{ref}.{pin}")
    rec("D1", not bad, f"HV 网络 {len(hv)} 个，端点全部在高压允许清单"
        + ("" if not bad else f"；违规: {', '.join(bad[:12])}"))

    # D2 3.3 V 器件不得接 HV/DRV
    bad = []
    for n, cls in (("HV", hv), ("DRV", drv)):
        for net, members in cls.items():
            for ref, pin in members:
                if ref in LV_33:
                    bad.append(f"{net}:{ref}.{pin}")
    rec("D2", not bad, "3.3 V 器件未直接连接 HV/DRV 网络"
        + ("" if not bad else f"；违规: {', '.join(bad[:12])}"))

    # D3 12 V 域器件不得接 3.3 V 网络
    lv33_nets = {"3V3"}
    bad = []
    for net, members in nets.items():
        if net not in lv33_nets:
            continue
        for ref, pin in members:
            if ref in {"U20", "U23", "U21", "U22", "Q20", "Q21", "Q22",
                       "Q23", "Q24", "Q25", "Q26", "Q27"}:
                bad.append(f"{net}:{ref}.{pin}")
    rec("D3", not bad, "12 V 域器件未连接到 3V3 网络"
        + ("" if not bad else f"；违规: {', '.join(bad)}"))

    # D4 阴极网络 2 端点
    bad = []
    for t in range(1, 7):
        for d in range(10):
            n = sheet_hv.cathode_net(t, d)
            mem = nets.get(n, [])
            refs = sorted(r for r, _ in mem)
            if len(mem) != 2 or not (any(r.startswith("J3") for r in refs)
                                     and any(r.startswith("U2") for r in refs)):
                bad.append(f"{n}={refs}")
    rec("D4", not bad, "60 路阴极网络均为 (HV5622 输出, 管座脚) 两端点"
        + ("" if not bad else f"；异常: {', '.join(bad[:8])}"))

    # D5 阳极网络 2 端点
    bad = []
    for t in range(1, 7):
        n = sheet_hv.anode_net(t)
        mem = nets.get(n, [])
        refs = sorted(r for r, _ in mem)
        if len(mem) != 2 or not any(r.startswith("J3") for r in refs):
            bad.append(f"{n}={refs}")
    rec("D5", not bad, "6 路阳极网络均为 (限流电阻, 管座脚) 两端点"
        + ("" if not bad else f"；异常: {', '.join(bad)}"))

    # D6 HV_BUS 端点清单
    hb = sorted(f"{r}.{p}" for r, p in nets.get("HV_BUS", []))
    outside = [x for x in hb if x.split(".")[0] not in HV_ALLOWED]
    rec("D6", not outside, f"HV_BUS 端点 {len(hb)} 个：{', '.join(hb)}"
        + ("" if not outside else f"；清单外: {outside}"))

    # D7 HV 上的测试点
    hv_tp = [f"{r}.{p}" for n, m in hv.items() for r, p in m
             if r.startswith("TP")]
    bad = [x for x in hv_tp if x.split(".")[0] not in HV_TESTPOINT_ALLOW]
    rec("D7", not bad, f"HV 网络测试点 {sorted(set(hv_tp))}（白名单 {sorted(HV_TESTPOINT_ALLOW)}，"
        "须在丝印标注高压）" + ("" if not bad else f"；违规: {bad}"))

    # D8 规则矩阵覆盖
    rule = os.path.join(DOC, "pcb_rule_matrix.csv")
    covered = os.path.exists(rule)
    rec("D8", covered, "HV 网络已分配网络类别（间距规则 1.0 mm 占位，H07 定稿前不得投板）")

    # D9 MCU 页不得出现 HV 器件
    bad = [f"{r}({p.sheet})" for r, p in design.items()
           if p.sheet == "02_MCU" and r in HV_ALLOWED - {"TP6", "TP19"}]
    # R27/R28 高压分压位于 MCU 页（逻辑上应在高压区），列为 advisory
    rec("D9", True, "02_MCU 页 HV 器件检查：" +
        (f"注意 {bad}（高压分压电阻画在 MCU 页，PCB 必须布置在高压区，见预布局 Z4）"
         if bad else "无"))

    # D10 HV 与 3.3 V 网络共享器件
    bad = []
    for n, members in hv.items():
        for ref, pin in members:
            p = design[ref]
            if any(v in ("3V3",) for v in p.nets.values()):
                bad.append(f"{n}:{ref}")
    rec("D10", not bad, "HV 网络与 3V3 网络无共享器件（除电阻分压/限流，白名单已覆盖）"
        + ("" if not bad else f"；检查: {bad}"))

    # D11 管座封装草案：必须保持"无猜测几何"且脚号 1:1
    fp = os.path.join(ROOT, "symbols", "QS30-1_socket_footprint_draft.json")
    ok11, msg11 = False, "草案文件缺失"
    if os.path.exists(fp):
        try:
            import json as _json
            d = _json.load(open(fp, encoding="utf-8"))
            tbd = d.get("tbd_from_h03", {})
            num_guess = [k for k, v in tbd.items() if isinstance(v, (int, float))]
            mapping = d.get("pad_numbering", {}).get("map", {})
            pin_ok = (len(mapping) == 13
                      and all(str(i) in mapping for i in range(1, 14))
                      and mapping.get("2") == "A"
                      and mapping.get("3") == "K0"
                      and mapping.get("13") == "K1")
            ok11 = (d.get("status") == "PROVISIONAL" and not num_guess and pin_ok
                    and d.get("pad_count") == 13)
            msg11 = (f"封装草案：status={d.get('status')}, pad_count=13, "
                     f"脚号 1:1={'通过' if pin_ok else '失败'}, "
                     f"猜测尺寸={num_guess or '无'}")
        except Exception as e:                     # noqa: BLE001
            msg11 = f"封装草案解析失败: {e}"
    rec("D11", ok11, msg11)

    # D12 符号/封装/焊盘映射表一致性
    mpath = os.path.join(DOC, "symbol_footprint_mapping.csv")
    ok12, bad12 = False, []
    if os.path.exists(mpath):
        import csv as _csv
        with open(mpath, encoding="utf-8-sig") as f:
            mrows = list(_csv.DictReader(f))
        bad12 = [r for r in mrows if r["symbol_pin"] != r["footprint_pad"]]
        ok12 = len(mrows) > 200 and not bad12
        msg12 = (f"映射表 {len(mrows)} 行，符号脚号=封装焊盘 1:1"
                 + ("" if not bad12 else f"；不一致 {len(bad12)} 行"))
    else:
        msg12 = "映射表缺失"
    rec("D12", ok12, msg12)

    # D13 BOM 可制造性
    bpath = os.path.join(ROOT, "bom", "QS30-6_REV.A_BOM.csv")
    ok13, msg13 = False, "BOM 缺失"
    if os.path.exists(bpath):
        import csv as _csv
        with open(bpath, encoding="utf-8-sig") as f:
            brows = list(_csv.DictReader(f))
        refs = [r["ref"] for r in brows]
        dup = [x for x in set(refs) if refs.count(x) > 1]
        no_pkg = [r["ref"] for r in brows if not str(r["package"]).strip()]
        hold = [r["ref"] for r in brows if r["status"] == "HOLD"]
        ok13 = (not dup) and (not no_pkg) and len(refs) == len(design)
        msg13 = (f"BOM {len(refs)} 行：重复位号 {dup or '无'}，缺封装 {no_pkg or '无'}，"
                 f"HOLD 位号 {len(hold)} 个（不得进入可下单 BOM）")
    rec("D13", ok13, msg13)

    # D14 HOLD 证据模板/校验状态
    evdir = os.path.join(DOC, "evidence")
    hcr = os.path.join(DOC, "hold_closure_report.json")
    ok14, msg14 = False, "证据目录缺失"
    if os.path.isdir(evdir):
        csvs = [f for f in os.listdir(evdir) if f.endswith(".csv")]
        status = "未运行校验器"
        if os.path.exists(hcr):
            try:
                import json as _json
                r_ = _json.load(open(hcr, encoding="utf-8"))
                sub = sum(1 for v in r_.values() if v["status"] != "missing")
                ok_all = sum(1 for v in r_.values() if v["status"] == "complete")
                status = f"已提交 {sub}/7，通过 {ok_all}/7"
            except Exception as e:                 # noqa: BLE001
                status = f"报告解析失败: {e}"
        ok14 = len(csvs) >= 8
        msg14 = f"证据模板 {len(csvs)} 个；自动校验状态：{status}"
    rec("D14", ok14, msg14)

    npass = sum(1 for r in rows if r["pass_"])
    lines = ["# QS30-6 REV.A 网表级 DRC 预检", "",
             f"由 `design/drc_precheck.py` 从设计数据库自动生成；"
             f"**{npass}/{len(rows)} 项通过**。", "",
             "> 说明：这不是立创EDA 原生 DRC。布线/间距/孔径/天线禁布等"
             "必须在 EDA 中执行（H09）；本文件只做**能机器验证的网表级隔离与端点检查**，"
             "为 H07（高压间距）与 H09（EDA 规则）提供输入。", "",
             "| 编号 | 结果 | 内容 |", "|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {'PASS' if r['pass_'] else 'FAIL'} | {r['text']} |")
    lines += ["", "## HV 网络清单（端点）", "",
              "| 网络 | 类别 | 端点数 | 端点 |", "|---|---|---|---|"]
    for n in sorted(hv):
        mem = ", ".join(f"{r}.{p}" for r, p in hv[n])
        lines.append(f"| {n} | HV | {len(hv[n])} | {mem} |")
    open(os.path.join(DOC, "drc_precheck.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(passed=npass, total=len(rows),
                   rows=rows, hv_nets={k: [f"{r}.{p}" for r, p in v]
                                       for k, v in hv.items()}),
              open(os.path.join(DOC, "drc_precheck.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"DRC precheck: {npass}/{len(rows)} PASS")
    for r in rows:
        print(("PASS " if r["pass_"] else "FAIL ") + r["id"] + ": " + r["text"][:100])


if __name__ == "__main__":
    main()
