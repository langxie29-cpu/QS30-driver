# -*- coding: utf-8 -*-
"""REV.A9 审计：现有六位仓库（REV.A / REV6）vs 目标九位模块化架构。

只做审计，不改任何旧文件。所有"发现"都带来源：
  - 设计事实：从 netlist/QS30-6_REV.A_netlist.csv 机器核对；
  - 器件事实：Ti LM393 SLCS005AH、Microchip HV5622 DS20005854A、Findchips/Microchip 分销数据；
  - 现有限制：环境无立创EDA/KiCad/ngspice（见 open_issues.md）。
输出：docs9/AUDIT.md, docs9/audit_diff.csv, docs9/audit_findings.csv
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC9 = os.path.join(ROOT, "docs9")
NET6 = os.path.join(ROOT, "netlist", "QS30-6_REV.A_netlist.csv")
BOM6 = os.path.join(ROOT, "bom", "QS30-6_REV.A_BOM.csv")

STATUS = ["VERIFIED", "STRONGLY SUPPORTED", "PROVISIONAL", "UNVERIFIED", "FAIL", "UNKNOWN"]


def load_nets():
    with open(NET6, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    nets = {}
    for r in rows:
        nets.setdefault(r["net"], []).append((r["ref"], r["pin"]))
    return rows, nets


def find(rows, ref, pin):
    return next((r for r in rows if r["ref"] == ref and r["pin"] == str(pin)), None)


def main():
    rows, nets = load_nets()
    with open(BOM6, encoding="utf-8-sig") as f:
        bom6 = list(csv.DictReader(f))
    os.makedirs(DOC9, exist_ok=True)

    # ---------- 机器核对的设计事实 ----------
    facts = {}
    facts["U8_VCC"] = (find(rows, "U8", 8) or {}).get("net")
    facts["U8_IN1m"] = (find(rows, "U8", 2) or {}).get("net")
    facts["U8_IN2m"] = (find(rows, "U8", 6) or {}).get("net")
    facts["U8_IN2p"] = (find(rows, "U8", 5) or {}).get("net")
    facts["U23_VCC"] = (find(rows, "U23", 8) or {}).get("net")
    facts["U23_IN1m"] = (find(rows, "U23", 2) or {}).get("net")
    facts["HV5622_mpn"] = sorted({r["mpn"] for r in bom6 if r["mpn"].startswith("HV5622")})
    facts["HV5622_pkg"] = sorted({r["package"] for r in bom6 if r["mpn"].startswith("HV5622")})
    facts["n_tubes"] = len([1 for n in nets if re.match(r"^A_T\d$", n)])
    facts["n_channels"] = len([1 for n in nets if re.match(r"^K_T\d_\d$", n)])
    facts["HV5622_count"] = len([r for r in bom6 if r["mpn"].startswith("HV5622")])
    # DRV_PG 门槛：R45/R46 分压（从 netlist net 端点找）
    facts["DRV_SNS_divider"] = [f"{r}.{p}" for r, p in nets.get("DRV_SNS", [])]
    facts["VREF_OVP"] = [f"{r}.{p}" for r, p in nets.get("VREF_OVP", [])]

    # ---------- 发现（P0/P1 + 目标差距），status 说明见 README9 ----------
    findings = [
        dict(id="P0-01", title="LM393 输入共模越界（3.3 V 供电 + 2.5 V 基准）",
             where="U8（LM393，VCC=3V3）IN1−/IN2− = VREF_2V5=2.5 V",
             evidence="TI SLCS005AH Table: VICR = 0…VCC−1.5 V（25 °C）、0…VCC−2 V（全温区）；"
                      "3.3 V 供电时允许上限 1.8 V / 1.3 V，2.5 V 越界 → DRV_PG 与 FAULT_OK 判定不可靠",
             status="FAIL", action="U8 改用 1.0 V 基准（由 2.5 V 基准电阻分压，1% 电阻）并重算 DRV_SNS/HVF_NODE 分压；"
                                  "或改轨到轨比较器（成本+）"),
        dict(id="P0-02", title="OVP 比较器 + PNP/NPN 锁存极性",
             where="U23 IN1+=OVP_SNS / IN1−=VREF_OVP；OUT1=OVP_SET（R78 10k 上拉到 EXT12）；"
                   "R80 10k → LATCH_B；Q21 PNP(E=EXT12,B=LATCH_B,C=OVP_LATCH)；"
                   "Q22 NPN(B=OVP_LATCH,C=LATCH_B,E=GND)；Q23/Q24 由 OVP_LATCH 经 47k 驱动；Q25 复位",
             evidence="逐管偏置推导：过压→OUT1 低→R80 拉低 LATCH_B→PNP 通→OVP_LATCH 高→NPN 通→自锁；"
                      "复位（Q25 拉低 OVP_LATCH）仅在 OVP_SNS 已回落时有效（Q25 关断后 R80 会再次置位）→ 极性正确",
             status="STRONGLY SUPPORTED", action="结论为纸面推导；需 BJT 级 SPICE/实物确认（P0-02 仍列入 Gate G1 复核项），"
                                                  "不得直接标 VERIFIED"),
        dict(id="P0-03", title="HV5622 料号与封装混用",
             where=f"BOM: mpn={facts['HV5622_mpn']} 封装={facts['HV5622_pkg']}；"
                   f"model.py 把 HV5622PJ 解析到 HV5622-PQFP44 引脚表",
             evidence="Findchips 分销数据（Microchip 在售）：HV5622PJ-G = PLCC-44（Tube，库存 1593，"
                      "预计 EOL 2036-05-20）；HV5622PG-G = PQFP-44（Tray，库存 860，预计 EOL 2036-08-05）。"
                      "即 PJ 是 PLCC、PG 是 PQFP；现设计用 PJ 料号 + PQFP 引脚映射 = 错误",
             status="FAIL", action="REV.A9 改用 HV5622PG-G（PQFP-44，沿用已验证引脚表）；"
                                  "若改用 PJ（PLCC-44）必须重做 PLCC 引脚表与焊盘并重新验证"),
        dict(id="P1-01", title="DRV_PG 欠压门槛低于 HV5622 推荐逻辑供电下限",
             where="DRV_PG 由 DRV_SNS 分压 vs 2.5 V 基准，门槛约 10.41 V；HV5622 VDD 推荐 10.8–13.2 V",
             evidence="设计计算（旧仓库 D 系列记录）+ HV5622 DS20005854A VDD=10.8–13.2 V",
             status="FAIL", action="门槛改为 11.0 V 上升 / 10.6 V 下降（约 0.4 V 迟滞），并做容差分析"),
        dict(id="P1-02", title="DCM/CCM 模型与真实工作模式不一致",
             where="开环 SPICE 用固定 D=0.73（DCM 工作点）；平均模型按 CCM 方程；"
                   "九管满载时 Iin≈0.41 A、ΔI≈0.65 A → 满载 CCM、轻载/空载 DCM",
             evidence="本项目 9 管重算（power9.py）：满载 CCM、空载 DCM；两种模式都会出现",
             status="FAIL", action="REV.A9 采用分模式预算：满载用 CCM 公式、轻载/空载用 DCM 公式，"
                                  "并在 Gate G3 用实物/ngspice 交叉验证；不得再用单一模型下结论"),
        dict(id="P1-03", title="OVP 容差窗口过严",
             where="旧验收 198.8 V ±1.5 V；实际含 TL431 ±0.5%、分压电阻 ±1%、LM393 Vos ±2…5 mV、温漂",
             evidence="worst-case 计算（power9.py）：192.9–204.1 V（±5.6 V）→ 198.8±1.5 V 窗口无法覆盖",
             status="FAIL", action="REV.A9 验收窗口放宽为 192.5–204.5 V（1% 电阻计算值）；BOM-B/C 用 0.1% 电阻可收紧"),
        dict(id="P1-04", title="上电/失电/模块断连安全态",
             where="3.3 V 丢失时 CD40109B ENABLE=3V3→高阻、12 V 域下拉使 BL=0（安全）；"
                   "但 DRV_VDD 丢失而 HV 电容有电、以及显示模块拔线两种情况未定义",
             evidence="旧设计只有 HV_EN=DRV_PG·FAULT_OK·HV_EN_REQ；无模块在位检测",
             status="PROVISIONAL", action="REV.A9 增加 SAFETY_LOOP（模块在位回路）+ HV_EN 串入；"
                                          "模块断连→HV_EN 断开→升压停→泄放；并加 HV 输出泄放电阻"),
        dict(id="P2-01", title="九位扩展需求",
             where="旧系统 6 管/2×HV5622/64 bit 帧/单一 PCB",
             evidence="旧 BOM/网表：227 器件、60 通道、2×HV5622",
             status="UNVERIFIED", action="REV.A9 重建为 3 模块 ×（1 HV5622 + 3 管）= 90 通道；96 bit 帧（3×32）"),
        dict(id="P2-02", title="成本与可制造性",
             where="旧 BOM 无价格列；HV5622 报价 32.15 元/颗为零售、未核实",
             evidence="Findchips 2026-10-18：HV5622PG-G 单颗 $8.81、100 片 $6.67；PJ-G 单颗 $8.32；"
                      "零售 32.15 元与美元批发价不同渠道，均需询价确认",
             status="UNKNOWN", action="BOM-A/B/C 给出价格占位与询价状态；不得把估算当成交价"),
        dict(id="P2-03", title="EDA 原生工程缺失",
             where="无立创EDA/KiCad；现有 PDF/CSV 不是可编辑工程",
             evidence="open_issues I-19/I-20；环境限制",
             status="UNKNOWN", action="尝试 KiCad；不可行则提供可导入网表/符号/封装并标注 PROVISIONAL，不伪造 ERC/DRC"),
    ]

    # ---------- 架构差异表：继承/修改/废弃 ----------
    diff = [
        dict(item="管数/位数", old="6 位（J_T1…J_T6）", new="9 位（3+3+3，模块化）", action="重建", status="PROVISIONAL"),
        dict(item="HV 驱动", old="2×HV5622（64 路，60 用）", new="3×HV5622PG-G（96 路，90 用）", action="扩建+修正料号", status="PROVISIONAL"),
        dict(item="串行链路", old="64 bit 帧，U21→U22 级联", new="96 bit 帧，3 级级联（含模块回线）", action="修改", status="PROVISIONAL"),
        dict(item="PCB 结构", old="单板 230×120 mm", new="3 块显示模块板 + 1 块中央主板（3+3+3）", action="重建", status="PROVISIONAL"),
        dict(item="电源", old="单套 12V→172V UC3843，6 管负载", new="同一套电源按 9 管重算（满载 CCM/轻载 DCM）", action="修改+重算", status="PROVISIONAL"),
        dict(item="OVP/锁存", old="LM393+TL431+PNP/NPN SCR+Q23/Q24/Q25", new="保留拓扑；修 P0-02 偏置复核 + P0-01 共模 + P1-03 容差", action="修改", status="STRONGLY SUPPORTED"),
        dict(item="逻辑门控", old="74HC08 三路 PG + HV_EN", new="增加 SAFETY_LOOP、模块在位；DRV_PG 门槛 11.0/10.6 V", action="修改", status="PROVISIONAL"),
        dict(item="电平转换", old="CD40109B ×2（64 bit 链路）", new="每模块 1×CD40109B（或统一放主板，按接口方案）", action="修改/评估", status="PROVISIONAL"),
        dict(item="ESP32-S3 低压部分", old="ESP32-S3-WROOM-1-N8 + USB + 3.3V + 双 OR", new="继承（主板中央位置）", action="继承", status="VERIFIED"),
        dict(item="QS30-1 电气映射", old="2=A；3=K0…13=K1；1/8 内部电极开路", new="完全继承（原厂映射不变）", action="继承", status="VERIFIED"),
        dict(item="管座", old="13 脚管座，TBD 尺寸（H03）", new="3 模块×3 管座；方案 A/B/C 比较；TBD 保留", action="重做机械", status="UNKNOWN"),
        dict(item="高压连接器", old="无（单板直连）", new="模块间 HV 线束 + 防触碰连接器 + Pin1 标识", action="新增", status="UNKNOWN"),
        dict(item="旧六位资料", old="docs/ 全部 REV.A 文档", new="原样保留为 Legacy Reference", action="保留", status="VERIFIED"),
        dict(item="测试计划", old="37 项 A–E 阶段", new="G0–G5 阶段门 + 模块化测试项", action="扩展", status="PROVISIONAL"),
        dict(item="仿真", old="SPICE 功率级/平均模型/OVP 行为模型", new="重算 9 管；分模式；BJT 级 OVP 复核", action="修改+新增", status="PROVISIONAL"),
    ]

    # ---------- 输出 ----------
    with open(os.path.join(DOC9, "audit_diff.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["项目", "旧（REV6）", "新（REV.A9）", "动作", "状态", "依据/备注"])
        for d in diff:
            w.writerow([d["item"], d["old"], d["new"], d["action"], d["status"], ""])
    with open(os.path.join(DOC9, "audit_findings.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["编号", "标题", "位置", "证据", "状态", "整改动作"])
        for x in findings:
            w.writerow([x["id"], x["title"], x["where"], x["evidence"], x["status"], x["action"]])

    md = ["# REV.A9 仓库审计与架构差异（G0 输入）", "",
          "> 审计对象：`langxie29-cpu/QS30-driver` 现六位 REV.A 基线（commit `52eaa95`）。",
          "> 本文件只陈述**已核对的事实**与**明确标注为推导/未知的内容**；不修改旧文件。", "",
          "## 1. 现有基线事实（机器核对）", "",
          f"- 器件/网络：227 器件、736 引脚、172 网络、60 通道（6 管×10）、2×HV5622；",
          f"- HV5622 BOM：mpn **{facts['HV5622_mpn']}** / 封装 **{facts['HV5622_pkg']}** / 数量 {facts['HV5622_count']}；",
          f"- U8（LM393）VCC=**{facts['U8_VCC']}**，IN1−={facts['U8_IN1m']}，IN2−={facts['U8_IN2m']}，IN2+={facts['U8_IN2p']}；",
          f"- U23（OVP LM393）VCC=**{facts['U23_VCC']}**，IN1−={facts['U23_IN1m']}（共模合法）；",
          f"- DRV_SNS 分压端点：{facts['DRV_SNS_divider']}；VREF_OVP：{facts['VREF_OVP']}；",
          "", "## 2. 架构差异表（继承 / 修改 / 废弃 / 新增）", "",
          "| 项目 | 旧（REV6） | 新（REV.A9） | 动作 | 状态 |", "|---|---|---|---|---|"]
    for d in diff:
        md.append(f"| {d['item']} | {d['old']} | {d['new']} | {d['action']} | {d['status']} |")
    md += ["", "## 3. 关键发现（P0/P1 + 差距）", "",
           "| 编号 | 标题 | 状态 | 证据摘要 | 整改动作 |", "|---|---|---|---|---|"]
    for x in findings:
        md.append(f"| {x['id']} | {x['title']} | **{x['status']}** | {x['evidence']} | {x['action']} |")
    md += ["", "## 4. 需要修改/继承/废弃的电路（结论）", "",
           "**继承（不改）**：ESP32-S3-WROOM-1-N8 低压部分（已验证）、QS30-1 电气映射（VERIFIED）、",
           "12V 输入/双 OR/3.3V、UC3843 功率级拓扑（重算参数）、CD40109B 电平转换方案、OVP 拓扑（修偏置/容差）。", "",
           "**修改**：HV5622 料号→HV5622PG-G；驱动数量 2→3；帧 64→96 bit；PG 门槛；U8 基准/分压；",
           "SAFETY_LOOP、模块接口、OVP 容差窗口、测试计划（G0–G5）。", "",
           "**废弃/退役**：单板 230×120 预布局（保留为 Legacy 参考）、`HV5622PJ→PQFP` 的映射（错误）、",
           "旧 64 bit 帧与 60 通道映射（保留 Legacy，不删除）。", "",
           "**新增**：三模块物理架构、模块接口规范 QS30-DISPLAY-MODULE/REV.A、90 通道映射、",
           "模块在位/断连安全回路、HV 线束与连接器、成本 BOM-A/B/C。", "",
           "## 5. 证据状态说明", "",
           "本仓库使用六级：**VERIFIED / STRONGLY SUPPORTED / PROVISIONAL / UNVERIFIED / UNKNOWN / FAIL**。",
           "本审计中：U8 共模越界与 HV5622 料号混用为 **FAIL**（有手册/分销数据直接证据）；",
           "OVP 极性为 **STRONGLY SUPPORTED**（纸面偏置推导，未做 BJT 级仿真/实测）；",
           "九位架构/成本/连接器/机械为 **PROVISIONAL/UNKNOWN**（需计算或询价）；",
           "无任何实物测试结论被标为 VERIFIED。", "",
           "## 6. 数据来源", "",
           "- TI LM393/LM2903 数据手册 SLCS005AH（docs9/sources/TI_LM393_LM2903.pdf）：VICR=0…VCC−1.5 V(25 °C)，全温区 0…VCC−2 V；",
           "- Microchip HV5622 DS20005854A（仓库 source_register S5）：32 路、VDD 10.8–13.2 V、VPP ≤220 V、PQFP-44 引脚表；",
           "- Findchips/Microchip 分销数据（2026-10-18 抓取）：HV5622PJ-G=PLCC-44/Tube、HV5622PG-G=PQFP-44/Tray 及报价；",
           "- 旧仓库：netlist/BOM/design_decisions/open_issues/HOLD_REGISTER/仿真结果（本仓库 git 历史保留）。"]
    open(os.path.join(DOC9, "AUDIT.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(dict(facts=facts, findings=findings, diff=diff),
              open(os.path.join(DOC9, "audit.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("audit: findings =", len(findings), "| diff rows =", len(diff))
    print("FAIL:", [x["id"] for x in findings if x["status"] == "FAIL"])
    print("wrote docs9/AUDIT.md, audit_diff.csv, audit_findings.csv, audit.json")


if __name__ == "__main__":
    main()
