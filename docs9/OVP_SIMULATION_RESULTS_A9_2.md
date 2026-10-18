# REV.A9.2 实际SPICE执行结果

**执行完成，保护工程结论FAIL。** 已用官方ngspice47实际运行基线/修改后电路和独立泄放测试，未以计算公式代替执行。当前错误CS和锁存过流阻止高压功能签核；正常172V启动/稳态、有效六/九位负载调整及反馈失效后的自主过压峰值均未通过验证。

最初PATH、Program Files、LocalAppData Programs和卸载注册表均未找到LTspice/ngspice。随后取得官方便携版ngspice47，`--version`成功，未安装系统服务或修改系统PATH。归档SHA256 `59225971bd68cdd1199443649aa4615a9e6d684933f205ab49006a3942518f5a` 与官方SourceForge下载页一致；可执行文件路径/哈希、命令和限制见 `sim/a9_2/environment.json`。首次latest/download返回源代码tar.gz而非Windows二进制；改用明确47_64.7z。Windows tar解压对部分空文件名返回错误，提取出的console程序经版本和真实电路运行验证可用；这些环境限制不隐去。

全部模型/实际引脚次序/假设详见 [MODEL_LIMITS.md](../sim/a9_2/MODEL_LIMITS.md)。UC3843、LM393、TL431为功能等效，BJT为通用Gummel-Poon模型，实际Q21/Q22/Q25再生拓扑保留，没有用数字锁存器取代。MOS/二极管为有明确限制的通用等效，不能签核温度、SOA、真实开关尖峰。每个子目录独立保存circuit.cir、command.json、ngspice.log、波形PNG及数值数据；失效run也保留。

| 证据run | 实际执行场景数 | 执行有效性 | 用途 |
|---|---:|---|---|
| baseline | 17 | FAIL，电流向量导出错误 | 首次错误不删除；rc=0不是成功证据 |
| baseline_repaired_vectors | 17 | 完成，中间模型 | 修复.save/向量大小写，尚未加入最终D4/UVLO等效 |
| a9_2_actual | 17 | **全部作废** | UVLO无迟滞在约1.002ms触发timestep too small；旧解析器错误PASS，见invalidated_runs.json纠正记录 |
| a9_2_uvlo_repair | 17 | 完成，中间模型 | 加入8.4/7.6V迟滞；最终D4尚未加入 |
| baseline_final_model | 17 | 17/17有效、rc=0 | 基线XML/CSV，同一最终模型与修改后对比 |
| final_actual_model | 17 | 17/17有效、rc=0 | 最终XML/CSV，包含实际D4二极管对和终点检查 |
| comp_precharged | 7 | 7/7有效、rc=0 | C15初始4V的独立OVP负载测试；不是实际转换器已进入稳态 |
| full_ref_corners | 2 | 2/2有效、rc=0 | TL431通用C级2.440/2.550V、R±1%、C±20%、β40/200的更外层角点 |
| discharge | 6 | 6/6有效、rc=0 | 无残余供能的被动泄放实验，其中单一泄放开路测试失败 |

共117次ngspice调用；最终直接比较34次，加上预充7、外层角点2、泄放6，共49次用于本轮最终结论。中间假设变更和无效执行不能混作49次“保护通过”。中间两个角点使用2.445/2.545V；更外层2.440/2.550V结果在full_ref_corners，不能把较窄扫描说成完整TL431C范围。

最终成功判据：rc=0、日志无Error/aborted/timestep too small/failed、实际`.meas end_time`达到请求终点。曾发生的中止不能被linearize补出的终点或返回码0掩盖。原始JSON/曲线没有删除，`invalidated_runs.json`明确指出哪些不能使用。解析器回归检查与最终结果复验见`sim/a9_2/verification.json`。

| 场景 | 执行结果/观察 | 电气结论 |
|---|---|---|
| 9位正常启动，80ms | 基线VREF_UC约2.505V、母线末值14.220V；修改后VREF恢复约5V、母线末值15.592V、峰值16.935V | **FAIL**，未建立172.183V；当前CS实际来自SW_HV，模型约15.69V，远超过1V工作阈值和6.3V绝对最大；真实芯片输入钳位/损坏未建模 |
| 空载/6位/9位 | 三种请求已分别运行，启动失败下三曲线近同；管等效为125V维持+20k支路，未起辉时无管电流 | **FAIL/未验证有效负载调整**，不能把相同的低压输出当三种负载通过 |
| 11.4/12/12.6V与输入阶跃 | 11.4V末值14.764V，12.6V末值16.419V；25ms从11.4到12.6V已执行 | **FAIL**，未调到目标；行为参考源在某些角点有数值过冲，本模型不能用于参考瞬态精度签核 |
| 6→9位负载请求 | 25ms请求跳变已执行，因母线低于125V无真正气体管负载阶跃 | **FAIL/阻塞**，需要正确CS和真实起辉/维持/熄灭模型后复验 |
| FB上臂开路、下臂短路 | 各自已执行；末值约15.631/15.591V，仍受错误CS限制 | **不能判保护通过**，没有正常运行态转故障的自主OVP动态，保留FAIL |
| OVP170→230V强制斜坡 | 基线正常低HV即拉低SET误置位；修改后检测与SET低同在13.62ms（保存采样10us） | 极性更正得到模型支持；**不是整机保护通过** |
| 上电已有230V | 独立强制源场景已执行，保护可置位；不能移除理想外部电压源 | 初始过压检测有响应，锁存过流仍FAIL |
| 锁存保持/恢复 | HV先升230再降170，25–27ms复位脉冲；40/60ms锁存仍约9.573V，Q25峰值约22.7mA | **FAIL**，未可靠复位；再生支路缺限流已超额定，不能按理想SCR逻辑判定工作 |
| OVP_RST卡高/请求卡高 | 请求在1ms后持续高；独立OVP仍可拉低HV_EN。复位卡高时Q21/Q22仍约0.8A量级模型外推 | 有独立硬件作用，但**电流/恢复FAIL**；不代表GPIO卡高安全已签核 |
| MCU 3V3掉电 | 20ms3V3降到0，模型FAULT/EN关闭；40ms DRV约0.177V，HV_IN约3.112V | **HOLD**：模型未含真实GPIO/CMOS失电反灌、共模失效及MOS体二极管 |
| 输入断电 | 20ms断12V，80ms HV_IN约0.0079V，但母线仍约15.586V | 执行成功；当前母线未升高，不能据此证明工作高压下断电安全，另见泄放实验 |
| 容差/延迟/峰值 | 见下表，独立注入230V峰值由夹具规定 | 静态/动态裕量不足，**HOLD/FAIL**；自主输出峰值待正确功率级后验证 |

