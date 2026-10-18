# QS30-6 REV.A 变更记录

格式：每次设计变更记录 **变更 / 理由 / 证据 / 影响面**。
`REV.A` 为本次实施基线；`REV.A r1` = 2026-10-18 首次由交接文件（修订01）转入工程实施。

---

## REV.A r1 — 2026-10-18（首次实施）

### 1. 主控、显示与接口（继承并核实）

| 变更 | 理由 | 证据 |
|---|---|---|
| 保持 U_MCU = ESP32-S3-WROOM-1-N8（无 PSRAM） | 交接决定；满足本地计数 + Wi-Fi | S1 表 1-1 变体；S2 焊盘表交叉核对 |
| 焊接焊盘号 1–41 全部按原厂表登记；GPIO/焊盘/网络对照进入自动检查 | 防止符号-封装-固件不一致 | `docs/erc_report.md` ERC-04 |
| 新增 GPIO18 = OVP_RST（过压锁存受控复位） | 独立 OVP 需要"受控恢复"，原交接未分配复位脚 | D-10 |
| USB-C：CC1/CC2 各 5.1 kΩ、D+/D− 22 Ω、USBLC6-2SC6、TXD0 499 Ω、ADC 0.1 µF | 原交接只给原则，未给值；采用 Espressif 官方建议值 | S1b / S2 / S12 |
| GPIO3/45 不接外设；GPIO46 10 kΩ 下拉；GPIO0 10 kΩ 上拉 | Espressif strapping 要求 | S1b |

### 2. 高压驱动（修正旧方案）

| 变更 | 理由 | 证据 |
|---|---|---|
| **HV5622 由 3 片（96 路/96 bit）改为 2 片（64 路/64 bit）** | 原厂数据手册每片 32 路输出；60 路需求 2 片即足 | S5 Table 2-1 + 功能框图 |
| 帧长 96 bit → 64 bit；备用通道 CH60–63 输出不接 | 同上 | D-03 / `channel_mapping.csv` |
| HV5622 POL 直接接 DRV_VDD（不接 MCU、不悬空） | POL=L 且 BL=L 时器件"All On"，属危险态 | S5 Table 3-2 |
| DRV_BL 在 12 V 域 10 kΩ 下拉；DRV_DIN/CLK/LAT/HV_EN_REQ 同样下拉 | 3.3 V 失电/高阻时保持确定低电平 | D-06 |
| 电平转换 U3/U4 = CD40109B，VCC=3V3、VDD=DRV_VDD、ENABLE 接 3V3 | 3.3 V 直接驱动 12 V 逻辑不成立：HV5622 VIH ≥ VDD−2 V | S5 / S13 |
| 明确 SPI ≤200 kHz（起始 100 kHz） | CD40109B 在 3.3 V/12 V 下延迟按 ≤600 ns 暂估 | S13 动态参数 |
| 新增 60 路通道映射表 + walking-one 验证要求 | 位序不得假设；J_T4 跨器件边界 | D-07 |

### 3. 高压电源与保护（新增/修正）

| 变更 | 理由 | 证据 |
|---|---|---|
| 工作点：Ea = **172.18 V**（2×750 k/22.1 k），Ra = 20 kΩ（2×10 kΩ/2 W） | 原厂推荐 Ea 170 V/Ra 20 kΩ；用标准阻值逼近 | S6 基本参数 + 推荐表 |
| 新增 **独立硬件 OVP：LM393 + TL431 2.5 V，触发 198.8 V**，分立 SCR 锁存 | 交接要求 OVP 不得依赖 MCU；原交接未给阈值 | S14/S17 + 计算 |
| OVP 触发后：Q23 拉低 UC3843 COMP（占空比→0）、Q24 拉低 HV_FAULT_N | 关断路径必须独立于固件 | 仿真 S7/S8 |
| 新增 GPIO18 → Q25 受控复位锁存（HV 降至阈值以下才释放） | 交接要求"故障锁存与受控恢复" | S7/S8 仿真 |
| 泄放电阻 **440 kΩ → 200 kΩ（2×100 kΩ）** | 原设计 172→50 V 需 ≈10.7 s，过长 | 仿真 S9：3.84 s |
| **L20 标记 Isat ≥5 A**（220 µH 不变） | 仿真启动浪涌 2.9–3.1 A，3 A 器件裕量不足 | S1–S6 仿真 |
| 新增 HV 输入高边开关 Q26/Q27（HV_EN 门控，默认关断） | 交接要求"默认关闭 + 硬件故障门控" | D-09 |
| 新增 EXT12_PG=10.80 V / 3V3_PG=3.107 V / DRV_PG=10.41 V 三路电源良好 + 74HC08 门控 | MCU 只能请求，必须硬件组合 | D-09 |
| EXT12_PG 门限由 11.0 V 修正为 **10.80 V** | 11.0 V 会使 12 V−5% 输入（EXT12≈10.9 V）误禁高压 | 计算 |
| 升压软启动：COMP 22 µF / 参考斜坡 150 ms | 抑制启动过冲（仿真 +4.97%，未触 OVP） | 仿真 S1 |
| RCD 钳位（UF4007 + 10 nF/630 V + 100 kΩ/2 W） | 抑制开关节点振铃 | 设计 |
| 阳极电阻改为 **2×10 kΩ/2 W 串联**（每管） | 单管短路耗散 1.48 W，需分担与降额 | 计算 |

