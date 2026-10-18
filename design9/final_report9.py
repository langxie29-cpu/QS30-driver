# -*- coding: utf-8 -*-
"""REV.A9 最终报告（A–G）+ 根文档（HOLD/open_issues/source_register/decisions/changelog/legacy）。

只读 docs9/ 与旧仓库机器结果，不重复计算；输出到根目录与 docs9/。
运行：python design9/final_report9.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC9 = os.path.join(ROOT, "docs9")


def j(name):
    return json.load(open(os.path.join(DOC9, name), encoding="utf-8"))


def main():
    audit = j("audit.json")
    des = j("design9_summary.json")
    power = j("power9.json")
    cost = j("cost9.json")
    findings = {x["id"]: x for x in audit["findings"]}
    fails = [k for k, v in findings.items() if v["status"] == "FAIL"]
    ok = power["ok"]

    # ---------------- A–G 报告 ----------------
    md = ["""# QS30-9 / REV.A 最终报告（A–G）

日期：2026-10-18 ｜ 基线：九位模块化（3+3+3）｜ 旧六位 REV.A 保留为 Legacy（commit 52eaa95）

## A. 当前实际完成了什么

| 项目 | 状态 | 证据 |
|---|---|---|
| 仓库审计 + 架构差异表（继承/修改/废弃/新增） | 完成 | `docs9/AUDIT.md`、`audit_diff.csv`、`audit_findings.csv` |
| 九位三模块架构（L/C/R 显示模块 + 中央主板） | 完成（软件侧） | `docs9/ARCHITECTURE.md`、网表 |
| P0-01 LM393 共模越界修复（U8 改 1.0 V 基准 + 分压重算） | 已修复（ERC 通过） | `audit_findings.csv`、`docs9/ERC9.md` E19/E20 |
| P0-02 OVP 极性/锁存复核 | 纸面推导 STRONGLY SUPPORTED，BJT 级仿真/实测未做 | findings P0-02 |
| P0-03 HV5622 料号/封装修复（PJ→PG，PQFP-44） | 已修复 | ERC E08、BOM9 |
| P1-01 DRV_PG 门槛 10.41→11.2 V（迟滞 0.34 V） | 已修复 | `docs9/POWER9.md` §6 |
| P1-02 DCM/CCM 模型不一致 | 已定量重算（典型 CCM 边界、轻载 DCM），台架未验证 | POWER9 §1 |
| P1-03 OVP 容差 | 已 worst-case 重算，窗口改 192.5–204.5 V | POWER9 §3 |
| P1-04 上下电/模块断连安全 | 增加 SAFETY_LOOP + Q4 高侧关断；台架未验证 | ARCHITECTURE §2 |
| 九管电源重算（电流/电感/应力/纹波/泄放/控制器评估） | 完成计算 | POWER9 |
| 驱动方案比较 + BOM-A/B/C + 成本框架 | 完成（价格未知处如实标注） | `DRIVER_COMPARE.md`、`COST9.md`、`bom9/` |
| 接口规范 QS30-DISPLAY-MODULE/REV.A + 96 bit 帧 + 回线 | 完成（PROVISIONAL，位序待实测） | `interface9.csv`、`channel_map9.csv` |
| 机械尺寸计算（100×100 档位评审） | 完成计算，结论：三管共板不可行/需支架或加大档位 | `MECH9.md` |
| 网表级 ERC | **36/36 PASS** | `docs9/ERC9.md` |
| G0–G5 阶段门 | 完成定义，G0 进行中 | `docs9/GATES.md` |
| EDA 原生工程/ERC/DRC | **未实现**（环境无 KiCad/立创EDA） | `docs9/EDA_STATUS.md` |
| 旧六位资料 | 原样保留为 Legacy Reference | `legacy/REV6/README.md` |

## B. 九位模块化架构是什么

