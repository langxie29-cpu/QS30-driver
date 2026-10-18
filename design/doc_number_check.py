# -*- coding: utf-8 -*-
"""文档关键数字一致性检查（防跨文档漂移）。

背景：项目有 20+ 交付物，同一关键数字（HV_BUS 172.18 V、OVP 198.8 V、效率 95.9%、
平均模型 8/8、60 通道、227 器件…）被多处引用，历史上已出现"95.8% vs 95.9%""负载
3.9 V/158 ms（实为输入阶跃）"等漂移。本脚本：

  C1 关键数字必须在 README/design_decisions 中出现（防止交付物漏更新）
  C2 当前状态文档中不得出现已废弃的旧值（CHANGELOG/行为模型历史章节除外）
  C3 平均模型判据数量必须是 8/8（曾为 7/7）
  C4 审查包页数与 CHANGELOG 最后一条记录的页数一致
  C5 交付物数字与机器可读结果（design_summary.json / spice_validation.json /
     drc_precheck.json / test_plan_check.json）一致

输出：docs/doc_consistency.md / .json
运行：python design/doc_number_check.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")

# 允许出现"历史值"的文件（变更记录/历史章节）
HISTORY_FILES = {"REV_A_CHANGELOG.md"}
# 当前状态文档（必须与最新结果一致）
CURRENT = ["README.md", "design_decisions.md", "open_issues.md",
           "HOLD_REGISTER.md", "sim/README.md", "docs/loop_scan.md",
           "docs/ovp_timing.md", "docs/test_plan_check.md"]

CANON = [
    (r"172\.18", "HV_BUS 稳态 172.18 V"),
    (r"198\.8", "OVP 阈值 198.8 V"),
    (r"95\.9\s*%", "功率级 SPICE 效率 95.9%"),
    (r"227", "器件数 227"),
    (r"736", "引脚数 736"),
    (r"60", "60 路阴极"),
]

STALE = [
    (r"95\.8\s*%", "旧效率 95.8%（应为 95.9%）"),
    (r"负载[^\n]{0,30}158\s*ms", "把输入阶跃恢复 158 ms 误归因为负载阶跃"),
    (r"启动建立时间", "启动建立时间：平均模型已改为初值=工作点，启动由行为模型 S1 覆盖"),
]


def read(p):
    try:
        return open(os.path.join(ROOT, p), encoding="utf-8").read()
    except FileNotFoundError:
        return ""


def main():
    checks = []

    def rec(cid, ok, text):
        checks.append(dict(id=cid, pass_=bool(ok), text=text))

    # C1 关键数字存在
    readme = read("README.md")
    dd = read("design_decisions.md")
    missing = [desc for pat, desc in CANON
               if not re.search(pat, readme) or not re.search(pat, dd)]
    rec("C1", not missing, "README 与 design_decisions 均包含关键数字"
        + ("" if not missing else f"；缺失: {missing}"))

    # C2 当前文档不得含废弃值
    bad = []
    EXPLAIN = ("漂移", "历史", "已修正", "旧值", "废弃", "→ ")
    for p in CURRENT:
        for line in read(p).splitlines():
            if any(w in line for w in EXPLAIN):
                continue        # 说明"某旧值已修正"的句子不是漂移
            for pat, desc in STALE:
                if re.search(pat, line):
                    bad.append(f"{p}: {desc} → {line.strip()[:110]}")
    rec("C2", not bad, "当前状态文档无废弃旧值"
        + ("" if not bad else f"；发现 {len(bad)} 处: {bad[:4]}"))

    # C3 平均模型判据数量
    bad = []
    for p in CURRENT:
        s = read(p)
        if "平均模型" in s:
            for m in re.finditer(r"平均模型[^\n]{0,40}?(\d+)\s*/\s*(\d+)", s):
                if (m.group(1), m.group(2)) != ("8", "8"):
                    bad.append(f"{p}: 平均模型判据 {m.group(1)}/{m.group(2)}（应为 8/8）")
    rec("C3", not bad, "平均模型判据数量为 8/8" + ("" if not bad else f"；{bad[:4]}"))

    # C4 审查包页数 vs CHANGELOG 最后记录
    import pymupdf
    pages = pymupdf.open(os.path.join(DOC, "QS30-6_REV.A_审查包.pdf")).page_count
    cl = read("REV_A_CHANGELOG.md")
    cl_pages = [int(x) for x in re.findall(r"审查包\s*(\d+)\s*页", cl)]
    last_cl = cl_pages[-1] if cl_pages else None
    rec("C4", last_cl == pages,
        f"审查包实际 {pages} 页，CHANGELOG 最后记录 {last_cl} 页")

    # C5 与机器可读结果一致
    d = json.load(open(os.path.join(DOC, "design_summary.json"), encoding="utf-8"))
    sv = json.load(open(os.path.join(ROOT, "sim", "results",
                                     "spice_validation.json"), encoding="utf-8"))
    drc = json.load(open(os.path.join(DOC, "drc_precheck.json"), encoding="utf-8"))
    tp = json.load(open(os.path.join(DOC, "test_plan_check.json"), encoding="utf-8"))
    avg = sv["averaged_closed_loop"]
    checks_avg = sum(1 for _, ok in avg["checks"] if ok)
    want = {
        "parts": (d["parts"], 227),
        "pins": (d["pins"], 736),
        "nets": (d["nets"], 172),
        "channels": (d["used_channels"], 60),
        "part_errors": (d["errors"], 0),
        "part_warnings": (d["warnings"], 0),
        "drc": (drc["passed"], drc["total"]),
        "avg_checks": (checks_avg, len(avg["checks"])),
        "testplan": (tp["passed"], tp["total"]),
    }
    bad = [f"{k}: 实际 {v[0]} / 期望 {v[1]}" for k, v in want.items() if v[0] != v[1]]
    rec("C5", not bad, f"机器结果一致（design_summary/spice/drc/test_plan）"
        + ("" if not bad else f"；{bad}"))

    npass = sum(1 for c in checks if c["pass_"])
    lines = ["# 文档关键数字一致性检查", "",
             f"由 `design/doc_number_check.py` 自动生成；**{npass}/{len(checks)} 项通过**。", "",
             "| 编号 | 结果 | 内容 |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['id']} | {'PASS' if c['pass_'] else 'FAIL'} | {c['text']} |")
    lines += ["", "## 当前关键数字（单一事实来源：机器可读结果）", "",
              "| 项目 | 值 |", "|---|---|",
              f"| HV_BUS 稳态 | 172.18 V（误差 3 mV） |",
              f"| OVP 阈值 / 首次触发 | 198.8 V / {sv['ovp_logic']['trip_level']:.2f} V |",
              f"| 功率级 SPICE 输出/效率 | {sv['boost']['vout_mean']:.2f} V / "
              f"{sv['boost']['eff_pct']:.1f}% |",
              f"| 平均模型闭环判据 | {checks_avg}/{len(avg['checks'])} |",
              f"| OVP 保护逻辑判据 | {sum(1 for _, ok in sv['ovp_logic']['checks'] if ok)}/"
              f"{len(sv['ovp_logic']['checks'])} |",
              f"| 器件/引脚/网络/通道 | {d['parts']} / {d['pins']} / {d['nets']} / {d['used_channels']} |",
              f"| ERC / DRC 预检 | 0/0 错误告警 / {drc['passed']}/{drc['total']} |",
              f"| 测试计划一致性 | {tp['passed']}/{tp['total']} |",
              f"| 审查包 | {pages} 页 |"]
    open(os.path.join(DOC, "doc_consistency.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(passed=npass, total=len(checks), checks=checks),
              open(os.path.join(DOC, "doc_consistency.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"doc consistency: {npass}/{len(checks)} PASS")
    for c in checks:
        print(("PASS " if c["pass_"] else "FAIL ") + c["id"] + ": " + c["text"][:130])
    sys.exit(0 if npass == len(checks) else 2)


if __name__ == "__main__":
    main()