### 4. 低压电源（细化）

| 变更 | 理由 | 证据 |
|---|---|---|
| 12 V→5.08 V：TPS54202（SOT-23-6，Vref 0.596 V，R=100 k/13.3 k） | 4.5–28 V 输入、2 A、500 kHz、5 ms 软启动 | S8 |
| 5 V→3.315 V：SY8089A（2.7–5.5 V、2 A、1 MHz，R=100 k/22.1 k） | 肖特基 OR 后 5V_SYS 最低 ≈4.4 V，需低压输入能力 | S10 |
| 5V_SYS = 双 SS14 肖特基 OR（EXT5 / VBUS），反向阻断 | 交接要求；参考实现零不确定，理想二极管 IC 作为后续替换选项 | D-08 |
| DRV_VDD = DMP3098L 高边开关，栅极 100 kΩ 上拉 → 默认关断 | 保证驱动逻辑在允许前不供电 | D-09 |
| 输入保护：PPTC 1.5 A + SMBJ16A TVS + SS54 反接 | 12 V 输入基本保护 | 设计 |
| 明确 USB 单独供电 ≤500 mA 的固件限制 | USB-C 默认电流声明 500 mA | I-09 |

### 5. 文档与工具链

| 变更 | 说明 |
|---|---|
| 新增 `design/`（Python 设计数据库 + 生成器）与 `sim/`（仿真） | 网表、BOM、映射表、连接表式原理图、预布局、仿真结果全部可复现 |
| 新增自动一致性检查 17 项（ERC-01..17） | `docs/erc_report.md`，当前 0 ERROR / 0 WARN |
| 新增 `source_register.md` | 每个关键参数可追溯到原始资料版本 |
| 明确环境限制：无立创EDA / 无 LTspice / 无 ngspice | 未执行的 ERC/DRC 与 SPICE 不得声称已完成；见 README |

---

## REV.A r2 — 2026-10-18（第二轮：封装草案 / 审查包 / 仿真可信度）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `symbols/QS30-1_socket_footprint_draft.json`（全部焊盘几何 TBD，脚本校验无猜测数值） | 交接允许建"明确标注 PROVISIONAL 的封装草案"，但禁止猜测坐标/孔径/镜像 | `design/footprint_draft.py` 的 `verify_no_guesses()` 输出 PASS |
| 新增 `docs/footprint/QS30-1_管座_1比1校对页.pdf`（A4/300 dpi，含 100 mm 标尺） | 现场叠图测量与 1:1 校验需要 | 图纸内含标尺与"实际大小/100%"提示 |
| 新增 `docs/footprint/H03_管座实测工作表.md` | 把 H03 关闭证据固化为可填表项（M1–M10、四视图、通断表） | HOLD_REGISTER H03 |
| 新增 `symbols/README.md` + `symbols/QS30-1_symbol_spec.json` | 让符号可在立创EDA 中可复现地建库（脚号 1:1、禁重排规则） | S6 电极图 |
| 新增 `docs/QS30-6_REV.A_审查包.pdf`（15 页：封面+ERC 摘要+原理图+预布局+1:1 页） | 单文件审查/签审交付 | `design/review_package.py` |
| 新增仿真步长收敛性检查（Ts/40、/80、/160） | 发现 Ts/40 稳态偏差 +13.5%，必须固化 Ts/80 为收敛步长 | `sim/results/convergence.md` |
| 尝试获取真实 SPICE/EDA 工具（失败，已记录） | KiCad 需管理员安装；ngspice 下载 403。不得声称已执行 SPICE/原生 ERC | 本文件与 I-19/I-20 |