- **物理**：左显示模块（3 管 + 1 HV5622）+ 中央主板（ESP32-S3、12V 输入、3.3/5V、升压+OVP、1 HV5622 + 中心 3 管）+ 右显示模块（3 管 + 1 HV5622）；左右板同 Gerber/BOM。
- **驱动**：3×HV5622PG-G（PQFP-44），每片 30 路使用、2 路备用 → **90/96 路**，静态显示无扫描。
- **数据链**：MCU → L → C → R 的 96 bit 级联；L 的 DATA OUT 经电缆回主板再进 C（明确的物理回线）；CLK/LAT/BL 3.3 V 并行分配，模块内 CD40109B 转 12 V。
- **安全（不依赖固件）**：`HV_EN = (DRV_PG·FAULT_OK)·SAFETY_OK·HV_EN_REQ` → Q4 高侧关断；SAFETY_LOOP 在 3 模块内串联，任一模块拔线 → SAFETY_OK=0 → HV_EN=0；3.3 V 丢失 → 模块 CD40109B 高阻 + 12 V 下拉 → BL=0 全关；OVP 锁存拉低 COMP；主板 + 每模块本地泄放。
- **电源**：一套 12V→172V UC3843；九管典型 20.25 mA/3.49 W，最大 27 mA/4.65 W；12 V 输入 ≈0.35/0.46 A。

## C. 与原六位方案相比成本变化

| 项 | 六位（旧） | 九位（REV.A9） | 变化 |
|---|---|---|---|
| HV5622 | 2 颗（PJ 料号/错误映射） | 3 颗 PG-G | +1 颗；按用户报价 32.15 元 → **+32.15 元（UNVERIFIED）** |
| 管 | 6（已有） | 9（已有） | 历史成本 160 元，**不计入本次现金支出** |
| PCB | 1 块 230×120 | 主板 1 + 显示板 3（左右同板） | 板数/面积增加，**未询价（UNKNOWN）** |
| 连接器/线束 | 无 | LV 16P×4 + HV 2P×6 + 线束 | 新增，**未询价** |
| 分立元件 | 227 器件 | 187 器件（3 模块 + 主板，不含外壳/线束） | 器件数少于旧（因复用模块） |
| 已知现金支出 | — | **96.45 元（3×HV5622）** | 其余全部待询价 |

**结论（诚实）**：无法给出完整成本对比——除 HV5622 与已拥有的辉光管外，PCB、连接器、线束、无源件均无有效报价。已知增量是 +1 颗 HV5622（约 +32 元，UNVERIFIED）；模块化会增加连接器/线束/板费，但左右板复用摊薄打样。**任何"总成本 X 元"的说法都必须等询价后才能给出。**

## D. 哪些已独立验证 / 哪些仍有风险

**已执行/机器可验证**：ERC9 36/36（规则级）；电源/OVP/泄放/门控为**解析计算**；旧六位的 SPICE/行为模型证据仍对 REV.A9 的**拓扑部分**有参考价值（UC3843 功率级、OVP 锁存拓扑、CD40109B 电平转换、QS30-1 映射）。

**风险/未验证（不得当作已验证）**：
- OVP 极性仅纸面偏置推导（STRONGLY SUPPORTED），无 BJT 级 SPICE、无实物；
- 90 路位序为**公式假设**（PROVISIONAL），必须 H04 级 walking-one 实测；
- 管座机械尺寸 TBD（H03）→ PCB 尺寸/封装不能冻结；
- HV 连接器 DC 额定/防触碰未核实（UNKNOWN）；
- 模块断连安全回路仅逻辑检查，未做故障注入；
- 九管 CW/CCM 边界与轻载稳定性未台架验证；
- 原生 EDA/ERC/DRC 未执行；Gerber 未生成。

## E. 现在能否绘制 / 打样 / 装配 / 上电？

| 能力 | 结论 |
|---|---|
| 绘制（原生 EDA 工程） | **不能**：无 KiCad/立创EDA；仅提供逐引脚网表 + 实验符号库（未验证） |
| 打样（PCB） | **不能**：管座封装 TBD、连接器未选型、EDA 工程缺失 |
| 装配 | **不能**：无 BOM 完整报价/供货、无 PCB |
| 上电（九位） | **不能**：无实物装配；且 H02–H08 安全测试未做 |

因此本项目的正确状态是：**软件侧架构/计算/审计完成，硬件侧未开始；禁止投板/下单/Gerber。**

## F. 最少还需要购买哪些物料（构建九位 REV.A9 样机）

