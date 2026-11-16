# Agent B：独立安全层器件连接候选

2026-11-17。状态 **PARTIAL DESIGN / HOLD**。`pin_connections.csv` 是逐引脚审查数据，不是完整电气网表、嘉立创原生图或可制造BOM。`netlist_scope.json` 逐项列出尚无实际电路的硬件接口。不能把这些接口赋理想电平后得到的逻辑结果解释成真实保护链通过。

本轮完整读取 S06 电路增量、S06B 报告及配置、S06C 接口记录，核对 S06D/E/F 后续功率结论。后续功率候选已为 LT3757AIMSE#PBF，S06F 仍有数值轨迹不收敛和真实硬限流缺证。UCC28C43/UCC27511 引脚表只是旧候选适配层，不将其强行替换为已通过的功率级；若选择 LT3757，必须另审核 SHDN/SS/VC/GATE 全链，不能直接搬用 UCC 的 COMP/IN− 接口。

## 电路边界及默认执行

U100 主输入 eFuse 保留内部上电自举，禁止靠尚不存在的 AUX/MCU 许可启动 U100。U101 高压支路独立 eFuse 以 8.2k SHDN–RTN101 默认关。RTN100、RTN101 均不是逻辑地；设置电阻、电容和裸焊盘回各自 RTN。GND17 接系统地。NC 引脚各自独立，不合并为公共网络。FLT 暂停在 `HOLD_U100/101_FLT_ISOLATION`，不再向 USB/3V3 直接上拉。

U401 光耦隔开 HV_INPUT_PERMIT 与 RTN101。LED820Ω；晶体管 C 经100k取24P，E到SHDN。失去LED电流应撤销许可，但输出短路/漏电、CTR老化及饱和存储时间仍需真实器件验证。它不是快过流路径。UCC27511 IN−47k上拉AUX12，只有Q201被完整硬件许可驱动时才拉低；OUTL经2.2Ω放栅，OUTH经10Ω充栅。RGS10k接真实Gate–Source，驱动地回分流负端Kelvin。源极分流产生的VGS偏移、负压钳位、寄生和Miller仍是HOLD。

U111 DRV12开关 EN10k下拉；QOD1k到DRV12只是放电候选，不能保证反向隔离。跨DRV12的HV5622和电平转换器控制输入必须另有无供电隔离及默认消隐；本表没有把BL接口伪装成已完成电路。所有IC本地旁路、元件精确订购码/有效容值和电源负载仍须补齐，不可依赖CSV自动生成原生图。

## 独立检测

U420/421/422沿用S06独立AUX、DRV、3V3窗口值。开漏输出上拉AUX12，各轨分别成网，不能把DRV窗口加入DRV自身建立条件。AUX域到3V3的正向有效证明/电平转换未释放；比较器断电时开漏释放不表示健康。

U430独立OVP：HV_BUS→232k→232k→OVP_SENSE→1k→GND。与正常反馈的取样走线、分压元件和比较器基准分开；不能从FB_NORMAL分支偷取OVP输入。名义186.0V，TPS3700 INB−过压时OUTB拉低。静态边界分析见`threshold_screen.json`。输入电容暂不添加，避免无依据延迟；布局寄生、钳位及单电阻开短路仍需资格。上臂断路会丢失OVP；独立于反馈不等于自身单故障覆盖，必须保留证明测试/第二检测通道HOLD。

U431/U432残压为两条独立分压、独立芯片：各 HV_BUS→68.1k→68.1k→sense→1k→GND。名义54.88V，只在两条通道均报告低于门槛、有效供电和诊断均成立后才允许人工复位。门槛是暂用工程筛查，**60V不是认证可触碰标准**。两通道不消除共同地开路、板面污染、同一连接器和未供电问题。AUX断电时禁止输出“残压安全”；USB单供电不能把无电的残压比较器当安全。外部独立电表与完整放电验证仍必需。

U440/U441各对应MOS和电感独立NTC。3V3经10k上拉传感节点，NTC到地；INA+直接看低门槛，INB−经65k/10k看高门槛。低电压表示热/短路，高电压表示传感器开路；2个输出合成该传感器的窗口故障。名义健康电压约0.4..3.0V。传感器准确MPN、R(T)/公差、接触热阻、热惯性、自热及温度上限尚未定，因此只冻结电压故障检测结构，**未冻结温度阈值**。不得用10k/B3950理想曲线代替真实温度保护。3V3过压/欠压也必须撤销许可，不能让比率改变被当成温度恢复。

## 锁存、请求与复位

U460/U461采用SN74LVC1G74DCUR。真实脚序是1CLK/2D/3Q反/4GND/5Q/6CLR低/7PRE低/8VCC，已从原厂图核实；不能套用其他74系列的记忆脚序。D与PRE接3V3，CLR外部10k下拉，禁止同时拉低PRE/CLR；上电Q并无保证，必须由独立电源有效链持续清零。U460 Q=FAULT_MEMORY_OK：故障异步清零，仅允许合格人工复位边沿置1。U461 Q=START_MEMORY：故障/停止/请求撤销均清零，人工复位绝不能给它时钟。两者需要不同实体按钮或严格的释放后新边沿判据。

