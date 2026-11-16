# Agent D 独立软件/仿真验证，2026-11-17

本目录是规格验证与受限器件单元证据，不是实现完整安全链的原理图，不构成功能安全认证。真实高压、采购、PCB制造均未进行。24V-07未通过、08未进入、09/10未通过，制造HOLD。

## 历史输入与本次边界

读取S06C–F报告和S06F执行脚本、原厂driver模型、既有driver单元。S06C的LT3757A只是替代候选，原TI控制器/驱动耦合失败保持；S06F快波形/前历史状态仍不收敛，4次180s超时不能被新低压逻辑试验覆盖。本次32次driver单元不是该功率级重测。所有39次新SPICE只用0–24V电压源；RC用缩放阈值模拟HV衰减，禁止解释为170V实物或完整器件资格。

## 软件闭环：明确暴露后再修正

`safety_model_r1_failed_snapshot.py`保存初稿。A与父审查指出DRV运行掉压必须锁存、残压有效性及支路关断确认缺失；新增同一组对抗测试后`tests_r1_red.log`：245个，241通过/4失败。修正为状态依赖DRV失压锁存，启动/复位检查`residual_valid`及`branch_off_confirmed`；`tests_r2_green.log`及`tests_final.log`：245个全部通过。可以`python reproduce_red.py`重现预期4失败，不改旧证据。

245个包括19个检测谓词单故障、171对有限双检测谓词、32个五输入许可真值组合、23个启动/停止/复位/物理限制等测试。这里“故障”是**外部诊断已成功检测到**的输入假设：绝不代表传感器断线、反馈断线、短路、反灌已经由电路检测到。heartbeat是独立动态监测器输出的抽象值，未实现监测器；GPIO运行卡高且心跳仍有效不会被这个模型识别，只有新启动边沿/死机心跳丢失受测。`faults`的物理覆盖必须另验。两个拓扑断言明确门极禁止无法清除被动充电与MOS硬短路，不能把输出命令为false解释为物理断电。

## 真实TI模型单元

原始TI UCC27511_TRANS，Final1.10、15SEP2015、PSpice16.2.0；实际来源为既有原厂SLUM488包。每例driver.lib SHA256 `8e17d92edd68786189ad99439f4db06b8726fbf911c1282a85027e998c36e9f6`，保持原字节，无括号修补或模型参数调通。ngspice47 / ps兼容 / Gear，默认27°C，仅模型限定温度，没有全温外推。

四种输入：默认禁止、运行IN−故障拉高、执行级高阻由47k拉到AUX禁止、AUX掉电；2/1ns两个最大步长。门极负载5.333nF，10Ω开通/2.2Ω关断/10k下拉，源极0V；**不包含实际MOS/Miller或源极分流压升**，不能继承完整功率级或S06C后替代控制器证明。

预先判据：禁止Vgate≤0.55V；有效门极≥10V；故障命令后300ns以内Vgate≤0.55V，300ns后始终≤0.55V；半步长关断时间差≤20ns。每组执行前preregister.json保存，全部命令/日志/网表/模型/waves.txt存在。

|记录|次数|执行验证|电气判断|
|---|---:|---|---|
|spice_r1，AUX12|8|4 PASS / 4 FAIL|4 PASS / 4 INCONCLUSIVE|
|spice_r2，AUX12|8|8 PASS|8有限PASS|
|spice_r3_aux11p4|8|8 PASS|8有限PASS|
|spice_r4_aux12p6|8|8 PASS|8有限PASS|

r1四次进程rc0且到终点，但ASCII默认打印精度把不同自适应时间写成相同值，严格单调性检查失败。没有把退出0当电气通过；r2仅将输出精度设为15位，保持容限/电路/验收不变重新运行。原始r1 summary遗漏electrical字段，`verification_summary.json`明确补为INCONCLUSIVE，不覆盖原文件。r1/r2来源URL曾误写SLUM030，同一审计明确纠正为历史manifest指向的SLUM488，模型hash未变。其他原始数据不改写。

## 被动路径与泄放失败

