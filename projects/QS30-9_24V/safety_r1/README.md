# QS30-9 高压安全工程 R1 交付报告

2026-11-17，Asia/Shanghai。工作基线 `ee53f81c3f93539906445482bd17e564829338ef`（`nxt/reva9-electrical-sprint03`）；成果已推送至 **`nxt/qs30-hv-safety-r1`**，未合并。**这是安全行为基线、部分器件连接设计、可重复软件/低压单元验证及审查工作流交付；完整硬件安全系统尚未完成，制造 HOLD。** 未采购、未下单、未进行物理高压实验。

## 1. 实际完成的成果

|工作|可审查入口|范围|
|---|---|---|
|输入/历史审查|[BASELINE](governance/BASELINE.md)、[历史哈希核验](governance/history_check.json)|指定八文件及S06C–F记录；3189个历史源文件未变；未跟踪历史大波形不在哈希范围|
|Round 1 行为设计|[架构](architecture/SAFETY_ARCHITECTURE.md)、[20条需求](architecture/requirements.json)|完整电源域图、11态/转换、启动顺序、极性、15项FMEA、关断/残压/复位|
|Round 2 器件候选|[连接说明](circuit/CIRCUIT_REVIEW.md)、[393条逐脚连接](circuit/pin_connections.csv)、[未实现接口](circuit/netlist_scope.json)|10种关键IC候选、8个指定型号逐项核对；不等于完整采购BOM/电气网表|
|资料资格|[原厂版本/哈希](sources/device_qualification.json)、[关键IC候选BOM](circuit/bom_candidates.csv)|10份原厂PDF归档；立创映射均HOLD；Q201另有PDF403缺证记录|
|Round 3 实际执行|[验证报告](verification/VERIFICATION_REPORT.md)、[机读统计](verification/verification_summary.json)|标准Python测试、真实TI门驱宏模型低压单元、24V拓扑/缩放RC；完整输入、日志、波形、命令及哈希|
|Round 4 独立审查|[C审查](review/INDEPENDENT_REVIEW.md)、[9项发现](review/findings.json)|C未参与初稿；独立反例、RTN/失电/复位/共因/短路/制造审查|
|Round 5 修复回归|[首轮红日志](verification/tests_r1_red.log)、[C红](review/round4_initial.txt)、[C绿](review/round5_retest.txt)、[最终259项](governance/final_checks.json)|保持相同判据修正逻辑，没有以程序退出0代替电气通过|
|继续闭环：泄放修订|[电路增量](circuit/BLEED_REVISION.md)、[新增6次仿真](verification/bleed_revision_r1/REVISION_REPORT.md)、[独立补审](review/BLEED_REVISION_REVIEW.md)|双永久主板泄放候选，在理想RC边界改善单开路表现，真实元件/制造仍HOLD|
|EDA/PCB迁移|[E制造审查](manufacturing/EDA_REVIEW.md)、[HOLD清单](governance/holds.json)|专业版迁移数据、封装/材料映射缺口/测试点/间距条件；未原生ERC/DRC|
|持续集成|[workflow](../../../.github/workflows/qs30-safety.yml)、[CI成功证据](governance/ci_success.json)|远程实际执行规格、独立回归及候选/证据完整性；CI不运行新SPICE|

独立子智能体实际承担A架构、B模拟电源、D仿真和C后置独立审查；E由主智能体在隔离文件承担。受并发槽位限制，C在初稿完成后启动，没有声称五个独立智能体同时运行。

## 2. 通过了什么，以及统计口径

**当前软件/数据共259项，259 PASS / 0 FAIL / 0 ERROR / 0 SKIP**：245项规格模型（19个已检测故障谓词、171对有限双谓词、32个许可真值组合、23个顺序/复位等）、4项C独立反例回归、10项关键IC/网络/来源及证据哈希/HOLD数据检查。重复执行同一测试不重复增加测试数量。

这些测试中的故障输入假定“外部硬件已经检测到了故障”；它们不证明物理断线/短路/温度或反灌已可检测。窗口心跳也仍是已资格信号的抽象，不是实际看门狗电路。软件状态机正确性不是硬件安全验证。

**实际新SPICE进程45次**（ngspice47，构建/可执行文件哈希见各预登记）：

