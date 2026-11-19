# NXT-M3 R8 分立驱动研究报告

**结论为 G0 REWORK，整机 ENGINEERING HOLD。** 两轮离线分别否定原始 10 kΩ 配置与重算 LVC 偏置。重算组合满足限定的电流和漏电算术条件，仍缺真实器件和独立关断资格。 [决策](ARCHITECTURE_DECISION.md)

## 冻结基准

远端 R7 头与指定提交一致。本轮从该提交单独建工作树。R7 原生网表 120 组件、135 网，历史 KiCad ERC 0，原生工程仅到原理图。R7 STM32C011F4P6 和 THVD1410 每板各一片，TMR 1-1212、LT3757A + UCC27511、HV5622PG-G 和三管独立 20 kΩ 参考阳极网络。保留同型三板、独立硬件保护、总计九管静态显示，所有报价均按三套自主模块。R7 典型 12 V 代理运行约 170.056 V、0.282 Vpp，前级 OCP、掉电与残压、真实热工况及 PCB 资格仍开。 [R7 基线](../r7/BASELINE_RECONSTRUCTION.md) · [资格](../r7/QUALIFICATION_MATRIX.json) · [BOM](../r7/FINAL_BOM.csv) · [R6 电气需求](../r6/POWER_REQUIREMENTS.md)

## G0-A / G0-B

原厂 MMDTA42 300 V 额定支持进一步研究，给出的 VCE(sat) 最大值属于 20 mA/2 mA、25 °C 脉冲条件。10 kΩ 即使理想 VOH=3.3 V 也未达到强迫 β=10 的 3 mA 电流。SN74HC595PWR 的 MCU 逻辑标称阈值可按原厂方法插值，3.3 V 带载输出和未供电保护仍有缺口。SN74LVC595APWR 改善证据，3.0 kΩ/10 kΩ 算得 0.361 mA，独立评估的关断漏电上界在假设条件下 0.253 V。195 V 管侧故障负载线有 480 mW 的反例。两颗双管跨温、半导通与基极关断条件仍是下一轮输入。 [MMDTA42](MMDTA42_QUALIFICATION.md) · [逻辑](74HC595_QUALIFICATION.md) · [安全](HV_DRIVER_SAFETY_REVIEW.md)

## G0-C 上游参考审查

固定 Marcin Saj 项目提交 `fc8950f4666dad26a65288d4631fe2a6298ec930`。原理图第 1 页经渲染和原作者 PNG 对照，五片标为 74595D 的移位器件、每片 100 nF、各 QH′→SER 级联、共用 CLK 和 RCLK。DIN、EN、CLK 构成外部三线，原文 EN 接 RCLK，是锁存控制。Arduino 示例 3 从位 39 到 0 发 40 位，取 SRCLK 上升沿，最后 EN 上升沿锁存。每管一个选通位，可持续静态输出。 [原理图](https://raw.githubusercontent.com/marcinsaj/Nixie-Tube-Driver-V3/fc8950f4666dad26a65288d4631fe2a6298ec930/datasheet/Schematic-Nixie-Tubes-Controller-40.pdf) · [示例](https://github.com/marcinsaj/Nixie-Tube-Driver-V3/tree/fc8950f4666dad26a65288d4631fe2a6298ec930/example/Nixie-Tube-Driver-V3-Example-3.ino)

40 路均为 10 kΩ 串阻和低端 NPN，共用地。图中 /OE 接地、/SRCLR 接 VCC，晶体管基极为串阻连接。发布物的器件标签没有可验的精确晶体管型号，基极下拉和独立许可路径在图中缺失。原图标注 1.75×3.30 英寸，PCB 底面照片可辨中央移位器和两侧分布式 NPN/电阻、四组 10 路侧边管接口。可编辑板层、Gerber、爬电间距与热可靠性证据缺失。R8 借鉴串行级联、静态映射和接插件组织，按本地安全要求重做消隐与切断。 [资料与图片](https://github.com/marcinsaj/Nixie-Tube-Driver-V3/tree/fc8950f4666dad26a65288d4631fe2a6298ec930/datasheet) · [版图外观](https://github.com/marcinsaj/Nixie-Tube-Driver-V3/tree/fc8950f4666dad26a65288d4631fe2a6298ec930/extras)

## 预研数量与成本

每板 4 移位器、15 双路晶体管、60 偏置电阻及至少 4 本地退耦。235 至 240 mm² 是约计元件本体面积，用于尺度比较。集成器件本体面积约 100 mm²（A）和 49 mm²（B），均须加外围、布线和安规距离。双路比 30 个单管节约 15 封装/板，封装后故障域、安全间距和更换难度需要独立对照。C 每板至少 83 个上述贴装件。报价计算按 1/3/5/10 套，料号、阶梯、LCSC 倍数与库存证据有据可追。PCB 层数、摆放面积、THT/SMT、完整落地成本与首次开发均保持 UNKNOWN。 [采购模型](DRIVER_COST_COMPARISON.csv)

## 5 V 边界计算

沿用 R7 每板空载 0.465 W、轻载 0.720 W、典型 1.612 W、最大 1.995 W，0.45 W/板低压预算单列。三板满载 HV 约 5.984 W。3.0 kΩ 版本高基极电流估算作为额外余量。板端 4.4/4.75/5.0/5.5 V 与 65/70/80% 效率均为研究参数。5 V、70% 条件下整机满载约 1.99 A。4.4 V、65% 约 2.41 A，含基极余量。三板各 5.5 µF 充至 160 V、50 ms，储能 0.211 J。4.4 V/70% 时仅电容充电约 1.37 A 的平均输入分量。需独立考虑峰值、软启动重叠与实测线损。例如源端 4.75 V、3 A 时，0.117 Ω 的总回路电阻足以使板端降至 4.4 V。 [边界表](5V_POWER_BUDGET.csv) · [USB-IF](https://usb.org/usbc)

Gate 2 前电源设计保持停留在负载和能量预算。UCC3803、TPS40210、LM5155 和 R7 LT3757A 正式选型、电感/开关应力和闭环零伏启动属后续依赖。作者 UCC3803 数据是历史参考范围。 [固定公开参考](https://github.com/drkmsmithjr/NixiePowerSupply) · [电源 Gate](GATE_STATUS.json)
