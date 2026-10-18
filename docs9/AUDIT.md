# REV.A9 仓库审计与架构差异（G0 输入）

> 审计对象：`langxie29-cpu/QS30-driver` 现六位 REV.A 基线（commit `52eaa95`）。
> 本文件只陈述**已核对的事实**与**明确标注为推导/未知的内容**；不修改旧文件。

## 1. 现有基线事实（机器核对）

- 器件/网络：227 器件、736 引脚、172 网络、60 通道（6 管×10）、2×HV5622；
- HV5622 BOM：mpn **['HV5622PJ']** / 封装 **['PQFP-44']** / 数量 2；
- U8（LM393）VCC=**3V3**，IN1−=VREF_2V5，IN2−=VREF_2V5，IN2+=HVF_NODE；
- U23（OVP LM393）VCC=**EXT12**，IN1−=VREF_OVP（共模合法）；
- DRV_SNS 分压端点：['U8.3', 'R45.2', 'R46.1', 'C37.1']；VREF_OVP：['U23.2', 'U24.1', 'U24.2', 'R74.2', 'C57.1']；

## 2. 架构差异表（继承 / 修改 / 废弃 / 新增）

| 项目 | 旧（REV6） | 新（REV.A9） | 动作 | 状态 |
|---|---|---|---|---|
| 管数/位数 | 6 位（J_T1…J_T6） | 9 位（3+3+3，模块化） | 重建 | PROVISIONAL |
| HV 驱动 | 2×HV5622（64 路，60 用） | 3×HV5622PG-G（96 路，90 用） | 扩建+修正料号 | PROVISIONAL |
| 串行链路 | 64 bit 帧，U21→U22 级联 | 96 bit 帧，3 级级联（含模块回线） | 修改 | PROVISIONAL |
| PCB 结构 | 单板 230×120 mm | 3 块显示模块板 + 1 块中央主板（3+3+3） | 重建 | PROVISIONAL |
| 电源 | 单套 12V→172V UC3843，6 管负载 | 同一套电源按 9 管重算（满载 CCM/轻载 DCM） | 修改+重算 | PROVISIONAL |
| OVP/锁存 | LM393+TL431+PNP/NPN SCR+Q23/Q24/Q25 | 保留拓扑；修 P0-02 偏置复核 + P0-01 共模 + P1-03 容差 | 修改 | STRONGLY SUPPORTED |
| 逻辑门控 | 74HC08 三路 PG + HV_EN | 增加 SAFETY_LOOP、模块在位；DRV_PG 门槛 11.0/10.6 V | 修改 | PROVISIONAL |
| 电平转换 | CD40109B ×2（64 bit 链路） | 每模块 1×CD40109B（或统一放主板，按接口方案） | 修改/评估 | PROVISIONAL |
| ESP32-S3 低压部分 | ESP32-S3-WROOM-1-N8 + USB + 3.3V + 双 OR | 继承（主板中央位置） | 继承 | VERIFIED |
| QS30-1 电气映射 | 2=A；3=K0…13=K1；1/8 内部电极开路 | 完全继承（原厂映射不变） | 继承 | VERIFIED |
| 管座 | 13 脚管座，TBD 尺寸（H03） | 3 模块×3 管座；方案 A/B/C 比较；TBD 保留 | 重做机械 | UNKNOWN |
| 高压连接器 | 无（单板直连） | 模块间 HV 线束 + 防触碰连接器 + Pin1 标识 | 新增 | UNKNOWN |
| 旧六位资料 | docs/ 全部 REV.A 文档 | 原样保留为 Legacy Reference | 保留 | VERIFIED |
| 测试计划 | 37 项 A–E 阶段 | G0–G5 阶段门 + 模块化测试项 | 扩展 | PROVISIONAL |
| 仿真 | SPICE 功率级/平均模型/OVP 行为模型 | 重算 9 管；分模式；BJT 级 OVP 复核 | 修改+新增 | PROVISIONAL |

## 3. 关键发现（P0/P1 + 差距）

