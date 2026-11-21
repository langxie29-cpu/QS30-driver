# R14 — Cathode Safety Closure

**R14 PARTIAL / HOLD**

**EVT_RELEASE = HOLD**

**MANUFACTURING_RELEASE = HOLD**

R14 从本地与远端跟踪引用一致的 R13 `bf6dd9adecc0adc18f43991aa06f227d0327c990` 创建独立分支。复制的是该提交包含的 R11 EDA 快照，快照最近的路径提交是 `9a0be72b655b274c6712053ac32ebb90612b82eb`，包含后续管座和走线修订。原始工程保留。 [独立 KiCad 10 候选](eda/NXT-M3-R14.kicad_pro)

## 本轮解决的工程问题

- 对原生 R11 的 263 项净距逐项分类。103 项是同封装焊盘，160 项是相邻封装焊盘。153 项涉及 Q1–Q30，其中 60 项为每颗晶导 SOT-23 重复出现的两个铜间距问题。Q1 候选去除了三个外部碰撞，原防护规则仍生效。 [原始分类](evidence/baseline/clearance_causes.csv) · [绝缘协调](INSULATION_COORDINATION.md)
- 新增原生 J5 功能按钮与 J6 常闭 HV STOP。GPIO10–13 的四个真实焊盘已映射并通过网表核对。J6 的电缆与输入级已实际布线，继承的 U8/ARMED 获得一条 PCB 连线。J6 停止硬件链及 J5 到 GPIO 的接续还需完成。 [接口原理图](eda/Physical_controls.kicad_sch) · [PCB 修改记录](PCB_CHANGELOG.md)
- ngspice 执行 21 个阴极代理及 4 个 STOP 代理，保留可复算原始波形。持续 195 V 工况约 0.4784 W / 4 s 约 1.914 J，Q35 开环模型清除锁存，故障后需新 ARM，单路泄放、回路短接、断供器卡通及未上电回灌的限制已登记。 [热/SOA](THERMAL_SOA_REVIEW.md) · [HV STOP](HV_STOP_VALIDATION.md) · [检测矩阵](FAULT_COVERAGE_MATRIX.csv)

## 原生证据差异

| KiCad 10.0.8 | R11 本轮复跑 | R14 候选 |
|---|---:|---:|
| ERC 错误 / 警告 | 0 / 0 | 0 / 0 |
| DRC 净距违规 | 263 | 260 |
| 未连接项 / 涉及网络 | 345 / 166 | 365 / 169 |
| 原理图与 PCB 一致性违规 | 0 | 0 |
| Q1 涉及净距违规 | 5 | 2 |

ERC 仍有四个忽略类别。DRC 仍有五个忽略类别。R14 新增接口造成整板开路净增 20，首个 Q1 通道也未完成接线。完整报告和审计对照可复查。 [基线](evidence/baseline/) · [R14 ERC](evidence/erc/ERC.rpt) · [R14 DRC](evidence/drc/DRC.rpt) · [审计摘要](evidence/pcb/summary.json)

## 距第一台样机

GPIO 选型、连接器分工、HV STOP 的逻辑行为和 Q1 外部净距问题已有原生证据。短接联锁、逻辑链与 eFuse 的失效、阴极单故障能量上界、三路诊断、涂覆与基材证据、样品安全绝缘和大范围 PCB 连通性仍阻塞样机。保留 LM3488/EFD15 优先验证与 LM5155 备选。R40 曾经和现在均为 DNP，冻结 R11 电源节点接法。DeepSeek 仅完成只读预检，付费调用 0。 [阻塞登记](R14_BLOCKER_REGISTER.md) · [复现说明](REPRODUCE.md)
