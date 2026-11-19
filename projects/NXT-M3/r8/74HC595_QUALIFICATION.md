# 3.3 V 74HC595 资格

目标为 TI **SN74HC595PWR**，TSSOP-16，PWR 封装，保留 R7 STM32C011F4P6 模块。SN74HC595 推荐 2–6 V，3.3 V 在其中。其输入、输出、电源排序资格分别处理。 [TI SCLS041J](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf) · [ST DS13866](https://www.st.com/resource/en/datasheet/stm32c011f4.pdf)

|项目|核对结果|
|---|---|
|STM32 → HC 输入|ST 表 50 在合适 CMOS 输出配置、8 mA 条件下给出 VOH≥VDD−0.4 V、VOL≤0.4 V。TI SBAA808 对 SN74HC595 在 3.3 V 的 VIH/VIL 插值得 2.358/0.942 V，共轨标称估计裕量均约 0.542 V。地差、上升沿、过冲和非同序供电仍需审查。 [TI 应用简报](https://www.ti.com/lit/ab/sbaa808/sbaa808.pdf)|
|HC 给基极的 VOH|原厂表 6.5 的小载点是 −20 µA，较大载流保证在 4.5/6 V 等指定条件。3.3 V 同时驱动 8 输出时的负载电平/总电流压降没有直接保证。图和插值不能把 −20 µA 条件用到 0.3 mA 输出。|
|串行与锁存|SER 14、SRCLK 11 上升沿、RCLK 12 上升沿。QH′ 9 接下一片 SER 14，持续输出独立于 /OE。四片 32 位，发送远端位后发近端位。/SRCLR 10 清移位端，需再打 RCLK 才向锁存端送零。|
|默认关断|/OE 13 拉高时仅并行端高阻，锁存保留。R7 的 HV5622 原取下降移位沿，低压 RS-485 协议和 STM32 保留，板内控制与位序须重新验证。MCU 未初始化时，硬件许可断开；/OE 上拉到有效本地 3.3 V、全部基极有独立对地下拉。|
|掉电与反向供电|全掉电时上拉也衰减，不能把 /OE 拉高的正常态当成安全边界。HC 的约束、输入钳位、VCC 顺序和未规定的 Ioff 条件导致反灌不确定。必须隔离独立供电域及处理 A/B/GND 断开。|
|并发全高|3.0 kΩ ±1% 以 3.6 V、基极端 0 V 做短路上界，1.212 mA/输出，八路 9.70 mA/片，30 路 36.36 mA/板。各器件供电、退耦和热需复核。/OE 自身故障、输出卡高和 C–E 短路均由独立高压许可限制。|

**重算路径为 TI SN74LVC595APWR**。SCASE93A §5.5 在 VCC=3.0 V、IOH=−12 mA 给出 VOH≥2.4 V，Ioff 10 µA、IOZ 15 µA 为表中上限且有各自测试条件。3.0 kΩ/10 kΩ、1% 容差在 VOH=2.4 V、假设 VBE=1.0 V 时得到 0.361 mA，达到 3.3 mA/10 算术筛选。22 kΩ 下拉与 15 µA IOZ 加 0.1 µA ICBO 的敏感度上界为 0.336 V。改为 10 kΩ，若另加 10 µA 热态 ICBO 假设，上界 0.253 V。后者小于 0.30 V 的研究线，仍需验证真实鬼影、VBE 和极性瞬态。低电压数字工作、单独的 Ioff 和 POR 规格无法代表斜坡全程。 [TI LVC 原厂](https://www.ti.com/lit/ds/symlink/sn74lvc595a.pdf) · [复算](evidence/runs/offline-discrete-g0/round_02/base_drive_rework/metrics.json)

SN74HC595PWR 在规则电平下仍可作为成本基准。当前资料支持替换逻辑候选进入 **G0 重审**。硬件独立关断、部分供电及 BJT 低流/热资格为 HOLD。
