# 真实器件级安全电路与剩余禁止条件

权威源 EVT01/NXT-PWR-EVT01.kicad_pro；逐针源 design_source.json、pin_connections.csv；当前图由主控创建，Flash草稿仅作对抗输入。全链资格HOLD。不存在万能FAULT行为源。

|功能/实际器件|电气输入→输出、供电与参考|最大延迟/单点故障/状态|
|---|---|---|
|独立OVP U430 TPS3700DDCR|四100k高臂、两430Ω低臂；独立内部400mV参考；INB→OUTB拉低FAULT_RAW_N；V5/GND_CTRL|静态trip180.935..192.107V，18/29µs为典型非max；上臂断线可能失去OVP，195V动态峰值未保证/HOLD|
|故障/运行锁存 U514 SN74HCS74DR|FAULT的/PRE=FAULT_RAW_N，/CLR常V5，RESET时钟采样RESET_DISALLOW；RUN由START边沿采样许可，故障/STOP异步清除|fault的异步置位优先于时钟；从不同时置PRE/CLR来清故障。数据/建立保持/掉电时序与单芯片失效HOLD|
|事件整形 U510 SN74HCS14DR|按钮10k/100n RC后Schmitt，START与RESET独立；STOP为NC闭合至V5、断开下拉|不以健康信号门控按钮时钟，避免一直按住按钮时恢复健康制造边沿；实际去抖/触点粘连与人工按钮MPN仍HOLD|
|许可 U511/U512/U513 SN74HCS08DR|两个残压低证明+支路低证明+独立有效性+新START+FAULT_FREE/FAULT_RAW_N双条件|四个HOLD输入有实际10k下拉，未完成时不会允许启动；外部请求新鲜度/看门狗/完整联锁未完成|
|电源监视 U500/501/502 TPS3808|分别G50监V5、G01分压监V12/RAW24；VDD全部V5，低有效RESET并入FAULT_RAW_N，10n CT|V12trip10.659..11.301V，RAW24trip19.069..20.231V；partial-power/输出保证与总最大关断时间未知/HOLD|
|真实偏置 LM5164DDAR、TPS7A1601DGNR|fused raw经DA1给BUCK_IN，真实12V降压，再5V LDO；不依赖U100先开|12V过压、掉电回灌、UVLO动态与真实电源范围未资格；禁止将未供电开漏高电平当健康|
|5V异常高压 U520 TPS3700+Q5P/Q5A/Q5B+OP520|U520独立由V12/PGND供电；5Vdivider127k/10k→5.326..5.638V；PNP拉起故障，NPN下拉PWM_SHDN/U101_UV，光耦跨到RTN100切U100|处理LDO上臂开路使V5上冲的反例；不是稳压钳位，不能保证HCS引脚永不超过6V。最大传播、热CTR、单故障HOLD|
|输入实际关断候选 U100/U101|U100 TPS26601的RTN100独立；SHDN光耦C到SHDN、E到RTN100；U101 LM5069公共PGND，UVLO被真实三极管禁止|U100 FLT仅诊断，不是未供电健康。Q101 DNP/R111 HOLD，无真实最终开断资格；没有RTN101自动短接|
|PWM禁止 QSD/门驱EN|LT3757 SHDN默认钳低，UCC IN−由默认禁止网络；RUN与PRECHARGE条件才撤禁止|电源轨建立/掉电、所有门极充放电路径仍HOLD；单一门极关闭不能限制Boost被动输入路径|
|温度 U440/U441 TPS3700+RTQ/RTL|NTCLE100E3103JB0，12k上拉、90.9k/10k窗口；低端短路和高端开路均拉FAULT，V5/GND_CTRL|R25±5%、B±0.75%等声明边界下电气trip81.59..89.41°C；贴合脱落、线缆和热热点滞后未证明/HOLD|
|残压 U431/U432 TPS3700|两独立2×330k/4.7k检测，OUTA只在低压主动拉低；Schmitt反相后与两通道/支路LOW证明相与|静态最坏trip58.282V<60V；上臂断/公共GND断可能虚假低，HOLD_RESIDUAL_VALID下拉阻断，双通道并不自动等于有效|
|支路关断见证 U433 TPS3700|L_FEED经30.1k/10k→OUTA，1.564..1.645V阈值|只是电压低证明；参考地断线/旁路漏电/故障开关粘连诊断HOLD|
|固定泄放 RB11..RB23|两个独立149.7k串；3×49.9k2512；HV_BUS→PGND|单串开路、初始最大22.315µF时195→60V约3.977s，含TCR约4.006s；RC静态条件，不含回灌/公共地开路/HOLD|
|状态/接口 TP501..506/JHV|FAULT_LATCH/RUN_TOKEN/PWM/branch/V12/V5焊盘；HV接口无封装，待防触碰连接器|非易失故障记录未实现；焊盘并非可裸露高压测点；外罩/受保护测试接口HOLD|

## 逐针与参考关系

LT3757AEMSE：1VC 2FBX 3SS 4RT 5SYNC 6SENSE 7GATE 8INTVCC 9SHDN 10VIN 11EP/GND。UCC27511物理：1VDD 2OUTH 3OUTL 4GND 5IN− 6IN+，与宏模型 IN+ IN− GND VDD OUTH OUTL 的顺序不同，未混用。

LM5069：1SENSE 2VIN 3UVLO 4OVLO 5GND 6TIMER 7PWR 8PGD 9OUT 10GATE。LM5164：1GND 2VIN 3EN 4RON 5FB 6PGOOD 7BST 8SW 9EP。TPS7A1601：1OUT 2FB 3PG 4GND 5EN 6NC 7DELAY 8IN 9EP。

TPS26601：IN8/9、UVLO10、OVP12、MODE13、SHDN14、RTN15、GND17、IMON18、ILIM19、dVdT20、FLT22、OUT23/24；EP映射自定义逻辑25并接RTN100，厂商EP不编号，库映射显式记录。OUT23/24为并联同一内部节点，ERC声明一个power_out+一个passive，不代表断开其中一路。RTN100与PGND之间无直接网桥，U100设置网络参考RTN100；GND17接PGND。

TPS3700：1OUTA 2GND 3INA+ 4INB− 5VDD 6OUTB。TPS3808：1RESET 2GND 3MR 4CT 5SENSE 6VDD。VOS618A：1LED-A 2LED-K 3E 4C。光耦型号使用厂家存在的VOS618A-3X001T，不使用不存在的-4X001T；其25°C CTR档不是热态最大传播保证。

PGND/GND_CTRL/GND_KELVIN/GND_DRV由三个真实网桥在指定星点相接，区别于浮动RTN100。LT3757 VIN及UCC VDD供V12，INTVCC独立7.2V，避免强迫12V超过VIN+0.3V条件。所有L_FEED之后附加储能必须重新登记故障能量。

## 明确未实现

HOLD_FULL_SAFETY_VALID、HOLD_RESIDUAL_VALID、HOLD_PRECHARGE_OK、HOLD_INPUT_CUT_VALID是有物理下拉的未完成许可端，不是已经完成的安全模块。独立预充/旁路、真实线性FET/限流、最大关断时限、12V过压防护、残压检测开地诊断、请求新鲜度/看门狗、非易失记录、完整安全单故障链均未完成。原H01–H10与24V-07/08/09/10及制造HOLD保持。模块器件化是可检查的进展，不是安全认证。
