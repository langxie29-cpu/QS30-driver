# R11 Type-C、布线与低线堵塞续轮

**2026-11-21 · Gate 0 REWORK · ENGINEERING HOLD · 制造 HOLD**

本轮基于管座提交 `9bf4f4a424241d731b8b0cc395da6bf4bbfaa6eb`、Type-C 提交 `db00df02893e169ddcf2583da06f930f07f9dc97` 与 R10 `28de4da83d4c02a80e16f68dae0151824e51d968`。双层 PCB 为当前工程主板。

## 实物设计文件与原生检查

- F1 转向后，J1 A9/B9 到 F1.1 的 0.50 mm VBUS 铜线导通。保险丝输出 F1.2 到 R1.1、R3.1 导通。U1 输入仍有一个 `5V_FUSED` 开项，U26 的 VBUS 取样和 `5V_RAW` 其余分支仍有两个开项。当前 USB-C 供电链尚未闭合。 [逐端铜线复核](evidence/blocker_closure/final/route_connectivity.json)
- V2.1 到 R305.2 的 ANODE_2 已走通，ANODE_3 仍导通。33 个交接焊盘中 2 个原生导通，30 路阴极及 ANODE_1 仍未连接。原生 Excellon 命中全部六个 Ø3.5 mm 管座安装孔，Ø8 mm 紧固件审查圆内未发现走线或焊盘。孔位沿用 R10 GZC13-F 参考，仍需收到实物后核对孔距、定位键和线序。 [管座审计](evidence/blocker_closure/final/socket_fit_audit.json) · [原生钻孔报告](evidence/blocker_closure/final/drill_report.txt)
- U3 改用项目自带封装。ESP32-S3-WROOM-1-N8、本体位置、焊盘中心、锡膏窗口和天线禁布区保持原样。借用 KiCad 10 的标准封装几何，将 12 个 GND 焊孔从 0.20 mm 改到 0.30 mm，铜环外径保持 0.60 mm，名义单边环宽 0.15 mm。将 3 条跨天线端板边的轮廓图元移到 F.Fab。原生 DRC 少了 12 个孔径错误和 2 个丝印警告。底层低压地铜扩到模块端，U3.1/U3.40 加短接和过孔，GND 开项 124 → 122。装配前仍需板厂确认热焊盘通孔的填孔和回流工艺。 [本地 U3 封装](eda/R10_R10.pretty/ESP32-S3-WROOM-1_0.30mm_Drill.kicad_mod) · [地铜对照](evidence/blocker_closure/ground_return_comparison.json) · [Espressif 模组数据表](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- KiCad 10.0.8 实跑 ERC 0 错误、0 警告，原生导出网表成功，原理图/PCB 一致性检查 0 项。DRC 退出 5。未连接项从 349 降至 **345**，集中于 **166 个网络**。规则违规从 277 降至 **263**，均为净距错误。工程 DRC 规则和板厂孔径下限保持原值。 [原生 ERC](evidence/blocker_closure/final/ERC_REPORT.txt) · [原生 DRC](evidence/blocker_closure/final/DRC_REPORT.txt) · [检查命令及退出码](evidence/blocker_closure/final/commands.json)

### Type-C 四层实布分支

在四层比较板上已把 J1 A5 到 U26.1/U26.2 的 CC1 接通，走在 In1.Cu。四个铜层均约束 U3 天线禁布。原生 DRC 剩 344 个未连接项和原 263 条净距违规，原理图一致性 0 项，未新增规则违规。另试把 `5V_PROT` 主干移至 In2.Cu，五种落孔位置产生新违规，均撤回。 中间原生 DRC 按原文件名存入压缩包。双层当前仅 CC2 通过铜线复核。现有证据只证明内层可解决这个 CC1 交叉，不能证明整板可布通或电源回流合格。当前无可比较的同工艺四层报价。 [四层 KiCad 比较板](evidence/blocker_closure/four_layer_cc1_preview.kicad_pcb) · [四层 CC1 DRC](evidence/blocker_closure/four_layer_cc1_10.json) · [内层电源对照](evidence/blocker_closure/four_layer_trunk_comparison.json) · [中间 DRC 归档](evidence/blocker_closure/intermediate_drc.zip)

## 从 0 V 启动的低线和容差复验

10 个工况全部有 ngspice 退出码 0 和到 65 ms 的有效波形。二次解析核对了每个原始波形的 SHA-256、有限值、时间顺序和 0 V 输出初值。对最终 62–65 ms 均值和纹波，用 165–175 V、≤1 Vpp 的代理筛选，4 个达到，6 个需要返工。代理使用现有 Type-C、eFuse、稳压和升压拓扑。R40 仅按仿真假设临时闭合，硬件仍 DNP。首轮厂商 LM5155 模型的前端联合运行超时，仍无有效厂商闭环波形。 [资格计算表](LOWLINE_BLOCKER_SWEEP.csv) · [原有 Type-C/厂商模型记录](TYPEC_ECO_REPORT.md) · [TI LM5155](https://www.ti.com/product/LM5155)

| 工况 | L3 / 时钟 | HV 平均 | 纹波 Vpp | L3 峰值电流 | 代理结果 |
| --- | --- | ---: | ---: | ---: | --- |
| 4.75 V 满载复跑 | 22 µH / 100 kHz | 155.843 V | 1.108 V | 1.627 A | REWORK |
| L3 低公差 | 17.6 µH / 100 kHz | 169.799 V | 0.182 V | 1.749 A | LIMITED_PASS |
| L3 高公差 | 26.4 µH / 100 kHz | 145.109 V | 0.821 V | 1.477 A | REWORK |
| 15 µH 候选低公差 | 12 µH / 100 kHz | 148.797 V | 1.381 V | 1.825 A | REWORK |
| 15 µH 候选高公差 | 18 µH / 100 kHz | 169.795 V | 0.109 V | 1.745 A | LIMITED_PASS |
| 15 µH 候选高线空载 | 12 µH / 100 kHz | 169.791 V | 0.211 V | 1.849 A | LIMITED_PASS |
| ±10% 假定窗口下端 | 16.2 µH / 100 kHz | 169.092 V | 2.219 V | 1.767 A | REWORK |
| ±10% 假定窗口上端 | 19.8 µH / 100 kHz | 162.315 V | 1.512 V | 1.721 A | REWORK |
| 降频诊断标称 | 22 µH / 80 kHz | 169.847 V | 0.542 V | 1.697 A | LIMITED_PASS |
| 降频诊断高公差 | 26.4 µH / 80 kHz | 166.898 V | 1.814 V | 1.645 A | REWORK |

除高线空载行外，源端均为 4.75 V，线缆往返 0.190 Ω，3.3 V 域用 2.475 W 负载边界，高压域 9.9 mA。高线为空载高压、0.76 W 低压、5.25 V。标称满载实际模型升压端平均仅 4.346 V。10 个模型工况最大的 L3 峰值为 1.84855 A，最大的 Q32 VDS 为 171.947 V，均发生在 15 µH 候选高线空载。开关本体和电流瞬态取决于代理及寄生，不能据此确定硬件降额。C47 3.3 µF 在 170 V 存储 47.69 mJ，上轮以 195 V 和 3.63 µF 边界得 69.02 mJ。 [应力原始日志](evidence/blocker_closure/lowline/candidate_15u_highline_light/run.log) · [既有应力核查](COMPONENT_STRESS_REVIEW.csv)

同尺寸 Coilcraft 15 µH 备选在 ±20% 低端失去调节，18 µH 假定窗口两端也未同时达到判据。80 kHz 测试只改变时钟周期和 92.5% 最大占空比的计时，保留原代理补偿斜率，属于诊断线索。原理图、PCB 和 BOM 的 L3、R79、R73 保留原值。 [Coilcraft 22 µH](https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/mss-mos/mss1278/mss1278-223/) · [Coilcraft 15 µH](https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/mss-mos/mss1278/mss1278-153/)

低线试验的 `circuit.cir`、`run.log`、`measurement.json`、`waveform_metrics.json` 和抽样 `waveform_sample.csv` 随工程保存。约 5 GB 全量 `waveform.raw` 位于本地同一工况目录，按 Git 忽略规则保留在工作树。可用 KiCad 10 的 Python 从本目录依次执行 `sim/lowline_tolerance.py` 和 `sim/summarize_lowline.py` 复跑并交叉核验。重新运行后求解器和时间戳可能产生新的文件散列。

## 仍阻塞投板的事项

| 优先级 | 摘要 | 闭合证据 |
| --- | --- | --- |
| P0 | 263 项净距错误。代表性 Q1 基极和集电极铜边约 0.655 mm，2.00 mm 工程筛选未满足。 | 完成实际电压与环境下的绝缘协调，选用可满足约束的高压封装与布局，清除 DRC。 |
| P0 | 低线满载输出、真实 LM5155 闭环、OVP/OCP、输入真断开、反灌、残压联锁及持续半导通仍无充分资格。 | 用一致的器件与电路获得冷启、已装电源链、重复故障应力和失电安全证据。国产 MMBTA42 需明确批次、SOA 与热态数据，HC595 需确认 3.3 V 带载 VOH/IOH 与漏电。 |
| P1 | U1 输入、U26 VBUS/CC1/供电和判定引脚、保护后电源、HV 反馈/采样、30 路阴极及第一路阳极仍开。 | 重排 Type-C/eFuse 局部电源入口、分配电源和连续回流，完成布线和真实寄生复核。 |
| P1 | 六孔和预留焊盘已入工程。R10 管座参照的实物安装与线序仍未校准。 | 1:1 样板确认孔距、螺钉和支座外廓，用实际管座核对定位键、阳极/阴极和绑扎。 |

下一轮优先推进三项工作。

1. 确定 Type-C/eFuse 小范围重新布局，完成 CC1、U26、U1 和负载回流，对照现有实布四层方案。
2. 连续验证低线、控制环路和故障切断。优先消除输出掉压和重复故障热应力，再更新原理图及仿真映射。
3. 为高压阴极段完成封装/绝缘选型并复核实物管座。按真实机械与绝缘约束完成剩余铜线并重跑原生检查。

[Gate 0 安全评估](GATE0_SAFETY_ASSESSMENT.md) · [阴极驱动验证](CATHODE_DRIVER_VALIDATION.md) · [制造阻塞](MANUFACTURING_BLOCKERS.md)