| 编号 | 标题 | 状态 | 证据摘要 | 整改动作 |
|---|---|---|---|---|
| P0-01 | LM393 输入共模越界（3.3 V 供电 + 2.5 V 基准） | **FAIL** | TI SLCS005AH Table: VICR = 0…VCC−1.5 V（25 °C）、0…VCC−2 V（全温区）；3.3 V 供电时允许上限 1.8 V / 1.3 V，2.5 V 越界 → DRV_PG 与 FAULT_OK 判定不可靠 | U8 改用 1.0 V 基准（由 2.5 V 基准电阻分压，1% 电阻）并重算 DRV_SNS/HVF_NODE 分压；或改轨到轨比较器（成本+） |
| P0-02 | OVP 比较器 + PNP/NPN 锁存极性 | **STRONGLY SUPPORTED** | 逐管偏置推导：过压→OUT1 低→R80 拉低 LATCH_B→PNP 通→OVP_LATCH 高→NPN 通→自锁；复位（Q25 拉低 OVP_LATCH）仅在 OVP_SNS 已回落时有效（Q25 关断后 R80 会再次置位）→ 极性正确 | 结论为纸面推导；需 BJT 级 SPICE/实物确认（P0-02 仍列入 Gate G1 复核项），不得直接标 VERIFIED |
| P0-03 | HV5622 料号与封装混用 | **FAIL** | Findchips 分销数据（Microchip 在售）：HV5622PJ-G = PLCC-44（Tube，库存 1593，预计 EOL 2036-05-20）；HV5622PG-G = PQFP-44（Tray，库存 860，预计 EOL 2036-08-05）。即 PJ 是 PLCC、PG 是 PQFP；现设计用 PJ 料号 + PQFP 引脚映射 = 错误 | REV.A9 改用 HV5622PG-G（PQFP-44，沿用已验证引脚表）；若改用 PJ（PLCC-44）必须重做 PLCC 引脚表与焊盘并重新验证 |
| P1-01 | DRV_PG 欠压门槛低于 HV5622 推荐逻辑供电下限 | **FAIL** | 设计计算（旧仓库 D 系列记录）+ HV5622 DS20005854A VDD=10.8–13.2 V | 门槛改为 11.0 V 上升 / 10.6 V 下降（约 0.4 V 迟滞），并做容差分析 |
| P1-02 | DCM/CCM 模型与真实工作模式不一致 | **FAIL** | 本项目 9 管重算（power9.py）：满载 CCM、空载 DCM；两种模式都会出现 | REV.A9 采用分模式预算：满载用 CCM 公式、轻载/空载用 DCM 公式，并在 Gate G3 用实物/ngspice 交叉验证；不得再用单一模型下结论 |
| P1-03 | OVP 容差窗口过严 | **FAIL** | worst-case 计算（power9.py）：192.9–204.1 V（±5.6 V）→ 198.8±1.5 V 窗口无法覆盖 | REV.A9 验收窗口放宽为 192.5–204.5 V（1% 电阻计算值）；BOM-B/C 用 0.1% 电阻可收紧 |
| P1-04 | 上电/失电/模块断连安全态 | **PROVISIONAL** | 旧设计只有 HV_EN=DRV_PG·FAULT_OK·HV_EN_REQ；无模块在位检测 | REV.A9 增加 SAFETY_LOOP（模块在位回路）+ HV_EN 串入；模块断连→HV_EN 断开→升压停→泄放；并加 HV 输出泄放电阻 |
| P2-01 | 九位扩展需求 | **UNVERIFIED** | 旧 BOM/网表：227 器件、60 通道、2×HV5622 | REV.A9 重建为 3 模块 ×（1 HV5622 + 3 管）= 90 通道；96 bit 帧（3×32） |
| P2-02 | 成本与可制造性 | **UNKNOWN** | Findchips 2026-10-18：HV5622PG-G 单颗 $8.81、100 片 $6.67；PJ-G 单颗 $8.32；零售 32.15 元与美元批发价不同渠道，均需询价确认 | BOM-A/B/C 给出价格占位与询价状态；不得把估算当成交价 |
| P2-03 | EDA 原生工程缺失 | **UNKNOWN** | open_issues I-19/I-20；环境限制 | 尝试 KiCad；不可行则提供可导入网表/符号/封装并标注 PROVISIONAL，不伪造 ERC/DRC |

## 4. 需要修改/继承/废弃的电路（结论）

**继承（不改）**：ESP32-S3-WROOM-1-N8 低压部分（已验证）、QS30-1 电气映射（VERIFIED）、
12V 输入/双 OR/3.3V、UC3843 功率级拓扑（重算参数）、CD40109B 电平转换方案、OVP 拓扑（修偏置/容差）。

**修改**：HV5622 料号→HV5622PG-G；驱动数量 2→3；帧 64→96 bit；PG 门槛；U8 基准/分压；
SAFETY_LOOP、模块接口、OVP 容差窗口、测试计划（G0–G5）。

**废弃/退役**：单板 230×120 预布局（保留为 Legacy 参考）、`HV5622PJ→PQFP` 的映射（错误）、
旧 64 bit 帧与 60 通道映射（保留 Legacy，不删除）。

**新增**：三模块物理架构、模块接口规范 QS30-DISPLAY-MODULE/REV.A、90 通道映射、
模块在位/断连安全回路、HV 线束与连接器、成本 BOM-A/B/C。

## 5. 证据状态说明

本仓库使用六级：**VERIFIED / STRONGLY SUPPORTED / PROVISIONAL / UNVERIFIED / UNKNOWN / FAIL**。
本审计中：U8 共模越界与 HV5622 料号混用为 **FAIL**（有手册/分销数据直接证据）；
OVP 极性为 **STRONGLY SUPPORTED**（纸面偏置推导，未做 BJT 级仿真/实测）；
九位架构/成本/连接器/机械为 **PROVISIONAL/UNKNOWN**（需计算或询价）；
无任何实物测试结论被标为 VERIFIED。

## 6. 数据来源

- TI LM393/LM2903 数据手册 SLCS005AH（docs9/sources/TI_LM393_LM2903.pdf）：VICR=0…VCC−1.5 V(25 °C)，全温区 0…VCC−2 V；
- Microchip HV5622 DS20005854A（仓库 source_register S5）：32 路、VDD 10.8–13.2 V、VPP ≤220 V、PQFP-44 引脚表；
- Findchips/Microchip 分销数据（2026-10-18 抓取）：HV5622PJ-G=PLCC-44/Tube、HV5622PG-G=PQFP-44/Tray 及报价；
- 旧仓库：netlist/BOM/design_decisions/open_issues/HOLD_REGISTER/仿真结果（本仓库 git 历史保留）。
