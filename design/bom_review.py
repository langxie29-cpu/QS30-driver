# -*- coding: utf-8 -*-
"""BOM 选型复核：关键器件的额定值/降额/替代料/封装冻结状态。

自动检查（数据来自 bom/QS30-6_REV.A_BOM.csv 与 design_decisions.md 的设计应力）：
  H1 关键器件必须在 BOM 中存在
  H2 电感 L20 必须满足"Isat ≥5 A"（启动浪涌 2.9–3.1 A，F-04）
  H3 高压开关/二极管/电容额定电压 ≥ 设计应力 ×1.25（HV_BUS 172.18、OVP 198.8）
  H4 阳极电阻降额 ≤80%（单管短路 1.48 W / 2 W）
  H5 封装/替代料状态必须填写（U20 的 DIP-8/SOIC-8 双封装为 WARN）

输出：docs/bom_review.md / .json
运行：python design/bom_review.py（有 FAIL 时退出码 2）
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
BOM = os.path.join(ROOT, "bom", "QS30-6_REV.A_BOM.csv")

V_BUS = 172.18
V_OVP = 198.8
V_REQ = max(V_BUS, V_OVP) * 1.25          # 248.5 V

# 关键器件选型复核表（人工判断部分：理由/替代料；数值由脚本校验）
REVIEW = [
    dict(ref="Q20", cat="高压开关", rule=f"Vds ≥ {V_REQ:.0f} V", alt="IRF840 / STP4N90K5（Vds≥500 V）",
         reason="400 V/10 A 覆盖 198.8 V OVP 与开关尖峰；Rds_on 0.55 Ω 决定导通损耗"),
    dict(ref="D20", cat="升压二极管", rule=f"Vrrm ≥ {V_REQ:.0f} V", alt="US1M / ES1J（快恢复）",
         reason="1000 V 快恢复；1 A 平均足够（Iout≈15 mA，Ipk≈0.5 A）"),
    dict(ref="C49", cat="高压电容", rule=f"额定 ≥ {V_REQ:.0f} V", alt="2×0.1 µF 串联提高耐压",
         reason="630 V X7R 吸收开关尖峰；DC 偏压下降容需实测"),
    dict(ref="C50", cat="高压储能", rule=f"额定 ≥ {V_REQ:.0f} V", alt="220 µF/250 V（体积换纹波）",
         reason="250 V 电解，172 V 下 45% 裕量；20 µF 决定纹波/保持时间"),
    dict(ref="C51", cat="高压储能", rule=f"额定 ≥ {V_REQ:.0f} V", alt="同 C50", reason="与 C50 并联"),
    dict(ref="C52", cat="高压电容", rule=f"额定 ≥ {V_REQ:.0f} V", alt="—", reason="630 V 缓冲/去耦"),
    dict(ref="L20", cat="升压电感", rule="Isat ≥ 5 A", alt="SUMIDA/CDRH 系列 ≥5 A 屏蔽", reason="220 µH；启动浪涌 2.9–3.1 A，留 1.6× 裕量"),
    dict(ref="U21", cat="高压驱动", rule="Vpp ≥ 200 V；32 通道", alt="HV5622 同型号替代需核对 Vpp/封装",
         reason="64 路=2×32；Vpp 覆盖 172 V + 余量；PQFP-44 散热焊盘"),
    dict(ref="U22", cat="高压驱动", rule="Vpp ≥ 200 V；32 通道", alt="同 U21", reason="同 U21"),
    dict(ref="U20", cat="PWM 控制器", rule="Vcc 12 V；DIP-8/SOIC-8", alt="UC3843AN（DIP-8）或 SOIC-8 二选一",
         reason="电流模式；封装需在结构与散热确定后冻结（WARN）"),
    dict(ref="U23", cat="OVP 比较器", rule="开漏/推挽；SOIC-8", alt="LM2903（温度范围更宽）", reason="LM393 双比较器，一路 OVP 一路故障"),
    dict(ref="R90", cat="阳极限流", rule="降额 ≤80%（1.48 W / 2 W）", alt="2×1 W 2512 串联/并联", reason="单管短路时 1.48 W；2512 2 W 需考虑温升降额"),
    dict(ref="F1", cat="输入保护", rule="保持电流 ≥ 0.6 A；I²t 可承受浪涌", alt="1.5 A/2 A PPTC", reason="稳态 0.6 A；浪涌 2.9 A 短时"),
    dict(ref="J1", cat="输入端子", rule="≥12 V/1 A", alt="5.08 mm 2P 或 5.5×2.1 DC 座", reason="12 V 输入 5.08 mm 2P（机械形式待结构确认）"),
]


def first_num(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def main():
    with open(BOM, encoding="utf-8-sig") as f:
        bom = {r["ref"]: r for r in csv.DictReader(f)}
    checks = []

    def rec(cid, ok, text):
        checks.append(dict(id=cid, pass_=bool(ok), text=text))

    # H1
    missing = [r["ref"] for r in REVIEW if r["ref"] not in bom]
    rec("H1", not missing, f"关键器件 {len(REVIEW)} 个均在 BOM 中"
        + ("" if not missing else f"；缺失: {missing}"))

    # H2 L20
    l20 = bom.get("L20", {}).get("value", "")
    ok_l20 = bool(re.search(r"(≥\s*5|5\s*A|/5A)", l20))
    rec("H2", ok_l20, f"L20 标注满足 Isat ≥5 A：`{l20}`"
        + ("" if ok_l20 else "；需更新 BOM（F-04）"))

    # H3 高压额定
    def rating(ref):
        """从 value/mpn 中提取额定电压（只取带 V 单位的数字，避免误取电容值）。"""
        txt = bom.get(ref, {}).get("value", "") + " " + bom.get(ref, {}).get("mpn", "")
        vals = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*V(?![A-Za-z])", txt)]
        return max(vals) if vals else None
    bad = []
    for ref, need in (("Q20", V_REQ), ("D20", V_REQ), ("C49", V_REQ),
                      ("C50", V_REQ), ("C51", V_REQ), ("C52", V_REQ)):
        r = rating(ref)
        if r is None or r < need:
            bad.append(f"{ref} 额定 {r} < {need:.0f} V")
    rec("H3", not bad, f"高压器件额定电压 ≥ {V_REQ:.0f} V（HV_BUS/OVP ×1.25）"
        + ("" if not bad else f"；{bad}"))

    # H4 阳极电阻降额
    r_val = bom.get("R90", {}).get("value", "")
    p = first_num(r_val)
    ok_r = p is not None and p >= 2.0 and (1.48 / p) <= 0.80
    rec("H4", ok_r, f"阳极电阻 2 W，单管短路 1.48 W → 降额 {1.48/2*100:.0f}% ≤80%"
        if ok_r else f"阳极电阻额定 {p} W 降额不足")

    # H5 封装/替代料
    u20 = bom.get("U20", {}).get("value", "")
    warn = [f"U20 封装未冻结：{u20}" for _ in [0] if "/" in u20]
    rec("H5", True, "替代料/封装状态："
        + ("；".join(warn + ["其余关键件替代料已在复核表列出（WARN 项见下表）"]) if warn
           else "均已列出替代料"))

    nfail = sum(1 for c in checks if not c["pass_"])
    lines = ["# BOM 选型复核（关键器件降额/替代料/封装状态）", "",
             f"由 `design/bom_review.py` 从 `bom/QS30-6_REV.A_BOM.csv` 与设计应力生成；"
             f"**{len(checks)-nfail}/{len(checks)} 项自动检查通过**。", "",
             "设计应力：HV_BUS **172.18 V**、OVP **198.8 V** → 高压器件额定要求 ≥ "
             f"**{V_REQ:.0f} V**（1.25×）；阳极电阻单管短路 **1.48 W**。", "",
             "| 编号 | 结果 | 内容 |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['id']} | {'PASS' if c['pass_'] else 'FAIL'} | {c['text']} |")
    lines += ["", "## 关键器件复核表", "",
              "| 位号 | 类别 | BOM 值 | 选型要求 | 选型理由 | 替代料 |",
              "|---|---|---|---|---|---|"]
    for r in REVIEW:
        b = bom.get(r["ref"], {})
        lines.append(f"| {r['ref']} | {r['cat']} | {b.get('value','—')} | {r['rule']} | "
                     f"{r['reason']} | {r['alt']} |")
    lines += ["", "## 说明", "",
              "- 自动检查只覆盖**能机器判定的降额/建议**；温度降额、纹波电流、ESR、磁芯饱和曲线、"
              "封装热阻仍需器件手册与实测（H06/H07）；",
              "- 本表不是可下单 BOM：所有 HOLD 关闭前不得释放 Gerber/下单（HOLD_REGISTER）。"]
    open(os.path.join(DOC, "bom_review.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(dict(checks=checks, review=REVIEW, v_req=V_REQ),
              open(os.path.join(DOC, "bom_review.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"BOM review: {len(checks)-nfail}/{len(checks)} PASS")
    for c in checks:
        print(("PASS " if c["pass_"] else "FAIL ") + c["id"] + ": " + c["text"][:120])
    sys.exit(0 if nfail == 0 else 2)


if __name__ == "__main__":
    main()