---

## REV.A r3 — 2026-10-18（SPICE 证据落地）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `sim/minispice.py`（SPICE 子集：MNA+后向欧拉+二极管Newton+压控开关） | 环境无 ngspice/LTspice，但结论需要真实执行过的 SPICE | 源码 + `sim/spice_tests/*.cir` |
| 新增 `sim/spice_validation.py` 与 `sim/results/spice_validation.md` | 求解器用解析解自检；升压功率级网表实际执行 | RC 1.8 mV / RL 0.46 mA / 二极管 5.6e-17 V 误差 PASS；Vout 171.99 V vs DCM 解析 171.95 V |
| 新增步长敏感性（50/20/10 ns）与 Coss 敏感性（1 pF/100 pF） | 防止把数值阻尼当效率；量化 Coss 影响 | 效率 89.9→95.8%；Coss 100 pF → 91.0%（−4.8 pt） |
| 新增 open issue I-22（Coss/开关损耗）并更新 H06 关闭证据 | 2.6 W 输出下 0.12 W 是显著项 | SPICE 敏感性结果 |
| 文档补充 D-18 仿真证据分级（A 厂商 SPICE / B 自带 SPICE / C 行为模型） | 避免"SPICE 已做"与"厂商 SPICE 未做"混淆 | design_decisions.md |
| 审查包新增 SPICE 验证页 | 审查更完整 | `docs/QS30-6_REV.A_审查包.pdf` |

---

## REV.A r4 — 2026-10-18（B 源支持 + DRC 预检）

| 变更 | 理由 | 证据 |
|---|---|---|
| minispice 支持 B 源（V/I 表达式：V(node)/time/min/max/数值后缀） | 让参考闭环网表可被解析；为 ngspice 交叉验证做准备 | 新增自检项 `07_b_source.cir` PASS（误差 1.0e-2 V，含 2 步显式延迟） |
| B 源改为按上一步解显式求值（frozen bvals） | 避免每步 Newton 卷入 B 源导致收敛变慢 | 收敛性/运行时间记录 |
| 明确 `boost_uc3843.cir` 仍为**未执行参考网表** | 闭环环路时间常数 ≈170 ms，开关级仿真 >10⁶ 步，超出本环境算力；不得声称已执行 | 文件头声明 + open_issues I-23 |
| 新增 `design/drc_precheck.py` 与 `docs/drc_precheck.md/json` | 在无 EDA 环境先做网表级隔离/端点/规则覆盖检查，服务 H07/H09 | **10/10 PASS**（D1–D10） |
| 修正网络分类：`DRV_VDD_EN/DRV_PG/DRV_OK/DRV_SNS` 归入 SIGNAL | 3.3 V 侧逻辑/检测节点，误分类会误导 DRC/PCB 规则 | DRC D2 由 FAIL → PASS |
| 审查包新增 DRC 预检页 | 审查完整性 | `docs/QS30-6_REV.A_审查包.pdf`（17 页） |

---

## REV.A r5 — 2026-10-18（HOLD 证据验收框架 + DRC 扩展）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/evidence_templates.py` → `docs/evidence/` 10 个 CSV 模板 | 把 HOLD"需要什么证据"变成可填、可校验的表；期望值与判据从设计数据库自动生成 | 模板行数：H02 78+6、H03 10+4+13、H04 64、H05 11、H06 14、H07 5、H08 4 |
| 新增 `design/evidence_check.py` | 自动判定 未提交/部分/通过/失败，并输出逐项失败原因 | `docs/hold_closure_report.md/json`（当前 0/7 已提交） |
| 新增 `design/evidence_selftest.py` | 证明校验器不是"死代码"：合成数据全合法 → 7/7 PASS；注入 3 处错误 → 准确捕获、退出码 2 | `docs/evidence_selftest.md` |
| DRC 预检扩展 D11–D14（封装草案"无猜测"、符号/焊盘 1:1、BOM 可制造性、证据模板状态） | 把封装草案与 BOM 也纳入机器检查，服务 H03/H09 | **DRC 14/14 PASS**（原 10 项 → 14 项） |
| 更新 README/HOLD/open_issues（新增 I-24）与审查包 | 保持交付一致性 | 审查包 18 页 |

---