| 物料 | 数量 | 说明 |
|---|---|---|
| HV5622PG-G（PQFP-44） | 3（+1 备件建议） | 需询价/验真；**不要买 PJ（PLCC）除非重做引脚表** |
| 13 脚 QS30-1 管座 | 9（+2 备） | 需实测尺寸（H03） |
| PCB | 主板 1 + 显示板 3（左右同板，可拼板） | 需先冻结封装/接口/机械 |
| LV 16P 带锁扣 IDC 连接器 + 线束 | 2 套（左右） | 3.3 V/12 V 逻辑 |
| HV 2P 防触碰连接器 + 线束 | 2 套 | **必须 ≥300 V DC 额定**（待选型核实） |
| 无源件/半导体 | 见 bom9/BOM9_B.csv | 价格待询价 |
| 12 V 电源、测试假负载、差分探头（≥1 kV） | 各 1 | 高压台架 G3 必需；**不得用未验证 PCB 直接接 170 V** |

## G. 下一阶段最值得执行的三个动作

1. **G0 评审**：确认"三板（主板含中心 3 管）+ 左右同板"架构、BOM-B 作为推荐档、以及是否接受 192.5–204.5 V 的 OVP 验收窗口（或改用 0.1% 电阻收紧）。
2. **冻结机械输入**：购买 13 脚管座样件并实测（H03），确定三管间距与固定方式（支架 vs 共板）；这一步决定 PCB 尺寸与打样档位。
3. **争取原生 EDA + 高压台架**：安装 KiCad（或立创EDA）重建工程并跑原生 ERC/DRC；同时准备隔离高压台架（含泄放/差分探头），先做 G1/G3，再谈整机上电。

---

## 证据状态汇总（六级）

| 状态 | 项 |
|---|---|
| VERIFIED | QS30-1 电气映射（原厂）、HV5622 PQFP-44 引脚表（DS20005854A）、ESP32/低压电源沿用旧验证 |
| STRONGLY SUPPORTED | OVP PNP/NPN 锁存极性（偏置推导） |
| PROVISIONAL | 九位架构、模块接口、96 bit 位序、BOM 结构、机械计算、ERC9 规则检查 |
| UNVERIFIED | 成本（除 HV5622 外无报价）、模块断连安全、轻载 DCM 稳定性 |
| UNKNOWN | 管座尺寸、HV 连接器 DC 额定、HV5622 真实价格/库存/真伪、原生 EDA 状态 |
| FAIL（已修/待验） | P0-01、P0-03、P1-01、P1-02、P1-03（软件侧已修，硬件侧待验证） |
"""]
    open(os.path.join(DOC9, "FINAL_REPORT9.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---------------- 根文档 ----------------
    open(os.path.join(ROOT, "HOLD_REGISTER9.md"), "w", encoding="utf-8").write("""# HOLD 登记（REV.A9 九位模块化基线）

由 REV.A9 重构引入的未冻结项。旧六位 HOLD Register 保留在 `HOLD_REGISTER.md`（Legacy）。

| ID | 项目 | 关闭条件 | 证据文件 | 状态 |
|---|---|---|---|---|
| H9-01 | 架构冻结（三板 vs 四板、BOM-B） | 用户评审 G0 | docs9/GATES.md | OPEN |
| H9-02 | HV5622 真实价格/库存/真伪 | 询价 + 收货验真 | bom9/BOM9_B.csv | OPEN |
| H9-03 | 13 脚管座机械尺寸 | 实测 10 项（H03 模板） | docs/evidence/H03_*.csv | OPEN |
| H9-04 | OVP 极性器件级验证 | BJT 级 SPICE + 台架 | docs9/POWER9.md（待补） | OPEN |
| H9-05 | 90 路位序 | walking-one 实测回填 | docs9/channel_map9.csv | OPEN |
| H9-06 | 原生 EDA 工程 + ERC/DRC | KiCad/立创EDA 工程 | docs9/EDA_STATUS.md | OPEN |
| H9-07 | HV 连接器额定/防触碰 | 选型手册 + 结构 | docs9/interface9.csv | OPEN |
| H9-08 | PCB 尺寸/机械冻结 | H9-03 后 | docs9/MECH9.md | OPEN |
| H9-09 | 高压台架（G3） | 实测 172 V/OVP/泄放/浪涌 | H06 证据 CSV | OPEN |
| H9-10 | 模块断连安全回路 | 故障注入实测 | docs9/ARCHITECTURE.md | OPEN |
| H9-11 | 轻载 DCM 稳定性 | G3 台架三点测试 | docs9/POWER9.md | OPEN |
| H9-12 | 成本/PCB 报价 | 询价单 | docs9/COST9.md | OPEN |
""")

    open(os.path.join(ROOT, "open_issues9.md"), "w", encoding="utf-8").write("""# 问题登记（REV.A9）