延迟采用C15预充4V的独立测试，避免把本来未达到PWM启动电压的COMP当作“快速关断”。保存曲线为10us等间隔抽样，精度不优于10us；全分辨率母线/BJT极值同时由ngspice.meas写入原生日志。下表是仿真观察，不是实物时间保证；BJT已过额定，数值仅用于定位趋势。

| COMP预充测试 | 实际OVP_SNS越参考时的强制母线 | 越参考→COMP低于模型1.4V条件 | 越参考→HV_IN低于7.6V |
|---|---:|---:|---:|
| 标称，comp_precharged/ovp_ramp | 212.15V | 3.28ms | 8.34ms |
| 较晚角点，comp_precharged/corner_late（VREF2.545V） | 222.95V | 7.15ms | 8.13ms |
| 较早角点，comp_precharged/corner_early（VREF2.445V） | 201.575V | 1.88ms | 8.55ms |

外层full_ref_corners使用2.550/2.440V，检测时刻分别15.11/12.15ms，对应强制母线223.325/201.125V。Q21/Q22通用模型仍约0.79A，超过200mA额定；**不得把超过额定后未烧毁的SPICE器件当作实物仍能锁存/关断的证明**。静态阈值的计算仅作核对：含R±1%和TL431C范围约190.27–206.86V，尚未叠加比较器失调、温漂和动态过冲，旧窗口不再可直接使用。

上述230V峰值是VFAULT夹具强制输出，既不能判保护能钳住230V，也不能当实际升压器峰值。要关闭此HOLD，必须先修CS/锁存，再在真实功率级故障注入中测峰值、传播延迟、续流与器件SOA，满足HV5622推荐≤220V并保留对绝对最大230V的明确裕量。

被动泄放结果（真实ngspice；只保留泄放支路，忽略反馈/检测分压的额外放电，假设转换器已完全停止供能；50V只是本次观察参考线）：

| 场景 | 初始电压/电容/泄放 | 实测首次≤50V | 结果边界 |
|---|---|---:|---|
| 三模块全部连接 | 172.18V /20.3uF /50k | 1.25596s | 理想被动支路通过观察条件，接触安全仍未认证 |
| 高RC角点 | 220V /24.36uF /50.5k | 1.82296s | 忽略残余供能；非正式允许时间指标 |
| 一支泄放开路 | 172.18V /20.3uF /66.667k | 1.67396s | 并联其余支路仍在 |
| 主板独立 | 172.18V /20uF /200k | 4.94696s | 12s时约8.572V |
| 主板独立且唯一泄放开路 | 172.18V /20uF /近似开路 | 12s内未达到 | **FAIL**，无其他分压/泄漏时仍172.18V；不是实际整机所有泄漏全都消失的断言 |
| 拔下单模块 | 172.18V /.1uF /200k | 0.0247396s | 接触安全、真实电容/插头可触及仍需实测 |

实际执行入口（每次run拒绝覆盖既有目录，均rc=0；逐次ngspice命令/rc/错误文本以各子目录为准）：

```powershell
python design9/safety_sim9.py --run baseline_final_model --native-run a9_2_before --csv sim/a9_2/baseline_netlist.csv
python design9/safety_sim9.py --run final_actual_model --native-run a9_2_final
python design9/safety_sim9.py --run comp_precharged --native-run a9_2_final --precharged
python design9/safety_sim9.py --run full_ref_corners --native-run a9_2_final --precharged --cases corner_late,corner_early
python design9/discharge_sim9.py
```

脚本是可复跑入口，现目录已存在时要换新的run名称；discharge脚本故意拒绝覆盖，复跑应选新目标目录/版本。每个.cir也可独立重跑。最终签核仍需：确切器件/温度模型、合理限流锁存、硬件安全复位、正确CS与斜坡补偿、实际磁件/电容/寄生、气体管迟滞、比较器共模/失调、MCU失电输入以及线束/失地/单故障覆盖，详见HOLD_REGISTER。
