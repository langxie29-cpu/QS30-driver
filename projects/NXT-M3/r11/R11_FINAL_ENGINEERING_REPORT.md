# NXT-M3 R11 工程最终报告

**2026-11-21 · GATE_0 = REWORK · ENGINEERING HOLD · MANUFACTURING_RELEASE = HOLD**

R11 基线为本地真实 R10 提交 `28de4da83d4c02a80e16f68dae0151824e51d968`，其父提交为 R9 `f74f626d798407439c17ac635eb7946727dec628`，再继承 R8 分立阴极 `b264d74dce5b799ecd13286fa3c2880b1b7135d2`。工作在 `nxt/nxt-m3-routing-simulation-r11`。R10 工作树中的未提交项目选项和机械预览保留。R11 采用 R10 已提交的工程及候选机械尺寸。

## 工程状态

| 状态 | 实际结论与证据 |
| --- | --- |
| SCHEMATIC_CAPTURE_COMPLETE | **LIMITED_PASS**。根页和 14 张子页可用。827 个引脚网络条目保持一致，4 片 595、30 路与两个 NC 逐路复核。实际高压电路仍为候选，R40 DNP。 [原理图](eda/NXT-M3-R11.kicad_sch) · [网表核验](evidence/r5/pins.json) |
| PCB_PLACEMENT_COMPLETE | **REWORK**。282 个电气候选和四个板载安装孔，泄放两排重摆。U3/MH1、U3/V1 投影，D3/Q32 区、封装净距和装配仍开放。 [布局审计](evidence/r5/board_independent.json) |
| PCB_ROUTING_PROGRESS | **REWORK**。2078 段实铜、170 过孔、98 网有铜。R10 的 561 个 PCB 连接项净减 262，进展 46.7%。剩 299 项／126 个 PCB 网络，另有 33 个管座端网，总计 159 个不同剩余网络。 [PCB](eda/NXT-M3-R11.kicad_pcb) · [分网表](evidence/r5/net_completion.csv) |
| ERC_STATUS | **PASS，原生检查**。KiCad 10.0.8 退出 0，0 错误、0 警告。继承 KiCad 默认忽略的 SPICE 与封装过滤器等 ERC 项由模型/焊盘另行复核。 [ERC](evidence/r5/ERC_REPORT.txt) |
| DRC_STATUS | **REWORK**。退出 5。266 条间距错误、12 条钻孔错误、2 条丝印警告，299 个未连接项、3 个缺失 V1–V3 封装。打开 all-track-errors 后结果相同，现有规则错误涉及焊盘/工艺，布线仍有实质开项。 [DRC](evidence/r5/DRC_REPORT.txt) · [分级原始条目](evidence/r5/DRC_TRIAGE.csv) |
| POWER_SIMULATION_STATUS | **REWORK**。25 个命名工况中 22 个完成波形，3 个 TI 模型工况不确定。标称开关代理确实从 0 V 起动，4.4 V 满载和重启未覆盖目标。 [电源仿真](POWER_SIMULATION_REPORT.md) |
| CATHODE_DRIVER_STATUS | **REWORK**。3.3 V 带载 VOH/IOH、晶导热态漏电、SOA 和单路故障边界仍待真实证据。 [驱动验证](CATHODE_DRIVER_VALIDATION.md) |
| GATE0_SAFETY_STATUS | **REWORK**。OVP/OCP 有代理切断记录，失供、反灌、假低、单路半导通和触达限制尚未关闭。 [安全评估](GATE0_SAFETY_ASSESSMENT.md) |
| MECHANICAL_FOOTPRINT_STATUS | **HOLD**。管座型号、焊脚中心、孔径、外径、高度、固定和装配方向全部要求实物数据。 [机械阻塞](MECHANICAL_BLOCKERS.md) |
| MANUFACTURING_RELEASE_STATUS | **HOLD**。依据 0 V 厂商闭环、器件热、绝缘、实物管座、完整 DRC 及物理检验链另行评审。 [制造阻塞](MANUFACTURING_BLOCKERS.md) |