| ID | 问题 | 等级 | 状态 | 说明 |
|---|---|---|---|---|
| I9-01 | LM393 3.3V 供电共模越界（旧设计） | P0 | 已修（软件） | U8 改 1.0V 基准（ERC E19/E20），硬件待验 |
| I9-02 | HV5622 PJ/PG 封装混用（旧设计） | P0 | 已修 | 统一 HV5622PG-G（PQFP-44） |
| I9-03 | OVP 极性仅纸面推导 | P0 | 待验证 | 需 BJT 级 SPICE/实测（H9-04） |
| I9-04 | DRV_PG 门槛低于 10.8 V（旧设计） | P1 | 已修 | 11.2 V ± 迟滞 0.34 V |
| I9-05 | DCM/CCM 模型混用（旧仓库） | P1 | 已重算 | 典型 CCM 边界/轻载 DCM（POWER9 §1） |
| I9-06 | OVP 容差窗口过严 | P1 | 已修 | 192.5–204.5 V（1% 电阻） |
| I9-07 | 上下电/模块断连安全态 | P1 | 设计已加，未验证 | SAFETY_LOOP + Q4 高侧关断 |
| I9-08 | 90 路位序未实测 | P1 | OPEN | PROVISIONAL 公式 |
| I9-09 | 管座尺寸 TBD | P1 | OPEN | 阻塞 PCB |
| I9-10 | HV 连接器额定/防触碰 | P1 | OPEN | UNKNOWN |
| I9-11 | 原生 EDA 缺失 | P1 | OPEN | 无 KiCad/立创EDA |
| I9-12 | 成本无有效报价 | P2 | OPEN | 仅 HV5622 有用户报价 |
""")

    open(os.path.join(ROOT, "source_register9.md"), "w", encoding="utf-8").write("""# 来源登记（REV.A9）

| ID | 来源 | 用途 | 证据等级 |
|---|---|---|---|
| S9-01 | TI《LM393/LM2903》SLCS005AH（本地 docs9/sources/TI_LM393_LM2903.pdf） | VICR = 0…VCC−1.5 V(25 °C)、全温区 0…VCC−2 V | VERIFIED |
| S9-02 | Microchip HV5622 DS20005854A（旧仓库 source_register S5） | 32 路、VDD 10.8–13.2 V、VPP ≤220 V、PQFP-44 引脚表 | VERIFIED（引脚表） |
| S9-03 | Findchips/Microchip 分销数据（2026-10-18 抓取） | HV5622PJ-G=PLCC-44/Tube、HV5622PG-G=PQFP-44/Tray、库存/报价 | STRONGLY SUPPORTED（分销聚合，非原厂） |
| S9-04 | 旧仓库仿真（SPICE/平均模型/行为模型 S1–S10） | 功率级/OVP/泄放参考（拓扑级） | 旧证据，未在 REV.A9 重新执行 |
| S9-05 | 用户提供 | 9 只 QS30-1 已有；HV5622 零售 32.15 元；六位管座约 15 元 | UNVERIFIED |
| S9-06 | 本仓库计算 | POWER9/COST9/MECH9/ERC9 | PROVISIONAL（计算/规则） |
""")

    open(os.path.join(ROOT, "design_decisions9.md"), "w", encoding="utf-8").write("""# 设计决策（REV.A9）

