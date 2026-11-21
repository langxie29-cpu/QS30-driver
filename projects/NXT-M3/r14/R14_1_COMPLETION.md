# R14.1 工程结论

**R14.1 PARTIAL / HOLD** · **EVT_RELEASE = HOLD** · **MANUFACTURING_RELEASE = HOLD**

本次直接基于 `d203259673981fc9dc7dcc8ede4780305f21c041` 继续。更新了原生 PCB、三张原理图的封装关联，以及 Q1、U11 的局部封装库。原生 XML 网表逐针映射与该基线一致。J5 GPIO 及高压电源拓扑沿用基线。R40 与 U11 仍为 DNP。

## A · Q1 电气连通已闭合，绝缘保持 HOLD

KiCad 铜连通引擎核对六个端点对，结果为 6/6。U20 QA 到 R100，R100 和 R200 到 Q1 基极，发射极回到 R200 地及 U20 地，集电极到 V1.3。Q1 的 1=B、2=E、3=C 对应晶导 C4749118 器件引脚。只向三块焊盘外侧延伸铜，各增加 0.875 mm，保留原 1.475 × 0.60 mm 焊膏和阻焊开窗。集电极走线在外层，换层使用通孔。其余 29 路维持原有封装。 [铜连通与焊盘审计](evidence/r14_1/terminal_audit.json) · [晶导器件资料](https://www.lcsc.com/datasheet/C4749118.pdf)

原生 DRC 仍报告 Q1 集电极至基极、发射极两处 0.6552 mm，低于现有 2.00 mm 筛查。器件工作时的内部功能绝缘需覆盖约 170 V 母线和未验证的瞬态。铜几何值还须结合实际引脚、焊脚、阻焊偏移、板材 CTI、污染等级及涂覆样片。保留规则、热态 SOA 和绝缘 HOLD。 [原生 DRC](evidence/r14_1/DRC.rpt) · [绝缘协调](INSULATION_COORDINATION.md) · [IEC 60664-1](https://webstore.iec.ch/en/publication/107319) · [IEC 60664-3](https://webstore.iec.ch/en/publication/26148)

## B · 急停输入至锁存输出已布通，完整链路保持 HOLD

已核验 J6 常闭回路、Q35 输入与参考地、Q35 到 U9 的 `FAULT_N`、U9 到 U8 的 `LATCH_CLR_N`、U8 到 U11.EN 与 U15 许可的 `ARMED`。U15 到消隐链的 `PWM_PERMIT`、U10 到 Q31 栅极及 Q31 漏极到四颗 595 的 /OE 均有实际铜连接。U11 IN 已接到 R40 下游端，OUT 已接到 C28。U8 采用同芯片、同引脚功能的 TI DCT 封装，以支持实布。U11 的 IN/OUT 分向铜尾保留原开窗和原器件。 [铜连通审计](evidence/r14_1/terminal_audit.json) · [TI SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf) · [TI TPS25947](https://www.ti.com/lit/ds/symlink/tps25947.pdf)

49 个已登记端点对由 22 个通增至 36 个通。剩余 13 个包括 U14 残压输出、U15 电源与地、HV_READY、显示请求、Q31/R25 返回、U11 的下游 5V_HV、地、OVLO、ILIM、ITIMER。这些开点保留在原生 DRC。断供、残压、正常显示和掉电失效安全均待关闭。 [剩余端点](evidence/r14_1/terminal_audit.json)

0–5 V ngspice 夹具运行了五个工况。开环时清锁存、/OE 拉高、输入开关撤销，保持按下 ARM 跨越恢复时无需软件且不会重新置位。重新按下 ARM 并满足残压释放条件时才恢复。复位、共用故障输入、联锁线短接和 U11 卡通均有原始波形。模型采用理想门、开关与外加比较器状态，未测得真实器件传播延迟、反向供能、机械触点特性、U11 真实切断或实际母线残压。 [夹具测量](evidence/r14_1/proxy/measurements.json)

## PCB 与验证

双层保留严格铜间距的尝试受限于已有铜和细间距焊盘。交付四层 PCB 候选，新增内层只用于低压走线，原 RF 和安装孔禁布区扩展至内层。安装孔坐标和钻孔未变。叠层材料、介质、层间边界及通孔工艺需资格验证。

KiCad 10.0.8 原生 ERC 0 错误 / 0 警告，沿用继承的忽略类别。DRC 由 260 项净距和 365 项未连接变为 253 项净距和 337 项未连接。七项消除由 U8 封装和局部布局变化产生，按对象 UUID 比对新增违规为零。原理图—PCB 一致性 0 项。项目仅校正顶层原理图元数据，规则文件及规则设置核对一致。DeepSeek Harness 只运行 R13 封存模式的只读预检，付费 Worker 调用 0。 [原始 ERC](evidence/r14_1/ERC.rpt) · [原始 DRC](evidence/r14_1/DRC.rpt) · [审计数据](evidence/r14_1/terminal_audit.json) · [Harness 预检](evidence/r14_1/worker_doctor.json)