## 六轮验证与提交

原生规则和网络开项分开计数。优先级统计为每项 DRC 记录归并，P0 含高压规则和缺失 V1–V3，P1 含 DRC 连接项，P2 为丝印。仿真计数为累计工况／有效波形。所有轮次 Gate 0 均为 REWORK，制造 HOLD。

| 轮次 | 修改与实际工具证据 | ERC / DRC / 已减少与剩余连接项 | 工况 / 有效 | P0/P1/P2 | 决策 | 提交 |
| --- | --- | --- | ---: | --- | --- | --- |
| R0 | 冻结 R10 原生文件与已重跑的 ERC、网表、DRC，复核 R9/R8 Git 继承和用户改动 | 0 / 292 / 0、CLI 499，连接引擎复核 561 | 0/0 | 242/550/2 | LIMITED_PASS 基线有效 | `de977d1fe5bd71dbb47d64d222bc69ba093a1a7f` |
| R1 | 原生 R11 项目、网络类、逻辑阴极映射与分区约束 | 0 / 292 / 0、CLI 499 | 0/0 | 242/550/2 | LIMITED_PASS | `12f977fe22ec52822a74b3f83a324e69213e497c` |
| R2 | 网表、偏置和电流模式模型，执行冷启、负载、输入、放电与故障 | R1 工程基线 | 20/17 | 242/550/2 | REWORK | `c47c08d336ff5031507218b0d87e561a476b130e` |
| R3 | 双层放置与五区原生布线，每区 KiCad DRC | 0 / 280 / 252、309 | 20/17 | 230/360/2 | REWORK | `923693932a33cc61c91263b1c56d0216c3e0ace0` |
| R4 | 小网格补线、低压局部地铜、寄生 L 和保护波形复跑 | 0 / 280 / 262、299 | 25/22 | 230/350/2 | REWORK | `7ae919ca6bbf14a2ee32a5cbd4c84715d3b5b590` |
| R5 | 独立执行 Native CLI 和 pcbnew 审计，复核 BOM、原始波形 SHA、器件应力及快速复算。独立过程为工具复核，未另行委托个人签核 | 0 / 280 / 262、299 | 25/22 | 230/350/2 | REWORK | 见本分支 R5 提交及交付回执 |

R11 改动全部在 `projects/NXT-M3/r11`。布局与原理图引脚同步差异为 0。原生 BOM 对比见 [BOM 复核](evidence/r5/bom_review.json)。检查及可复现命令见 [交付入口](REPRODUCE.md) 和 [原生命令记录](evidence/r5/commands.json)。

## 电气资格与下一轮

标称 5 V、7.65 mA 冷启代理得 169.809 V、0.133112 Vpp、1.73528 A 峰值电感电流和 171.858 V Q32 VDS。全试验最大电感电流 1.75726 A，50 nH 假设工况 VDS 达 251.15 V。C47 在 170 V／3.3 µF 储能 47.69 mJ，195 V／3.63 µF 为 69.02 mJ。195 V 半导通等阻代理的 0.4801 W 可由上游持续供能。R4 的假定 10–50 nH 证明峰值对寄生敏感，当前缺实际完整回路和寄生提取。 [资格矩阵](POWER_QUALIFICATION_MATRIX.csv) · [应力表](COMPONENT_STRESS_REVIEW.csv)

1. 取得可运行的真实控制器/保护模型，闭合低线满载、重启、失供/反灌和半导通诊断，并计划相应板级证据。
2. 实测拆机管座全部尺寸、针位/键位及导通，检查 OLED 和墙装 RF，并冻结绝缘协调输入。
3. 重摆和完成开关环、回流、采样、各 595 与管座交接。选定层数和焊装工艺后重跑原生 DRC、同步和应力检查。

[KiCad 工程入口](eda/NXT-M3-R11.kicad_pro) · [布线报告](PCB_ROUTING_REPORT.md) · [本轮工程证据](evidence/r5)
