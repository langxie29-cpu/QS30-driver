# Σ / NXT R9 架构评审

**架构 LIMITED_PASS · 硬件资格 REWORK · 制造 HOLD**

三块板各自包含下面完整链路。控制端只提供数据、时间协调和组事务。每块保存独立凭据、配置及应用镜像，一块重启不重置其余模块。跨板 HV、SPI 或 I²C 连线不进入此架构。

```text
5 V 本地输入 ┬─ 前端保护 ─ 3.3 V 降压 ─ ESP32-S3 ┬─ I²C ─ OLED（独立断电/复位接口）
             │                                   └─ SPI + latch ─ 4 × 74HC595 ─ 30 × MMBTA42
             └─ 真实切断 ─ 升压 ─ HV 母线 ─ 三支独立阳极限流 ─ QS30-1 × 3
                           │          └─ 双永久泄放 + 残压联锁
本地硬件 OVP/OCP/支路故障/欠压 ─ 锁存 ─ 输入切断、PWM 禁止、/OE 消隐
```

## MCU、时序与 RF

- **ESP32-S3-WROOM-1-N8**，8 MiB Quad SPI Flash、无 PSRAM、模组 PCB 天线、18 × 25.5 mm。N8 用双应用槽和 OTA 元数据，初始规划每槽 3 MiB，剩余放 boot/partition、NVS、密钥/日志，实机校验分区尺寸、签名/回滚与完整镜像。检查 N8 模组丝印及来料渠道。模组规定 3.0–3.6 V、外部供电能力至少 500 mA，原厂表 6-4 记录 355 mA 的 25 ℃、3.3 V、802.11b 满占空 TX 条件。设计暂给逻辑总轨 0.60 A 峰值并选持续额定 ≥1 A 的降压候选。实测 WIFI TX/重连与 OLED 同时动作时的模组焊盘电压。 [Espressif 模组规格](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- SPI2 建议 GPIO11 MOSI、GPIO12 SCLK、GPIO10 RCLK（GPIO 手动锁存），GPIO13 为消隐请求，GPIO14 为硬件看门狗心跳请求。I²C GPIO8 SDA、GPIO9 SCL。GPIO4 OLED 电源/复位请求、GPIO5 硬件 FAULT 输入、GPIO6 逻辑 PGOOD 只读。GPIO19/20 留 USB D−/D+，GPIO43/44 留 UART0。GPIO0、3、45、46 保持 strap 合规，EN 外部监控加厂商建议 10 kΩ/1 µF 起点，预留 GPIO0 下载。GPIO26–32 留模组 Flash 相关用途，GPIO48 等未分配。确认原生封装 pin number 与 board variant 后才冻结网表。 [Espressif 模组规格](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- PCB 天线优先伸出板边。模组图中的地与禁布关系照用，外壳装配天线周围至少留厂商建议的 15 mm 空隙。OLED PCB、金属面板/固定件、线束、高压开关热环路和相邻模块均进三维核对。测试装壳后三块并发的 RSSI、重连、吞吐及端到端切换时序。 [Espressif PCB 布局](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)

## 74HC595 接口与默认消隐

首选计算对象 TI SN74HC595PWR ×4，MCU 与 HC 共 3.3 V。依 TI SBAA808 对 3.3 V 的插值 VIH≈2.358 V、VIL≈0.942 V，ESP 高阻负载 25 ℃点 VOH≥2.64 V、VOL≤0.33 V，名义静态余量 0.282/0.612 V。输入阈值插值、共轨压降和温度角都进入低压实测。起始 SCLK 1 MHz，源端阻尼 22–47 Ω 候选，短线与共地。SER=14、SRCLK=11、RCLK=12、QH′=9；远端字节先移入。/SRCLR=10 只清移位寄存器，复位后在 /OE 关态下打 RCLK 锁存零；先写满 32 位再锁存。R8 保留旧通道表用于复核，R9 映射计划为 bit 0–9、10–19、20–29 从左到右三管，30/31=0，实物低压逐位点亮验证。 [TI 数据表](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf) · [TI 3.3 V 应用说明](https://www.ti.com/lit/ab/sbaa808/sbaa808.pdf) · [R8 资格审查](../r8/74HC595_QUALIFICATION.md)

/OE 上拉由本地有效轨供电，硬件组合许可通过开漏下拉后才能显示。硬件许可由低压正常、故障锁存释放、外部有窗口看门狗和 MCU 显示请求共同决定。独立监督输出默认禁止 HV，无 MCU 正向驱动输入切断。高压预充由硬件许可和有效 ARM 条件控制，与逐帧 /OE 区分，普通显示更换不循环启动电源。复位、下载、棕断、编程和 OTA 请求先消隐，随后停心跳并撤销 HV 运行请求。看门狗只由成功完成关键任务和状态检查后的应用路径喂狗，禁止常驻 PWM 喂狗。看门狗超时研究目标 ≤100 ms，实际失效窗含继电/开关时间，待测。GPIO 冻结、外设继续跑及 /OE 卡低都要测试。硬件故障立即并行触发 PWM inhibit 和切断且锁存，网络无法解锁。3.3 V 掉到保证区外时，/OE 与 HC 输出状态进入未知区，由输入断能、基极下拉、储能措施共同隔离。USB/治具/扩展的反向供电和 ESD 路径列入掉电验证。 [安全门槛](SAFETY_GATE_STATUS.md)

## 国产单管筛选

| 项目 | 扬杰 MMBTA42 / C699244 | 山东晶导 MMBTA42 / C4749118 |
| --- | --- | --- |
| 封装与引脚 | SOT-23，1=B、2=E、3=C，样本与封装图待来料核对 | SOT-23，1=B、2=E、3=C，样本与封装图待来料核对 |
| 击穿/额定 | BVCEO ≥300 V @1 mA, IB=0，VCBO 300 V，VEBO 5 V，IC abs 500 mA | BVCEO ≥300 V @1 mA, IB=0，VCBO 300 V，VEBO 5 V，IC 连续 abs 300 mA |
| 饱和数据（25 ℃） | VCE(sat)≤0.5 V、VBE(sat)≤1.0 V @20/2 mA | VCE(sat)≤0.2 V、VBE(sat)≤0.9 V @20/2 mA |
| 截止（25 ℃） | ICBO≤0.5 µA @VCB=200 V, IE=0。国内商家属性栏单位与原厂冲突，采用原厂值 | ICBO≤0.25 µA @VCB=200 V, IE=0 |
| 功耗/热 | 350 mW @25 ℃，RθJA=357 ℃/W，Tj 上限 150 ℃。85 ℃筛选约 182 mW，实装热阻与热态资格待测 | 350 mW @25 ℃，RθJA=357 ℃/W，Tj 上限 150 ℃。85 ℃按该热阻筛选约 182 mW |
| 判定 | 来源可追溯，REWORK | 纸面饱和、漏电和低流 hFE 较好，首轮候选，REWORK |

两品牌 170 V 相对 300 V 余量 130 V，195 V 分析边界余量 105 V。资格关注实际阴极关断尖峰，拟先以 240 V 峰值筛选，预留 20% 额定差额。厂家 ICBO 测试无法外推至高温整支路 ICEO，也无法代表局部线性 SOA。25 ℃饱和测点并非 QS30-1 实际约 1.7–3.3 mA 及全温保证。需取得两品牌批次、热态截止/鬼影、低电流 VCE(sat)、焊盘热阻、脉冲 SOA；样本计划见 [下一轮](NEXT_ENGINEERING_DECISIONS.md)。 [扬杰原厂](https://www.21yangjie.com/pdf/xxh/xxhsjg/MMBTA42.pdf) · [扬杰国内渠道](https://item.szlcsc.com/733936.html) · [晶导原厂规格经 LCSC 分发](https://datasheet.lcsc.com/lcsc/2208091800_Shandong-Jingdao-Microelectronics-MMBTA42_C4749118.pdf) · [晶导国内组装渠道](https://jlcpcb.com/partdetail/5321818-MMBTA42/C4749118)

基极暂用 **3.0 kΩ / 10 kΩ，均 ±1%**。以 VBE=1.0 V、强迫 β=10 和 IC=3.3 mA，要求 HC 带载 VOH≥1.0+3.03k×(0.33m+1.0/9.9k)=**2.306 V**。若 VOH=2.40 V，IB 净值 **0.361 mA**。HC 在 3.3 V、此带载点没有保证值，实测最低 VOH 原则上还需留制造余量。低压测试可采用 2.45 V 指标。取 3.6 V 和基极短地，单路上界 1.212 mA、8 路 9.70 mA/片、30 路 36.36 mA/板。正常三路同时选通同法上界 3.64 mA。以 IOZ 5 µA（原表条件为 6 V）加假设热态支路 10 µA，10.1 kΩ 上压降 0.152 V，只是高阻灵敏度计算。测试上限目标 0.30 V，需覆盖 HC 部分上电/掉电、热态 BJT 与不受控输出。错误多位高由位图一管最多一阴极规则先拦截，随后由硬件支路许可处理；标准总 OCP 对单稳定故障可能失敏。若 HC 未通过，调整阻值或研究保持 74HC595 的缓冲方案，变更成本重算。 [TI 数据表](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf)

电源架构、器件、计算和储能替换详见 [5 V 电源收敛](POWER_COMPONENT_REVIEW.md)。
