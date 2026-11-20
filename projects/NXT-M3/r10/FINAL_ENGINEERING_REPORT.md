# Σ / NXT R10 工程报告

**2026-11-20 · GATE_0 = REWORK · ENGINEERING_RELEASE = HOLD**

R10 以本地 R9 `f74f626d798407439c17ac635eb7946727dec628` 为直接基线。R9 的分立阴极、三管静态、自主 Wi‑Fi、0.91 英寸 OLED 和 5 V 输入继承到一套可以编辑、可以导出网表的 KiCad 工程。三模块组合仍由 R9 的协议模型覆盖。R10 的原理图和有封装器件布局可用于工程评审。

| 项 | 实际结果 |
| --- | --- |
| A. 原理图 | [KiCad 项目](eda/NXT-M3-R10.kicad_pro)与[根原理图](eda/NXT-M3-R10.kicad_sch)含 14 页子电路。完成静态驱动与电源保护候选的物理连接。高压闭环、支路诊断和最终管座仍未收口，维持工程 HOLD。 |
| B. ERC | KiCad 10.0.8 原生运行，0 错误、0 警告，退出码 0。另成功执行网表、BOM、PDF 导出。 [ERC 原始记录](evidence/ERC.rpt) |
| C. 30 路阴极 | 对 4 片 SN74HC595 级联、30 个国产 MMBTA42、两个电阻和每个逻辑管脚逐路核对原生网表。位 30/31 实际 NC。V1–V3 物理管座对应焊脚仍需实物确认。 [阴极逐脚表](CATHODE_MAP.csv) |
| D. MCU 与 OLED | ESP32-S3-WROOM-1-N8、1 A 3.3 V 降压、EN 监督、GPIO0 隐藏按键、3.3 V UART ROM 恢复、看门狗及硬件故障输入、分域 I²C 和有开关的可拆 OLED。天线按板边布置。RF、复位与恢复时序、外设样品和固件移植待验证。 [GPIO](GPIO.csv) |
| E. 高压 | 落图 5 V eFuse 切断、LM5155DSSR、偏置和外部驱动、独立硬件比较、故障清锁、双路泄放、残压取样及阳极限流。R40 开路 DNP。启动、补偿、SOA、热态漏电、失供/反灌、保护角落和残压假低读均待关闭。 [电气与仿真](POWER_AND_FAULT_REVIEW.md) |
| F. PCB | [真实双层预布局](eda/NXT-M3-R10.kicad_pcb)，282 个有封装的器件及四个机械孔候选。无实际铜走线。KiCad 一致性只剩 V1–V3 封装缺失。DRC 失败，292 条规则违规、499 个未连接项和 3 个缺失封装；类别见 [原生摘要](evidence/summary.json)。 |
| G. 机械 | Ø29.6 mm 玻璃，38 mm 节距，实际玻璃包络净距 8.4 mm。拆机座型号、外径、安装高度、焊脚坐标、定位、插入深度及固定方式待实测。OLED 载架、插拔空间、防触碰和墙面尺寸仍为工程占位。 [机械与 PCB 分区](PCB_LAYOUT.md) |
| H. 成本 | 0.91 英寸黄色 OLED 情景，单块 ¥247.38，三块 ¥218.17/块，十块 ¥175.67/块。相比 R9 分别增加 ¥26.84、¥23.72 和 ¥17.38。增量主要来自电源入口 eFuse、数字安全和接口件。整机贴装、OLED 型号、管座及 PCB 供应商报价未取得。 [成本表](BOM_R10_COST.csv) |
| I. 第一次全板制造 | 关闭 P0 器件 SOA、支路诊断、供能与残压保护、绝缘和可触及性。还需确定拆机座管脚和焊盘、通过布局与走线 DRC、实际 OLED/低压验证、工艺与费用资格。 [制造阻塞](MANUFACTURING_BLOCKERS.md) |
| J. 下轮前三项 | ① 核实拆机座实物导通、孔坐标及 OLED 载架。② 完成 R10 原理图对应的低压隔离工装与真实厂商闭环/保护仿真，重点关闭 MMBTA42 热态 SOA 和支路检测。③ 按已确认标准和防护重做关键功率与阴极摆位，决定双层、四层或分板并完成走线复查。 |

## 交付索引

- [完整元件与封装表](COMPONENT_FOOTPRINT_MAP.csv)、[各符号物理引脚](PHYSICAL_PIN_MAP.csv)、[原生 BOM](evidence/native_bom.csv)。
- [机械参数](mechanical.json)、[机械布局图](mechanical_layout.svg)、[二维检查](evidence/mechanical_clearances.csv)。
- [原理图 PDF](evidence/NXT-M3-R10.pdf)、[原生网表](evidence/native_netlist.xml)、[DRC 原始记录](evidence/DRC.json)、[ngspice](evidence/ngspice.log)。
- [复现说明](REPRODUCE.md)、[命令、路径和退出码记录](evidence/commands.json)。

元件状态以表中标注和原理图为准。冻结的是产品方向；晶导候选、实际料号可获得性、器件资格和可制造性仍待工程关闭。当前无实物高压上电、故障注入或高压 PCB 制造放行。