|运行目录|实际次数|严格执行检查|限定工程结论|
|---|---:|---|---|
|verification/spice_r1|8|4 PASS / 4 FAIL|4门驱有限PASS / 4 INCONCLUSIVE|
|verification/spice_r2|8|8 PASS|8门驱有限PASS|
|verification/spice_r3_aux11p4|8|8 PASS|8门驱有限PASS|
|verification/spice_r4_aux12p6|8|8 PASS|8门驱有限PASS|
|verification/topology_r1|6|6 PASS|被动通路/RC一致性6 PASS；其中泄放要求3数学PASS/1 FAIL|
|verification/topology_r2|1|1 PASS|RC一致性PASS，5s泄放要求FAIL|
|verification/bleed_revision_r1/evidence|6|6 PASS|修订RC6项有限PASS，保持原FAIL|
|合计|45|41 PASS / 4 FAIL|不同层次不相加成“硬件安全通过数”|

45次进程均rc0并到各自终点，但首轮4例ASCII时间精度破坏严格单调检查，因此仍记执行FAIL。32次厂商门驱中28有限电气PASS/4 INCONCLUSIVE/0已判电气FAIL；其负载为线性电容，未包含真实MOS/Miller/源极弹跳。7个原拓扑研究一致性PASS不掩盖其中2项泄放设计FAIL；修订6例不覆盖真实电阻/高压/共地。所有新仿真电压源为0–24V；195V只用于缩放阈值及解析边界，没有170V物理试验或本次完整HV功率级仿真。

原厂PDF哈希和3189项历史源完整性分别检查通过；两项OVP/残压静态公差筛查也通过，但不算SPICE或动态电气资格。

