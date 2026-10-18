# -*- coding: utf-8 -*-
"""测试计划 ↔ 证据模板一致性检查。

检查 `docs/test_plan.csv`（由 docs/test_plan.md 整理的机器可读版）：
  T1 序号唯一、阶段齐全（A–E）、状态合法
  T2 每个 evidence_target 引用的 HOLD 合法（H01–H09）且证据文件存在
  T3 每个 H02–H08 证据 CSV 至少被一个测试项引用（无孤立证据）
  T4 高压相关测试（C 阶段）必须引用 H06；管座/管子测试必须引用 H02/H03；RF 必须引用 H08
  T5 test_plan.md 与 test_plan.csv 的序号集合一致（防止文档漂移）

输出：docs/test_plan_check.md / .json
运行：python design/test_plan_check.py
"""
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
EV = os.path.join(DOC, "evidence")

HOLDS = [f"H{i:02d}" for i in range(1, 10)]
AUTO_HOLDS = {f"H{i:02d}" for i in range(2, 9)}
STATUS = {"待执行", "进行中", "通过", "失败", "N/A"}


def load():
    with open(os.path.join(DOC, "test_plan.csv"), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    rows = load()
    rows_by_id = {r["id"]: r for r in rows}
    checks = []

    def rec(cid, ok, text):
        checks.append(dict(id=cid, pass_=bool(ok), text=text))

    # T1
    dup = {i for i in rows_by_id if sum(1 for r in rows if r["id"] == i) > 1}
    stages = {r["stage"] for r in rows}
    bad_status = [r["id"] for r in rows if r["status"] not in STATUS]
    rec("T1", not dup and stages == {"A", "B", "C", "D", "E"} and not bad_status,
        f"{len(rows)} 项；阶段 {sorted(stages)}；重复序号 {dup or '无'}；"
        f"非法状态 {bad_status or '无'}")

    # T2
    bad = []
    used = set()
    for r in rows:
        for tgt in r["evidence_target"].split(";"):
            tgt = tgt.strip()
            if not tgt:
                continue
            hold, _, fname = tgt.partition(":")
            hold, fname = hold.strip(), fname.strip()
            if hold in ("N/A", ""):
                continue
            if hold not in HOLDS:
                bad.append(f"{r['id']} 非法 HOLD {hold}")
                continue
            if hold in AUTO_HOLDS:
                p = os.path.join(EV, fname)
                if not os.path.exists(p):
                    bad.append(f"{r['id']} 证据文件缺失 {fname}")
                else:
                    used.add(fname)
    rec("T2", not bad, "每个测试项的 evidence_target 均指向存在的证据文件"
        + ("" if not bad else f"；问题: {bad[:8]}"))

    # T3
    all_csv = {f for f in os.listdir(EV) if f.endswith(".csv")}
    orphan = sorted(all_csv - used)
    rec("T3", not orphan, f"证据 CSV {len(all_csv)} 个，全部被测试计划引用"
        + ("" if not orphan else f"；孤立: {orphan}"))

    # T4 关键映射
    def targets(stage_prefix):
        return [r for r in rows if r["id"].startswith(stage_prefix)]
    req = []
    for r in targets("C"):
        if r["id"] == "C0":
            if not r["evidence_target"].startswith("H07"):
                req.append("C0 未指向 H07")
        elif not r["evidence_target"].startswith("H06"):
            req.append(f"{r['id']} 未指向 H06")
    for r in targets("D"):
        tgt = r["evidence_target"]
        if not (tgt.startswith("H02") or tgt.startswith("H03")):
            req.append(f"{r['id']} 未指向 H02/H03")
    for r in targets("E"):
        if r["id"] == "E3" and not r["evidence_target"].startswith("H08"):
            req.append("E3 未指向 H08")
    if not any(r["evidence_target"].startswith("H04") for r in targets("B")):
        req.append("B 阶段缺少 H04 walking-one 引用")
    rec("T4", not req, "阶段↔证据映射正确（C→H06、C0→H07、D→H02/H03、B→H04、E3→H08）"
        + ("" if not req else f"；问题: {req}"))

    # T5 与 test_plan.md 序号一致性
    md = open(os.path.join(DOC, "test_plan.md"), encoding="utf-8").read()
    md_ids = set(re.findall(r"\|\s*([A-E]\d{1,2})\s*\|", md))
    csv_ids = set(rows_by_id)
    missing = sorted(md_ids - csv_ids)
    extra = sorted(csv_ids - md_ids)
    rec("T5", not missing and not extra,
        f"test_plan.md 序号 {len(md_ids)} 个，CSV {len(csv_ids)} 个，一致"
        + ("" if not (missing or extra) else f"；md 缺 {missing}；csv 多 {extra}"))

    npass = sum(1 for c in checks if c["pass_"])
    lines = ["# 测试计划 ↔ 证据一致性检查", "",
             f"由 `design/test_plan_check.py` 从 `docs/test_plan.md`（人读）+ "
             f"`docs/test_plan.csv`（机读）自动生成；**{npass}/{len(checks)} 项通过**。", "",
             "| 编号 | 结果 | 内容 |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['id']} | {'PASS' if c['pass_'] else 'FAIL'} | {c['text']} |")
    lines += ["", "## 测试项一览（阶段 / 证据目标 / 状态）", "",
              "| 阶段 | 序号 | 测试 | 证据目标 | 状态 |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['stage']} | {r['id']} | {r['test']} | "
                     f"{r['evidence_target']} | {r['status']} |")
    lines += ["", "说明：`evidence_target` 为 `HOLD:CSV` 时，CSV 位于 `docs/evidence/`；"
              "`N/A:*` 表示该测试只需人工记录（截图/波形/视频），不进入自动证据判据。"]
    open(os.path.join(DOC, "test_plan_check.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(passed=npass, total=len(checks), rows=checks,
                   test_ids=sorted(csv_ids)), open(os.path.join(DOC, "test_plan_check.json"),
                                                   "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"test_plan_check: {npass}/{len(checks)} PASS")
    for c in checks:
        print(("PASS " if c["pass_"] else "FAIL ") + c["id"] + ": " + c["text"][:110])
    raise SystemExit(0 if npass == len(checks) else 2)


if __name__ == "__main__":
    main()