## REV.A r6 — 2026-10-18（平均模型闭环 + HOLD 看板）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `sim/boost_averaged.cir` / `sim/boost_averaged_steps.cir` | 开关级闭环需 >10⁶ 步、超出算力；用平均模型在算力内验证闭环 | 稳态 172.18 V（误差 3 mV）、duty 0.931、iL 219 mA（峰值 300 mA）、负载下探 3.9 V |
| `spice_validation.py` 新增平均模型闭环判据（7 项） | 让闭环结论可自动判定 | 7/7 通过；波形 `sim/results/spice_averaged_closed_loop.png` |
| minispice B 源扩展 `I(element)` 电流引用 | 平均模型需要 `I(L1)` 构造平均二极管电流 | 回归测试（4 项自检 + 功率级）仍全 PASS |
| 新增 `design/hold_dashboard.py` → `docs/hold_dashboard.md` | 把 HOLD 填写进度与关键路径可视化 | 当前 0/7 已提交（与事实一致） |
| 重写 `sim/README.md`（结构整理：证据总览/功率级/平均模型/行为模型/参考网表/局限） | 原文件经多次追加后编号混乱 | — |
| 审查包新增「HOLD 进度看板」页并更新 SPICE 页 | 审查与项目管理一致 | 审查包 19 页 |

---

## REV.A r7 — 2026-10-18（OVP 保护逻辑 SPICE + HOLD 签署联动）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `sim/boost_ovp_logic.cir` + 7 项判据 | 把"触发/锁存/泄放/复位/再触发"在 SPICE 侧验证（此前只有行为模型） | 触发 198.92 V、峰值 201.92 V、0.3 s 泄放到 123 V、复位释放、再次锁存、最终锁存：7/7 PASS |
| `spice_validation.py` 新增 §3.5 与波形 `spice_ovp_latch.png` | 报告与图形证据 | 验证运行 ≈33 s |
| 新增 `design/hold_signoff.py` + `docs/HOLD_SIGNOFF.csv` | 把自动证据与人工签审联动，CLOSED 需两者同时满足；防"证据未过却签关闭" | 报告 `docs/hold_signoff_report.md`（当前 CLOSED 0 / OPEN 7 / MANUAL 2 / VIOLATION 0） |
| `design_decisions.md` 新增 D-22（OVP SPICE 证据）与 D-23（签署联动规则） | 决策留痕 | — |
| README/sim README/open_issues/HOLD 同步更新 | 交付一致性 | 审查包 20 页 |

---

## REV.A r8 — 2026-10-18（环路参数扫描 + 瞬态指标修正）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/loop_scan.py` → `docs/loop_scan.md/csv` + `sim/results/loop_scan_heatmap.png` | 给 H06 补偿调整（R72/C56）提供趋势与稳定性边界 | 27 组扫描：Kp 0→0.15 使输入阶跃下探 8.2→2.1 V；26/27 稳定，1 组振荡 |
| 修正平均模型瞬态指标归因 | 原"负载 3.9 V/158 ms"实际来自输入阶跃；按事件拆分 | 负载 +50%：下探 0.25 V/恢复 <1 ms；输入 12→11.4 V：3.90 V/8 ms；闭环判据 8/8 |
| sim README 增加平均模型/扫描小节并纠正数字 | 文档与仿真输出一致 | — |
| design_decisions 新增 D-24；HOLD H06 增加"环路相位裕度"实测项 | 决策留痕与 HOLD 闭环 | 审查包 21 页 |

---

## REV.A r9 — 2026-10-18（OVP 时序窗口 + 测试计划一致性）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/ovp_timing_scan.py` → `docs/ovp_timing.md/csv` + `sim/results/ovp_timing.png` | 给出 MCU 复位脉冲最小宽度与锁存保持时间（H06 实测前的时序窗口） | 7 组脉宽：最小可靠 0.2 ms；不复位时 0.9 s 保持；复位后再次锁存，最大 201.3–201.9 V |
| 修正"无复位也判为释放"的检测 bug | 初始 latch=0 被误判为释放 | 仅在锁存建立后判断释放；现 no-reset 正确显示"保持" |
| 新增 `docs/test_plan.csv`（37 项机读）+ `design/test_plan_check.py` | 把分阶段测试计划变成可机器检查的交付物，防文档漂移 | **5/5 PASS**（T1–T5） |
| test_plan.md 增加 C0（PCB 高压间距/爬电实测） | 补 H07 的硬件验证入口 | T3/T4 由 FAIL → PASS |
| design_decisions 新增 D-25（OVP 时序）、D-26（测试计划一致性）；HOLD H06 增补 | 决策留痕 | 审查包 23 页 |