远程CI [43906102107](https://github.com/langxie29-cpu/QS30-driver/actions/runs/43906102107) 已在提交 `3e6712373c20eaf2516c04ab9d5a08abfb10be66` 成功。首轮 [43905265707](https://github.com/langxie29-cpu/QS30-driver/actions/runs/43905265707) 因workflow先于测试目录提交而失败，见[原失败记录](governance/ci_initial_failure.json)；补齐提交后实际重跑通过。未把本地结果当作远程执行。

## 3. 失败、修正及保留结果

- 初稿245项中4项失败：DRV运行掉压未锁存、残压检测有效性在启动/复位缺失、复位缺支路关断回读；修复后同245项通过。原模型快照和红日志可重现。
- C独立4例初始2失败：健康态RESET不撤令牌、按住RESET仍可武装；D修后C用同4判据独立复测全通过。真实CLR/CLK竞争仍HOLD。
- B自审修正HV输入许可等待预充完成的死锁；DRV启动许可也排除了自身DRV_OK依赖。
- TPS3431只实现超时，不能满足窗口下限；没有降低架构要求，新增实际窗口检测HOLD。
- 原泄放单开路/模块组合暴露FAIL：仅一主板串、模块电容保留时约5.074852s；主板唯一泄放开路时残压长期保留。新增两条2×90.9k永久串，单串开路最慢约4.613041s；一电阻短路后剩余电阻须承受195V/0.422542W，准确MPN及热降额未资格。原C07 FAIL保持，候选仅记MODEL_IMPROVEMENT_ONLY。
- 首轮4次SPICE的时间打印精度错误以新目录/15位输出修正重跑，未改容限/电气判据。早期来源URL误写SLUM030，追加审计更正为真实SLUM488，原模型哈希未变；未覆盖旧记录。
- eFuse卡通时，门极为0仍被动充电约23.483V；MOS D-S短路也不能由关栅消除。此类物理风险没有被逻辑模型“修成通过”。

## 4. 尚未验证与硬件完整性

完整09仍未通过：故障聚合/供电有效转换、按钮释放后新边沿、请求动态见证、实际窗口看门狗、异步置位优先/释放时序、独立残压诊断、FLT/IMON隔离、持续支路OC、BL/COMP掉电执行、真正退磁及受限启动尚有未实现或未资格接口。逐脚表中这些接口明确列HOLD，不是可制造电路的省略写法。

eFuse加密动态模型、反接/USB保活/半供电、全温光耦漏电和关断时延、TPS3700最大传播上界、195V故障峰及剩余电感能量均缺证；真实高压、物理MOS/eFuse短路、器件/布线共因和全部硬件单故障未验证。正常反馈、OVP与双残压独立分压仍共有物理回路；断地/上臂断线诊断不能由“独立”一词证明。

历史24V-07真实电流采样、热态磁件、非线性器件/数值收敛仍未通过；24V-08未进入。旧12V过流采样、异常锁存电流、不安全复位及失电FAIL完全保留。新安全模型与门驱单元不能覆盖或关闭这些门槛。

## 5. 与上一版的实质变化

将“MCU高电平+AND许可”升级为人工新START、新请求、硬件令牌、窗口健康和供电有效要求；将复位与启动分离；将输入关断回读和独立有效残压纳入复位。分别处理DRV建立与DRV失压，修复两类启动死锁。沿用S06B对RTN隔离要求，拒绝旧FLT直接上拉3V3。补充双残压/温感窗口候选和逐脚审查；识别TPS3431能力不足。新增可重复故障回归、真实低压门驱/被动路径/泄放原失败，以及双主板泄放修订候选。

S06C后续LT3757A仍是候选，UCC28C43/UCC27511适配表不能自动变成LT3757A的SHDN/SS/VC/GATE实现。新双泄放增加约0.173432W负载，原5.71642W的HV研究预算至少增至约5.88985W，须重新审07正常限流/效率/热/闭环，未凭旧预算放行。

## 6. 低压验证板和完整主板结论

**可以继续设计独立低压验证板；目前不能释放该板制造。** 物理不装Boost L/MOS/D、HV电容、管座和可接HV输出，检测端只注入限流低压。先完成实际窗口/锁存/按钮/PG/残压/双执行接口、准确封装/无源BOM、低压源能量与接线/ERC审查，再进入后续制造评审。本次无采购或下单授权执行。

**完整QS30主板禁止投板。** 未建立嘉立创专业版原生安全原理图，未运行原生ERC/DRC。CSV、JSON、Mermaid和封装名均不是原生工程。立创C编号未验证；HV间距标准的污染等级、材料组、海拔、瞬态及可触碰结构尚未冻结，不能猜毫米值放行。07/08/09/10及历史制造HOLD均未关闭。

## 7. 下一阶段最小工作集，按风险和依赖顺序

1. 完成真实电源有效/部分供电默认禁止、窗口看门狗、请求/人工边沿与置位优先锁存电路；明确最大时延，先用限流低压验证。不要由MCU产生最终安全资格。
2. 完成双执行器和RTN接口（含FLT/IMON）、真实支路关断回读；验证反接、USB保活、失电/复电、执行器卡通与MOS短路源能清除路径。
3. 完成OVP/温感/残压独立检测的真实元件、断线/断地诊断和最坏时延；冻结残压用途及接触安全依据。选定双泄放真实MPN/热降额/失效模式并更新负载预算。
4. 关闭07真实采样/硬限流、热态L(I,T)/磁损和模型收敛/关断应力；全部07门槛满足后才进入08从0V自主启动及闭环。
5. 在前述条件下验证09完整故障传播/195V峰值和10真实泄放/模块/单故障，再迁移专业版受控库、原生ERC/布局/DRC及机械绝缘审查。真实HV操作和制造均须后续明确授权与放行。

## 8. 复现和提交

标准库即可运行所有软件/数据回归（输出路径必须全新）：

```powershell
python projects/QS30-9_24V/safety_r1/governance/run_checks.py --output checks_new.json
python projects/QS30-9_24V/safety_r1/governance/history_guard.py check
```

新克隆不带未跟踪ngspice工具；按验证报告取得官方构建并核可执行哈希，显式传`--exe`，所有仿真输出必须新目录。原厂模型副本已归档，不依赖未提交S06C–F。回归与哈希检查不产生新SPICE次数；完整命令见各runner及预登记。CI读取已归档波形哈希，不把它称为远程重仿真。

已分阶段提交：`8eb61e88`历史保护/EDA门槛；`ff79a169`行为架构；`5375c7a4`器件来源/逐脚候选/CI；`3e671237`反例修复及45次低压仿真证据。最终报告、C泄放补审与远程CI证据另有收尾提交；以工作分支git log为准。没有提交接手时README/project.json/TASKS.csv或其它S06C–F历史工作区变更。