| ID | 决策 | 理由 | 状态 |
|---|---|---|---|
| D9-01 | 采用 3+3+3 三模块（左右同板 + 中央主板含中心 3 管） | 复用打样、中心控制集中、接口统一 | PROVISIONAL |
| D9-02 | 驱动保留 HV5622（3×PG-G），不用 74HC595+分立 | 焊点/面积/维修点少一个数量级；分立需逐管高压验证 | PROVISIONAL（价格待询） |
| D9-03 | 串行 96 bit 级联（MCU→L→C→R，含回线），不采用独立数据线 | 连接器引脚少、时序简单；静态显示无需分组刷新 | PROVISIONAL（位序待实测） |
| D9-04 | 每模块 1×CD40109B 本地电平转换 | 3.3 V 丢失时模块本地 BL=0 全关；电缆只走 3.3 V 逻辑 | PROVISIONAL |
| D9-05 | HV5622 统一 PG-G（PQFP-44） | 已验证引脚表；PJ=PLCC 需重做引脚/焊盘 | VERIFIED（料号事实） |
| D9-06 | U8 比较器改 1.0 V 基准 | LM393 3.3 V 供电共模上限 1.3 V（全温区） | PROVISIONAL（待实测） |
| D9-07 | DRV_PG 11.2 V、迟滞 ~0.34 V | 高于 HV5622 10.8 V 下限且覆盖 12 V−5% 输入 | PROVISIONAL |
| D9-08 | OVP 验收窗口 192.5–204.5 V | 1% 电阻 + 0.5% 基准 + Vos worst-case | PROVISIONAL |
| D9-09 | SAFETY_LOOP 模块在位检测 | 拔线 → HV_EN=0；不依赖固件 | PROVISIONAL（待故障注入） |
| D9-10 | 高压连接器独立于 IDC，必须 ≥300 V 额定、防触碰 | 禁止 170 V 进普通 IDC/杜邦 | OPEN（选型） |
| D9-11 | 三管不共板（建议支架/面板），或 100×150 档位 | 100 mm 宽放不下 3×30.2 + 间隙 + 高压爬电 | PROVISIONAL（待 H03） |
| D9-12 | 保留 UC3843 + 现有功率级拓扑 | 3.5–4.7 W/14× 升压，现有验证可复用；替代控制器需新验证 | PROVISIONAL |
| D9-13 | 旧六位资料原样保留为 Legacy | 可追溯，不删旧证据 | VERIFIED |
""")

    open(os.path.join(ROOT, "REV_A9_CHANGELOG.md"), "w", encoding="utf-8").write("""# REV.A9 变更记录（九位模块化重构）

## r9.1 — 2026-10-18（初始重构）

- 新增 docs9/：审计、架构、网表、90 路映射、接口、ERC9（36/36）、BOM-A/B/C、成本、机械、
  驱动比较、G0–G5、EDA 状态、最终 A–G 报告；
- 旧六位 REV.A 保留为 Legacy（commit 52eaa95，README 说明）；
- 修复：P0-03（HV5622 料号）、P0-01（LM393 共模，U8 改 1.0 V 基准）、
  P1-01（DRV_PG 11.2 V）、P1-03（OVP 窗口 192.5–204.5 V）、P1-02（DCM/CCM 分模式重算）；
- 新增 SAFETY_LOOP、模块接口、96 bit 帧、3×HV5622；
- 未实现：原生 EDA/ERC/DRC、Gerber、实物验证；禁止投板/下单。

> 本变更未做 force push / reset --hard；旧提交与文件保留。
""")

    legacy_dir = os.path.join(ROOT, "legacy", "REV6")
    os.makedirs(legacy_dir, exist_ok=True)
    open(os.path.join(legacy_dir, "README.md"), "w", encoding="utf-8").write("""# Legacy：六位 REV.A（REV6）

本目录只放说明；旧六位设计的全部文件仍在原路径（README/design/docs/sim/netlist/bom/symbols），
对应 git 提交 `52eaa95`。

- 旧基线：6 位、2×HV5622（PQFP 映射、料号 PJ 为错误）、60 通道、单板 230×120；
- 旧证据：SPICE、平均模型、OVP 行为模型、ERC 19 项、DRC 14 项、审查包 29 页；
- 新基线（REV.A9）在 `docs9/`，两者并存，不删除旧证据。

已知旧问题（在 REV.A9 修正）：LM393 3.3 V 共模（U8）、HV5622 PJ/PG 混用、DRV_PG 10.41 V、
OVP 窗口 ±1.5 V 过严、DCM/CCM 模型混用。
""")
    print("wrote docs9/FINAL_REPORT9.md + 根文档（HOLD/open_issues/source_register/decisions/changelog/legacy）")


if __name__ == "__main__":
    main()
