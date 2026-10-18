# -*- coding: utf-8 -*-
"""HOLD 签署与关闭联动：把"自动证据校验"与"人工签署"合成可审计记录。

输入：
  docs/hold_closure_report.json   （design/evidence_check.py 生成）
  docs/HOLD_SIGNOFF.csv           （模板自动生成；人工填写签署字段）
输出：
  docs/hold_signoff_report.md/.json
规则：
  - CLOSED 仅当：自动证据状态 = complete 且 签署字段齐全（signer/date/rev）
  - 自动通过但未签署 → PENDING_SIGN
  - 未提交证据但签署为 CLOSED → 无效（VOID，需补证据）
  - H01/H09 无对应证据 CSV → 人工类（MANUAL），必须签署 + 附审查记录
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
SIGN = os.path.join(DOC, "HOLD_SIGNOFF.csv")

HOLDS = ["H01", "H02", "H03", "H04", "H05", "H06", "H07", "H08", "H09"]
AUTO_HOLDS = {"H02", "H03", "H04", "H05", "H06", "H07", "H08"}
MANUAL_HOLDS = {"H01", "H09"}


def ensure_template():
    if os.path.exists(SIGN):
        return False
    rows = []
    for h in HOLDS:
        rows.append([h, "", "FILL", "FILL", "FILL", "FILL", "OPEN", ""])
    with open(SIGN, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["hold_id", "evidence_files", "signer", "role", "date",
                    "design_rev", "decision", "comments"])
        w.writerows(rows)
    return True


def main():
    created = ensure_template()
    auto = {}
    if os.path.exists(os.path.join(DOC, "hold_closure_report.json")):
        auto = json.load(open(os.path.join(DOC, "hold_closure_report.json"),
                              encoding="utf-8"))
    with open(SIGN, encoding="utf-8-sig") as f:
        sign = {r["hold_id"]: r for r in csv.DictReader(f)}

    out = []
    counts = dict(CLOSED=0, PENDING_SIGN=0, VIOLATION=0, OPEN=0, MANUAL=0)
    for h in HOLDS:
        r = sign.get(h, {})
        decision = str(r.get("decision", "")).strip().upper()
        signed = all(str(r.get(k, "")).strip() not in ("", "FILL")
                     for k in ("signer", "role", "date", "design_rev"))
        a = auto.get(h, {}).get("status", "manual")
        if h in MANUAL_HOLDS:
            status = "MANUAL" if not signed else ("CLOSED" if decision == "CLOSED" else "MANUAL")
            if status == "MANUAL":
                counts["MANUAL"] += 1
            else:
                counts["CLOSED"] += 1
        elif a == "complete":
            if signed and decision == "CLOSED":
                status = "CLOSED"
                counts["CLOSED"] += 1
            else:
                status = "PENDING_SIGN"
                counts["PENDING_SIGN"] += 1
        elif decision == "CLOSED":
            status = "VIOLATION"
            counts["VIOLATION"] += 1
        else:
            status = "OPEN"
            counts["OPEN"] += 1
        out.append(dict(hold=h, auto=a if h in AUTO_HOLDS else "manual",
                        signer=r.get("signer", ""), date=r.get("date", ""),
                        rev=r.get("design_rev", ""), decision=decision or "OPEN",
                        status=status,
                        comments=r.get("comments", "")))

    lines = ["# HOLD 签署与关闭联动报告", "",
             f"- 已关闭（CLOSED）：**{counts['CLOSED']}**；"
             f"待签署（PENDING_SIGN）：{counts['PENDING_SIGN']}；"
             f"未关闭（OPEN）：{counts['OPEN']}；"
             f"违规关闭（VIOLATION）：{counts['VIOLATION']}",
             f"- 人工类（H01/H09）未签署：{counts['MANUAL']}",
             "",
             "> 规则：CLOSED 需同时满足「自动证据判据通过」且「签署字段齐全」；"
             "证据未通过却签署 CLOSED 记为 VIOLATION。"
             "本报告由 `design/hold_signoff.py` 生成，签署表为 `docs/HOLD_SIGNOFF.csv`。",
             "",
             "| HOLD | 自动证据 | 签署人 | 日期 | 版本 | 决定 | 联动结果 | 备注 |",
             "|---|---|---|---|---|---|---|---|"]
    for o in out:
        lines.append(f"| {o['hold']} | {o['auto']} | {o['signer'] or '—'} | "
                     f"{o['date'] or '—'} | {o['rev'] or '—'} | {o['decision']} | "
                     f"**{o['status']}** | {o['comments'] or ''} |")
    lines += ["", "## 说明", "",
              "- 自动证据：`docs/hold_closure_report.md`（未提交=missing，部分=partial，"
              "通过=complete，判据失败=fail）；",
              "- 人工类 H01/H09 无 CSV 证据，需签署 + 附审查记录；",
              "- 只有 CLOSED 才意味着该 HOLD 解除对投板/生产的阻塞；VIOLATION 必须撤销。"]
    open(os.path.join(DOC, "hold_signoff_report.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(out, open(os.path.join(DOC, "hold_signoff_report.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print(("模板已创建: " + SIGN + "\n") if created else "")
    print("\n".join(lines[:14]))
    if counts["VIOLATION"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
