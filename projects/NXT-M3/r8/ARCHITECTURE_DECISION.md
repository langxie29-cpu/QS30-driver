# NXT-M3 R8 分立阴极架构决策

## RECOMMENDED ARCHITECTURE

保留三块 STM32C011F4P6 自主三管板、每板独立高压切断和 RS-485 模块网络。5 V 外部输入 + 3.3 V 逻辑 + 分立阴极开关继续列为研究目标。下一项设计研究候选是四路 MMDTA42-7-F、SN74LVC595APWR 与 3.0 kΩ 串阻/10 kΩ 下拉。G0 当前 **REWORK**，正式工作流 **HOLD**。 [Gate](GATE_STATUS.json) · [批准调用后的续作](GATE0_CONTINUATION.md)

## ACCEPTED / REJECTED COMPONENTS

|问题|判断|
|---|---|
|1. MMDTA42 适合静态阴极吗？|300 V 开路耐压适合保留为候选。1.5–3.3 mA 的跨温 VCE(sat)、热漏电、双裸片互热及连续故障 SOA 未达到资格。|
|2. 3.3 V 74HC595 可靠吗？|SN74HC595PWR 处在推荐工作范围，共轨标称逻辑允许。以 3.3 V 直接承担带载基极驱动和部分掉电仍缺证据，当前 REWORK。SN74LVC595APWR 带载保证和 Ioff 为后续证据更强的候选。|
|3. 10 kΩ 基极串阻合理吗？|拒绝该冻结值。理想 3.3 V 算例有 0.199 mA，达不到 3 mA/10 的 0.300 mA。3.0 kΩ/10 kΩ 重算为 0.361 mA，仍需实际器件条件闭合。|
|4. 能否保证 30 路正常关断与故障安全？|架构可提供 30 路静态功能。默认 /OE、基极下拉、失电隔离和独立去能均待证明。C–E 短接后 /OE 不能切开阴极。|
|5. 双路是否更好？|每板少 15 个晶体管封装和贴装点。双路引脚间距、互热、双通道共失、返修及国内供应是代价。没有匹配成本/安全证据支持正式优先。|
|6. 可验证节约多少？|单套 A 的冻结驱动 IC 子集 US$26.43。C 初始候选有源子集 US$14.76，LVC 重算路径 US$17.36。完整成本、同渠道归一化节约和与 B 的量产比较为 UNKNOWN。|
|7. 5 V 能取消 AUX12 吗？|分立逻辑与阴极开关无需 12 V 偏置。全机仍需验证栅驱、输入保护、掉电状态和独立许可，全拆 AUX12 为 HOLD。|
|8. 可进 PCB 吗？|当前 Gate 0 REWORK。Gate 1 和 Gate 2 尚未进入。|
|9. 保留哪些 UNKNOWN/HOLD？|低流饱和/温度、鬼影阈值、掉电、短路/线性区 SOA、外壳绝缘、5 V 冷启、采购报价和正式计费模型验证。|
|10. 最小有价值验证？|冻结低压四路等效负载准备，先把新组合的 VOH、基极电流、/OE 上电和失电、许可链分别闭合。取得低流全温和高压热泄漏/SOA 证据后再决定是否正式进入 G1。|

## EVIDENCE-BASED COST SAVINGS

公开报价显示离散有源件子集可降低，但每板有 79 个有源及偏置贴装点和至少 4 个本地去耦。以原样 A 为参照，LVC 的单套有源子集差为 US$9.07，尚含不同卖方、不同日期和不同可交付条件。剩余电阻、封装、贴片、辅助电源、独立安全、板层、返修、税运、NRE 需要完整报价。真实整机节约为 **UNKNOWN**。 [逐量成本](DRIVER_COST_COMPARISON.csv) · [候选 BOM](DRIVER_BOM.csv)

## REMAINING SAFETY RISKS

195 V、最小 19.8 kΩ 与管短接下，半导通 BJT 的负载线峰耗散约 480 mW。对照原厂指定板 300 mW，属于足以阻止资格的反例。三组独立切断、泄放、上电监测和残压再 ARM 必须闭合。 [故障证据](HV_DRIVER_SAFETY_REVIEW.md)

## GATE STATUS

G0 **REWORK**。G1–G3 **NOT_ENTERED**。制造 **ENGINEERING HOLD**。 [状态](GATE_STATUS.json)

## GIT BRANCH AND SHA

分支 `nxt/nxt-m3-5v-discrete-cathode-r8`。基准 `bfaa22d1080544b754c8809873c136ee7247688a`。交付 SHA 从本工作树的 `git rev-parse HEAD` 读取。

## NEXT DEVELOPMENT ACTION

以已有 3.0 kΩ/10 kΩ 组合和 3.3 V 共轨为边界定义低压等效负载验证，分别要求 3.0/3.3 mA 及八路并发源电流；补齐厂商或独立低流/热态证据。把 /OE 的正常关断与独立硬件 HV_PERMIT 的故障去能分开验收。 [四路验证门槛](FOUR_CHANNEL_PROTOTYPE.md)