**不能将条件直接AND进按钮时钟**：按钮一直按下、故障消失时AND上升沿会误复位；必须先见按钮释放，再接受下一次新按下并做消抖。RESET_QUALIFIED_EDGE、START_QUALIFIED_EDGE因此仍是明确未实现接口，不能在EDA中随意直连按钮。复位许可需24P/AUX/3V3、温度窗口、互锁、请求低、两个残压通道有效且安全、输入开关关断回读、无持续故障同时成立。DRV12此时应关闭，不把DRV_OK作为清锁前提形成死锁。

U470 TPS3431SDRBR 是硬件失活检测候选：EN/SET1硬接3V3，CWD经10k到3V3，WDI来自动态心跳且10k下拉；WDO低必须异步清除U460/U461。固定超时170..230ms，仅属该候选预算，是否足以保证当前功率级能量必须另定；WDO会自行释放，因此不能直接代替锁存。初次有效心跳见证、请求先低后新边沿、MCU异常重启、程序跑飞但外设继续发心跳的限制均未解决，不能称其为完整程序执行监控。不能把EN/SET1接MCU允许禁用。

U480..484 AND树仅给出可审查接法：BASE_PERMIT=BASE_GOOD·FAULT_MEMORY_OK·INTERLOCK_OK；DRV_PERMIT=BASE_PERMIT·START_MEMORY·REQUEST_VALID；HV_INPUT_PERMIT=DRV_PERMIT·DRV_OK·BASE_PERMIT；PWM_STAGE_ALLOW=HV_INPUT_PERMIT·DEMAG_OK·PRECHARGE_OK；PWM_PERMIT=PWM_STAGE_ALLOW·LIMITED_START_OK·BASE_PERMIT。HV输入许可不能等待PRECHARGE_OK，否则24V开关关闭时预充永远无法完成；该死锁已在B轮自审修正。PRECHARGE_OK只约束PWM。**若DEMAG_OK只在每个脉冲后短暂成立，不得用AND直接截断任意PWM，此处需要经资格的脉冲仲裁器**。既有单脉冲/真实退磁检测缺失仍阻塞功率运行。

BASE_GOOD、故障聚合、有效正逻辑转换、消抖/重新武装、持久支路OC、关断回读、预充电压电流时间窗口、退磁、受限启动、COMP默认钳位、BL默认及模块隔离仍待完整器件电路。这些不是已完成设计的省略线，而是禁止投板的明确HOLD。当前可设计物理无Boost链的低压验证夹具，但释放验证板前仍须关闭其实际使用电路的封装、供电和限制能量问题。

## 器件依据与传播预算

原厂全文/版本/哈希在`../sources/device_qualification.json`，10份PDF逐项存档。8个指定候选均经本轮原厂在线核查；附加触发器/看门狗也核实。来源： [TPS2660](https://www.ti.com/lit/ds/symlink/tps2660.pdf)、[TPS3700](https://www.ti.com/lit/ds/symlink/tps3700.pdf)、[TPS3890](https://www.ti.com/lit/ds/symlink/tps3890.pdf)、[UCC28C43](https://www.ti.com/lit/ds/symlink/ucc28c43.pdf)、[UCC27511](https://www.ti.com/lit/ds/symlink/ucc27511.pdf)、[TPS22810](https://www.ti.com/lit/ds/symlink/tps22810.pdf)、[SN74LVC1G11](https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf)、[VOS618A](https://www.vishay.com/docs/83465/vos618a.pdf)、[SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf)、[TPS3431](https://www.ti.com/lit/ds/symlink/tps3431.pdf)。

UCC逐周期限流的70ns上界仅适用于原厂规定比较器条件，不包括RC、逻辑、门驱、MOS截止及布线。TPS3700的18/29µs为表内标称延迟，不是完整OVP最大响应保证；450µs启动有效上界也不能当作过压响应时间。TPS3890的典型18µs不可升级为全温上界。光耦25°C CTR/漏电/饱和开关数据不能外推热态最大延迟。SN74LVC的Ioff仅覆盖指定VCC=0条件，不证明任意慢跌落/半供电输出为低。完整预算必须把最大输入能量、C最小、阈值最高、延迟最大和泄放开路共同计入：没有这些上界就不能证明峰值≤195V。

## 双执行路径的物理限制

关栅不能关掉D-S已短的MOS。U101失效导通时关栅仍有24V→L→D→C被动供能；若同时输出短路，关栅不阻止直通。MOS短路时只靠输入开关清除持续输入，已有输出电容还会经整流器/负载等路径保留或释放能量。两执行路径共用检测、供电、接地、许可逻辑也存在共同故障。上游U100或保险丝的兜底响应必须与故障电流/供源限流/I²t及热SOA匹配，不能因为有保险丝就称冗余。故障去除和电源复电均不得自动重启；输出储能独立处理，泄放开路单故障及模块拆除要求进入24V-10。

## 迁移/制造阻塞

精确可购料与立创编号全为`HOLD_UNVERIFIED`，未编造C编号；元件包名不是已核对嘉立创封装。需按本轮原厂机械图逐针核对符号/焊盘1/EP/方向、建立本地受控库和测试点，再做真实ERC。当前未创建原生工程、未运行ERC/DRC。HV间距必须先确定标准、污染等级、材料组、海拔、瞬态和防触碰结构，不从170V直接猜一个毫米值。网表中的分压电阻值不代表其工作电压、脉冲、功率和温漂订货码已经资格化。