---

## REV.A r10 — 2026-10-18（固件约束派生 + 文档数字一致性）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/firmware_constraints.py` → `docs/firmware_constraints.md/json` | 固件交接需要权威 GPIO/帧长/位序；手写易与网表脱节，故从网表+映射表派生 | 8 控制脚（含 IO 号）、64 位帧（60 用+4 备）、13 条约束；网络名全部校验存在 |
| 新增 `design/doc_number_check.py` → `docs/doc_consistency.md/json` | 防止跨文档关键数字漂移（历史已出现 95.8%/158 ms/7-7 类问题） | **5/5 PASS**；实际抓到并修正 4 处漂移（95.8%→95.9%、158 ms 误归因、7/7→8/8、缺基线数字） |
| README/design_decisions/HOLD 同步；report package 新增两页 | 交付一致性 | 审查包 25 页 |

---

## REV.A r11 — 2026-10-18（BOM 选型复核 + 固件约束进测试判据）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/bom_review.py` → `docs/bom_review.md/json` | 补齐"BOM + 选型理由"交付物：关键件降额/替代料/封装状态可机器复核 | 14 关键件，**5/5 PASS**（L20 Isat≥5A、高压额定≥248V、阳极电阻降额 74%） |
| 修正 BOM：L20 `220uH/3A` → `220uH/5A` | 与 F-04 决策（启动浪涌 2.9–3.1 A）一致；此前 BOM 未同步 | 重新生成 BOM/网表；H2 PASS |
| 测试计划 E5 增加固件约束判据 | 把 F07/F08（读 HVF_NODE、复位脉宽 ≥0.2 ms 且 HV<198.8 V）变成测试项 | test_plan.md/csv 同步；一致性 5/5 仍 PASS |
| README/design_decisions/审查包更新 | 交付一致性 | 审查包 26 页 |

---

## REV.A r12 — 2026-10-18（热/浪涌复核 + 投板前检查清单）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `design/thermal_review.py` → `docs/thermal_review.md/json` | 复核 HV5622 温升与 PPTC 启动浪涌；器件参数未知处用区间表达、不伪造 | 温升 0.7–6.3 °C（19–78 mW）；启动峰值 3.12 A；I²t 0.0010 A²s、超 1.5 A 0.1 ms |
| 新增 `design/preflight_checklist.py` → `docs/preflight_checklist.md/json` | 汇总所有机器检查 + HOLD，给出**硬性放行判定** | **RELEASE BLOCKED**：机器检查 11/11 PASS，HOLD CLOSED 0/9；列出 12 项投板前待关闭事项 |
| open_issues 新增 I-25（PPTC/HV5622 手册参数） | 诚实标注假设来源 | — |
| design_decisions 新增 D-30/D-31；HOLD H06 增补温升/PPTC | 决策留痕 | 审查包 28 页 |

---

## REV.A r13 — 2026-10-18（总交接页 + 从零复现验证）

| 变更 | 理由 | 证据 |
|---|---|---|
| 新增 `docs/HANDOVER.md` | 交付物太多，需要单一入口：索引/证据分级/HOLD 解除路径/限制/复现 | 审查包 29 页（末页即交接页） |
| 从零复现验证 | 证明"已完成"可复现，而非一次性手工产物 | 临时副本清空生成物后重跑全部脚本：FINAL_EXIT=0；8 项关键指标与工作区逐项一致（227/736/172/60、171.987 V/95.867%、198.921/201.925 V、14/14、RELEASE BLOCKED、0.0010 A²s/0.74–6.28 °C、27 组/1 不稳定） |
| README 顶部增加交接入口 | 使用者先读结论 | — |
| 明确阻塞判定 | 本轮结束时把目标标记为 blocked：剩余 HOLD 需实物/EDA，非本环境可解决 | `preflight_checklist.md`、`HOLD_REGISTER.md` |

---

## 待登记（下一轮）

- H03 管座实测后：更新封装坐标/孔径/1 脚视图 → 封装版本 r2。
- H04 walking-one 结果回填 `channel_mapping.csv` 位序列。
- H06 实物测试后：按实测 U_tube / 浪涌 / 泄放曲线更新 R90–R101、L20、Cout。
- H07 间距标准确定后：写入网络类别规则并生成 DRC 参数。
