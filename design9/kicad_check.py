# -*- coding: utf-8 -*-
"""G1：用本机 KiCad 10 CLI 做真实检查并记录结果。

对 MAIN / DISPLAY 各执行：
  1. kicad-cli sch export netlist   （真实 KiCad 加载 + 网表导出）
  2. kicad-cli sch erc              （原生 ERC）
  3. kicad-cli pcb drc              （原生 DRC）
并把 KiCad 导出的网表与 netlist9 CSV（按 DesignRef 映射）逐引脚对比。
输出：kicad/logs/、kicad/EDA_CHECK_RESULTS.md、kicad/eda_check_results.json
运行：python design9/kicad_check.py
"""
import csv
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KC = r"C:\Users\Admin（无密码）\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
PROJ = os.path.join(ROOT, "kicad", "projects")
LOGS = os.path.join(ROOT, "kicad", "logs")
os.makedirs(LOGS, exist_ok=True)
CSV_NET = os.path.join(ROOT, "netlist9", "QS30-9_REV.A_netlist.csv")
BOARDS = {
    "QS30-9_DISPLAY": ("MOD_L",),
    "QS30-9_MAIN": ("MB_", "MOD_C"),
}


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def csv_nets(sheets):
    m = {}
    with open(CSV_NET, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if any(r["sheet"].startswith(s) for s in sheets):
                m[(r["ref"], r["pin"])] = r["net"]
    return m


def kicad_nets(netfile):
    """解析 KiCad 网表：返回 (ref,pin)->net 与 net 数。"""
    txt = open(netfile, encoding="utf-8").read()
    res = {}
    # 先建立 KiCad ref → DesignRef 映射（符号实例属性）
    refmap = {}
    for m in re.finditer(r"\(comp\s+\(ref\s+\"([^\"]+)\"\)(.*?)(?=\(comp\s+\(ref|\(nets\b)", txt, re.S):
        kref, body = m.group(1), m.group(2)
        dm = re.search(r'\(name\s+\"DesignRef\"\)\s+\"([^\"]*)\"', body)
        if dm:
            refmap[kref] = dm.group(1)
    # (net (code "n") (name "X") ... (node (ref "U1") (pin "3") ...))
    for blk in re.findall(r"\(net\s+\(code[^)]*\)\s+\(name\s+\"([^\"]*)\"\)(.*?)(?=\(net\s+\(code|\Z)", txt, re.S):
        name, body = blk
        for ref, pin in re.findall(r"\(ref\s+\"([^\"]+)\"\)\s*\(pin\s+\"([^\"]+)\"\)", body):
            res[(refmap.get(ref, ref), pin)] = name
    return res, len(set(res.values()))


def legacy_main():
    raise RuntimeError('Historical overwrite workflow disabled; use main() with --run NEW_NAME')
    rows = []
    js = {}
    for board, sheets in BOARDS.items():
        pdir = os.path.join(PROJ, board)
        sch = os.path.join(pdir, f"{board}.kicad_sch")
        pcb = os.path.join(pdir, f"{board}.kicad_pcb")
        net = os.path.join(LOGS, f"{board}.net")
        rc1, log1 = run([KC, "sch", "export", "netlist", sch, "-o", net])
        erc = os.path.join(LOGS, f"{board}.erc.rpt")
        rc2, log2 = run([KC, "sch", "erc", sch, "-o", erc])
        drc = os.path.join(LOGS, f"{board}.drc.rpt")
        rc3, log3 = run([KC, "pcb", "drc", pcb, "-o", drc])
        open(os.path.join(LOGS, f"{board}.cli.log"), "w", encoding="utf-8").write(
            f"NETLIST rc={rc1}\n{log1}\n\nERC rc={rc2}\n{log2}\n\nDRC rc={rc3}\n{log3}\n")
        kd, knets = kicad_nets(net) if os.path.exists(net) else ({}, 0)
        cd = csv_nets(sheets)
        matched = sum(1 for k, v in cd.items() if kd.get(k) == v)
        common = sum(1 for k in cd if k in kd)
        erc_txt = open(erc, encoding="utf-8", errors="replace").read() if os.path.exists(erc) else ""
        drc_txt = open(drc, encoding="utf-8", errors="replace").read() if os.path.exists(drc) else ""
        def count(txt, *pats):
            return sum(len(re.findall(p, txt, re.I)) for p in pats)
        row = dict(board=board, netlist_rc=rc1, kicad_nets=knets,
                   kicad_nodes=len(kd), csv_nodes=len(cd), common_nodes=common,
                   net_match=matched, net_total=len(cd),
                   erc_rc=rc2, erc_errors=count(erc_txt, r"error", r"错误"),
                   erc_warnings=count(erc_txt, r"warning", r"警告"),
                   drc_rc=rc3, drc_errors=count(drc_txt, r"error", r"错误", r"violation"),
                   drc_warnings=count(drc_txt, r"warning", r"警告"))
        rows.append(row)
        js[board] = row
        print(board, row)
    md = ["# KiCad 10 原生检查结果（真实日志）", "",
          f"工具：`{KC}`（KiCad 10.0.6）；日志：`kicad/logs/`", "",
          "| 板 | 网表导出 | KiCad 网络/节点 | CSV 节点 | 名称一致 | 节点对应 | ERC rc | ERC 错误/警告 | DRC rc | DRC 错误/警告 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['board']} | rc={r['netlist_rc']} | {r['kicad_nets']}/{r['kicad_nodes']} | "
                  f"{r['csv_nodes']} | {r['net_match']}/{r['net_total']} | {r['common_nodes']} | "
                  f"rc={r['erc_rc']} | {r['erc_errors']}/{r['erc_warnings']} | "
                  f"rc={r['drc_rc']} | {r['drc_errors']}/{r['drc_warnings']} |")
    md += ["", "## 状态分级", "",
           "| 级别 | 状态 | 证据 |", "|---|---|---|",
           "| L1 已生成 | ✅ | kicad/projects/*（6 文件） |",
           "| L2 语法解析 | ✅ | kiutils 1.4.8 回读成功 |",
           "| L3 能在 KiCad 打开 | ✅ | 本表 netlist_rc=0（KiCad 10.0.6 真实加载并导出） |",
           "| L4 原生 ERC | ✅ 已执行（见日志；存在错误/警告未修复） | kicad/logs/*.erc.rpt |",
           "| L5 原生 DRC | ✅ 已执行（初布局，存在错误/警告未修复） | kicad/logs/*.drc.rpt |",
           "", "## 未完成/风险", "",
           "- ERC/DRC 日志中的错误**尚未修复**，PCB 仅为初布局（矩形近似焊盘、无布线）；",
           "- 管座/HV 连接器/PQFP-44 封装尺寸仍为 PROVISIONAL，不能据此刻板；",
           "- 名称一致率反映自动符号+标签映射是否正确；未一致项需逐项修（见日志）。"]
    open(os.path.join(ROOT, "kicad", "EDA_CHECK_RESULTS.md"), "w",
         encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(js, open(os.path.join(ROOT, "kicad", "eda_check_results.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote kicad/EDA_CHECK_RESULTS.md + logs/")


def main():
    """REV.A9.1 safe entry point; historical checker retained above for review."""
    import argparse
    from pathlib import Path
    from reconcile9 import capture
    parser = argparse.ArgumentParser(description='Append-only native KiCad checks; never overwrites a run')
    parser.add_argument('--run', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in ('.', '..'):
        parser.error('run must be a single new directory name')
    result = capture(args.run, args.publish)
    return 0 if all(b['reconciliation']=='PASS' for b in result['boards'].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