`topology_r1`六次及`topology_r2`一次均完成并与独立拓扑/解析结果一致。24V支路开关卡导通时，即使gate=0，输出仍约23.483V；这就是Boost电感/二极管被动路径。正常断开夹具约1.196µV。简化二极管模型只证明通路，不证明eFuse或真实整流器能力；Q漏源短路的源能清除/I²t/SOA与两故障组合仍HOLD。

RC保守忽略正常反馈和检测分压，只计独立泄放。以195V初态按24/195缩放初态/60V阈值，时间常数不变；COUT20µF+5%，模块3×100n+5%；每个200k+1%。这些只是已有设计数值及容差假设，实际MPN温漂/老化/电压额定待审。

|拓扑|解析195→60V|5s设计判据|
|---|---:|---|
|四支泄放，全连接|1.268713s|有限PASS|
|一支开路，仍三支|1.691617s|有限PASS|
|模块全拔，仅主板一支|4.999854s|数学PASS但余量仅0.146ms，工程HOLD|
|模块全拔且主板泄放开路|近无限，6s波形几乎不变|FAIL，保持制造HOLD|
|模块电容仍在，仅主板一支泄放可用|5.074852s|FAIL，`topology_r2`独立追加|

60V/5s仅已有设计判据，触碰安全标准未确定；输出关断仍有储能。必须建立主板独立双泄放支路/故障诊断及模块残压措施，再用真实容差/温升/可触碰要求复测。不能因全连接一支开路通过就关闭24V-10。

## 复现与计数

从仓库根目录：`python -m unittest discover -s projects/QS30-9_24V/safety_r1/verification -p test_safety.py -v`。仿真`run_spice.py --output <全新目录> --exe <ngspice路径> --aux 12`，默认找仓库已有ngspice；禁止覆盖现有输出。`run_topology.py`默认输出固定且存在即拒绝覆盖，复现时复制脚本并显式修改独立输出目录。工具不在仓库CI自动安装，仿真跨平台未宣称合格。`audit_results.py`只重读数据/执行软件回归，不计新仿真；`artifact_hashes.json`覆盖本目录证据。

本次实际39次仿真进程：39次rc0到终点；按保存的严格执行检查35 PASS/4 FAIL。32次driver中28有限电气PASS、4 INCONCLUSIVE、0已判电气FAIL；7次拓扑一致性PASS，其中5项泄放要求3数学PASS/2 FAIL。245个软件测试当前全通过；红轮同245个中的4失败保留。不同层次计数不可相加成“通过安全项目数”。

HOLD：完整硬件时序/独立比较器锁存/复位电路、厂商模型温度和部分供电覆盖、eFuse RTN接口与USB反灌、输出残压监测有效性、真实短路切断、磁件热态、真实反馈断线响应、输出储能/泄放单故障、全器件单故障、原生EDA/ERC/PCB，均尚未验证。

## 独立C审查追加修复

C的`review/test_adversarial.py`四项中初始两失败：健康运行时按RESET未撤销令牌，以及RESET持续按下还能新启动。按故障优先顺序保留硬件锁存处理，随后健康态RESET立即强制OFF且清request/manual边沿资格。相同独立四判据修后通过，最终证据由C保存；本目录245项全量回归再执行。不能以这项软件修正声称硬件RESET电路已实现。

## 工具与重现前置

`tools/ngspice47`不是已跟踪交付，不假设新克隆有仿真器。需独立取得官方ngspice47控制台构建（[官方入口](https://ngspice.sourceforge.io/download.html)），核对`spice_r2/preregister.json`中exe SHA256及`version.txt`，通过`--exe`显式传入；同版本不同构建仍需重新记录hash/日志并复核数值。没有在CI自动下载或称Linux同版本已经通过。原厂模型已逐例归档，runner在历史sources不存在时改用`spice_r2/inhibited_2ns/driver.lib`，仍核对相同SHA。`run_topology.py --output <新目录>`支持全矩阵复现，`--only main_bleeder_only_modules_cap_connected`可单独补充边界；这些命令会产生新的进程尝试，原有证据从不覆盖。


