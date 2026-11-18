# 前级保护架构 R5

**电气 HOLD。否决原启动策略下 LM5069/R111 的直接替代。** 保留 LM5069-1 作带功率限制的预充/前级管理候选。优先研究可保证的启动限流和独立支路快速开断。两条链都要保持失电禁能和人工复位。

## 窗口与电流政策

TI 最小稳态限流 48.5 mV、最大开断阈值 130 mV，加 ±1% 采样电阻。Rs ≤ 48.5 mV/[I_start,max×1.01] 且 Rs ≥ 130 mV/[I_breaker,max×0.99]。冻结启动峰 1.649202 A 与冷态 3.1 A 给出 29.117 mΩ 上界、42.359 mΩ 下界。静态窗口要求 I_start,max ≤ 0.36569×I_breaker,max。3.1 A 冷态参考下，启动最大允许 1.134 A。若设计到 1.0 A，冷态窗口为 42.359–48.020 mΩ，热态允许开断电流低于 2.735 A 时窗口仍关闭。按 2.5 A 假设，启动峰应低于 0.914 A。真实传播延迟、纹波、温漂、Kelvin 压降与误差须另外预算。

分离偏置建立、支路预充、稳定确认、新 START、受控升压。0.85/1.0 A 作研究目标，比较输入电压、热态、负载和输出电容角落，同时检查 R4 输出建立 1 s、恢复及波动限值。分别观察源电流和 L20 峰流。R111 继续 HOLD。

LT3757A 的 RS20 为 62 mΩ ±1%，SENSE 阈值 100/110/120 mV 对应 1.597–1.955 A 静态范围。实际峰值还需比较器传播、消隐、UCC27511、Q20 关断、斜率、温度与 SENSE 振铃。原 1.6492 A 名义峰高于最低静态阈值，无法移植为启动保证。PWM 关闭无法阻止 Boost 被动输入路径或应对 Q20 D–S 短。继续独立审查真实 12 V 偏置、门驱和 INTVCC。 [ADI LT3757A](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3757-3757a.pdf) · [TI UCC27511](https://www.ti.com/lit/ds/symlink/ucc27511.pdf)

## Q101 与实际故障开断

- **准确研究候选 Infineon IPB017N10N5LFATMA1**。100 V、D²PAK-7、G=1、D=4/焊盘、S=2/3/5/6/7，原厂 active/preferred、有线性热插拔 SOA 曲线。典型 Qg 195 nC、Qgd 141 nC。要评估实际加载时的最慢门极放电和 TVS 后最高 VDS，并使用实际故障前壳温、脉宽、重复应力和 PCB 铜的热模型，取得热态 SOA 证明。TI 用 CSD19536KTT 作参考加载示例，可对照开断测试方法。Q101 仍为 DNP。
- LM5069 的 1.2 µs 最大断路器响应来自指定 150 mV 阶跃和无载条件。最大「检测→比较→锁存→门极下降→支路电流下降」仍未知。独立支路检测先筛 INA301 的 36 V 共模、过压和真实加载延迟，完整预算需覆盖故障斜坡和温度。不能取得最大延迟或热态 SOA 时，前级继续 HOLD。
- TPS26601 U100 保留独立 SHDN，RTN100 维持浮动参考。逐项处理采样短路、Q101 D–S 短、U100 内部开关短、检测/偏置掉电、旁路粘连、输入持续供电。故障锁存后应确认开断、监控有效及残压低，再接受新 RESET 与新 START。持续按住按钮、恢复偏置和循环供电均须纳入重启审查。

[TI LM5069](https://www.ti.com/lit/ds/symlink/lm5069.pdf) · [Infineon 订货与生命周期](https://www.infineon.com/part/IPB017N10N5LF) · [Infineon SOA 与封装](https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipb017n10n5lf-datasheet-en.pdf) · [TI INA301](https://www.ti.com/product/INA301)

## 储能与热态边界

26.4 V 时 Q101 上游 56.51 µF 储能 19.69 mJ，动作完成前可继续输入。下游假设 1 µF 为 0.348 mJ。在 135 µH 线性、1.6492 A 初值与假设 2.5 A 阈值下，无损本地电容的临界值约 0.684 µF，持续 26.4 V 升流到阈值约 4.35 µs。这是两个孤立敏感度算例。实际故障可同时由源和电容供能，热态饱和时线性模型会偏乐观。取得 L(I,T)、纹波/损耗和实际温升，另计 Q101 Coss/Eoss、TVS、PCB 走线、封装、探头和局部去耦。开断节点附近的储能应按能否绕过该开断器件分区。

195 V、22.315 µF 的 HV 输出储能约 424.3 mJ，属于独立 HV 回路。分别审查双泄放、共地故障、回灌、触碰、残压与输出短路。冻结 R4 后置储能故障的 ELECTRICAL_FAIL 保留。

[窗口扫参](evidence/frontend_static_windows.csv) · [储能扫参](evidence/frontend_storage_sensitivity.csv) · [R4 能量预算](../power_loop_r4/FAULT_ENERGY_BUDGET.csv)
