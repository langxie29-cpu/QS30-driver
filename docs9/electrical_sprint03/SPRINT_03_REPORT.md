# NXT / REV.A9 — Electrical Closure Sprint 03

2026-11-11，Asia/Shanghai。**整机 FAIL/HOLD。实际器件拓扑结论 UNKNOWN；HV-G0 BLOCKED；HV-G1 BLOCKED；HV-G2 FAIL。** 所有电压/电流“测得”均指本机SPICE数值解或对历史原始数据的重算，本轮没有实体高压实验。

## 1. 本轮结论

无法证明现有真实UC3843AN单级Boost能在实际最坏输入与九管负载下稳定、安全地产生目标高压。也没有足够证据证明单级Boost原理本身绝对不可行。当前工程有明确错误CS接线，输入/磁件/供应商与换流模型未冻结，且开环模型资格检查暴露重大参考点与恢复模型敏感性。因此不应继续从完整失效电路搜索Type-II参数。

本轮形成五项可复核结论：

1. 从当前原理图重新导出原生XML并逐脚比对，确认无耦合电感的常规Boost。U20设计订购码其实是 **UC3843AN / DIP-8**；上一轮“只有UC3843泛称”的摘要不完整。厂商仍UNKNOWN。[TI准确订购页](https://www.ti.com/product/UC3843A/part-details/UC3843AN)对应A系列；本轮取得SLUS224H，未将TI默认为实际采购厂商。
2. 九管最大支路功率不是完整输出预算。计入当前泄放与两路分压，高压侧约 **30.670mA / 5.281W**。11.4V电感输入条件下的有限损耗筛查需要 **93.685%** 占空与约 **.810µs** 关断时间。输入损失和真实热/换流未包括。
3. 已知激励验证：保持SW=12V，电流从.2→.8A，原CS仍约11.9997V；没有A/V电流转换。候选.15Ω夹具的30/120mV只是独立示范，不是已选限流设计。
4. 历史Type-II原始波形按周期重算，140–150ms周期均值仍以 **105.124V/s** 上升；166.229V终值不是稳压。约116.38V的窄跌落与约97.99A二值开关换流尖峰同刻出现，模型不能签核真实器件应力。
5. 候选MOS二值开关用gate-to-GND控制，加入源极电阻后不再等于VGS控制。同参数对照改为gate-to-source后，输出端晚窗口pp从约55.38V变为5.35V；换官方Diotec研究模型也使尖峰大幅改变。两者均证明旧尖峰高度依赖模型；没有用“曲线更漂亮”宣布修复或合格。

**决策采用情况C：先冻结参数和模型。** 单级保留为研究候选；是否换两级/反激依赖G0的真实器件、输入和时序证据。正式原理图和PCB保持原样，原系统保护FAIL保留。

## 2. 基线、工作边界和证据读取

根目录 `D:/PROJECTS/dsharness/QS30-1`。起始分支 `nxt/reva9-electrical-sprint02`，HEAD `9682439fe35636ed2c2928bc50d30858133e4c8a`。独立本地分支 `nxt/reva9-electrical-sprint03`，HEAD未变。工作区原已修改README、kicad_gen.py、reconcile9.py和两PCB；还存在Sprint01/02与A9.3未跟踪资料，均完整保留。未stash、reset、清理、commit、push或生成制造文件。

工作区及祖先目录没有适用AGENTS.md，仓库内也未发现。阅读README、docs9全部33份Markdown设计/审查文档、POWER9、GATES、G0冻结、HOLD/问题卡、OVP审计与输入规范、MODEL_LIMITS和两轮完整报告；原始证据包含Sprint01实际启动/测量/RC结果、Sprint02全部command.json/deck/结果及Type-II原始压缩波形、超时/二极管兼容性记录。`sim/sprint03/document_inventory.json`记录设计文档哈希；本轮未把历史结果当成新测量。未找到独立且已填完整的器件问题卡，HOLD_REGISTER的H01/H04/H14及OVP_SIMULATION_INPUTS是现有权威缺项来源。

工具本轮实际查询：KiCad CLI **10.0.8**，ngspice **47**（本地ngspice_con.exe），既有review_venv Python环境，numpy2.5.4/matplotlib3.11.2。仅使用已有依赖。确切路径与二进制哈希在最终清单。两套原生项目为MAIN和DISPLAY，DISPLAY表示左右同模板，并未虚构第三套项目。

独立区域为 `sim/sprint03/`、本目录及 `design9/sprint03_*.py`。起始状态/完整已跟踪差异保存在 [baseline.json](../../sim/sprint03/baseline.json)、[inherited-worktree.patch](../../sim/sprint03/inherited-worktree.patch)。1603个此前存在的Git可见文件已冻结SHA256，最终逐一检查；未把tools依赖误报为已冻结的设计输入。

当前DRC698（508 errors、190 warnings）、ERC0 errors/364 warnings是Sprint02原始证据，**本轮没有重跑或声称为新DRC/ERC实测**。原生设计输入全部哈希不变；本轮只导出两份XML，核对64个HV相关CSV/原生引脚。没有修改规则、exclusion、映射、固件、PCB或任何历史报告。

## 3. 实际器件与输入规格

完整逐参数表：[COMPONENT_MODEL_MATRIX.csv](COMPONENT_MODEL_MATRIX.csv)，状态定义及阻塞项：[说明](COMPONENT_MODEL_MATRIX.md)。CONFIRMED仅指工程文件或原始规格中确认的设计值，不表示供应商/实物/模型已经签核。

| 项目 | 确认的设计输入 | 未知或研究假设 |
|---|---|---|
| 输入 | 12V系统 | 适配器型号/额定电流/最小最大/瞬态UNKNOWN；11.4–12.6V为ASSUMED研究包络 |
| 控制器 | UC3843AN、DIP-8、8脚连接 | 制造商/采购确认UNKNOWN；TI A系列为条件性对照；原生PRELIM封装未合格 |
| 电感 | 220µH、≥5A设计标识、12×12占位 | 实际型号、DCR、Isat定义/温度、Irms UNKNOWN；.3Ω和线性L ASSUMED |
| MOS | IRF740、400V/10A家族标签、TO-220 | 厂商/后缀、SOA和热/非线性模型UNKNOWN；.55Ω/150pF/1nF模型简化 |
| 二极管 | UF4007、DO-41、1000V/1A设计标签 | 实际供应商UNKNOWN；Diotec原厂模型仅研究对照，75ns不代表所有条件的恢复 |
| 电容 | C11/C12各10µF/250V，模块各.1µF；C10=10nF跨二极管 | 厂商/公差/ESR/ESL/纹波寿命UNKNOWN；总20.3µF、ESR.5Ω模型假设 |
| CS/反馈 | 实际R36=100k、C13=470p测SW；R34/R35=1.5M/22.1k | 实际没有分流；候选.15Ω功率/公差未选。参考误差/偏流不能忽略 |
| 负载/频率 | 九管13.5/20.25/27mA规格工作点；RT10k/CT2.2nF | 实际批次工作点/迟滞未知；78kHz设计估计，模型测得不是实物频率 |

当前目标由反馈计算172.183V，旧POWER9的171.84V与该连接不符。按TI A系列参考输入范围和分压1%描述，**不含偏流**的静态极值约163.42–181.23V；−2µA级输入偏流通过1.5M上臂可产生约3V量级额外偏移，准确方向/边界应按选定厂商约定计算。这说明旧“167.64–176.14覆盖169–175验收”的论述不能作为精度签核。

本轮在线核对官方A系列PDF、准确TI订购页、非A系列PDF、TI DN40、Diotec产品页。A系列PDF/订购网页原始下载、URL和哈希在 [source/downloads.json](../../sim/sprint03/source/downloads.json)。Vishay官方PDF在线访问失败，沿用仓库已存原厂PDF及文本，失败不伪称成功；厂商未冻结仍保留UNKNOWN。未以UCC28C43模型改名替代AN。

## 4. 拓扑计算

推导、假设和架构对比详见 [TOPOLOGY_FEASIBILITY.md](TOPOLOGY_FEASIBILITY.md) 与 [calculations.json](calculations.json)。满载筛查如下，Vin为电感端电压而非未经核实的适配器端：

| Vin | 理想D | 有限损耗D | 关断 | I_L峰值/RMS |
|---:|---:|---:|---:|---:|
|11.4V|93.379%|93.685%|.810µs|.784/.515A|
|12V|93.031%|93.324%|.856µs|.773/.494A|
|12.6V|92.682%|92.964%|.902µs|.765/.476A|

输入前级再损失.5V的研究例需93.988%、关断.771µs。MOS/二极管静态电压量级分别约Vo+Vf和Vo，寄生尖峰尚不能界定，不签核400/1000V额定裕量。满载CCM，典型接近边界，轻载DCM。C10单边沿硬换向能量量级11.56W，超过正常高压侧5.28W；其用途和能量路径必须另审，不能无授权删除。

[TI A系列Rev.H](https://www.ti.com/lit/ds/symlink/uc3843a.pdf)的DMAX保证下限92%不支持直接批准所需93.7%；同时其测试RT/CT/VCC不同，不能据此断定每个实际工作点必失败。A系列放电电流有界，有助设计计算，仍需要门极Miller、传播/下降、恢复、CS延迟和RT/CT公差的共同预算。模型约96.4%的结果不能取代它。

11.4V筛查下电感/MOS/候选分流/二极管导通损耗约.080/.137/.037/.031W，不含切换与温升，**不报告实际效率**。理想电容纹波约18mVpp，未计ESR/换流，不能当成输出端纹波合格。没有已批准降额/纹波/启动/过冲门限，建议值均PROPOSED，见矩阵说明。

## 5. SPICE分层验证

所有新运行上限45s，明确最大步长、固定reltol=.001/abstol1n/vntol1µ、gear；未放松容差。1ms控制器、.5ms采样、3ms热启动功率筛查与5ms原接线检查，没有重复300ms长超时任务。24次调用均到达各自终点、rc0且日志没有被脚本识别的执行错误；**完成不等于工程PASS**。总运行时间由最终JSON逐次汇总，日志/波形保留在各run目录。

### C1 UC3843振荡器/PWM — INCONCLUSIVE（功能对照完成；真实AN模型未合格）

| 条件 | 本轮结果 | 限定状态 |
|---|---|---|
| 未取样基准，10k/2.2n，IDIS8.3mA |78.948kHz，CT约.998–2.699V，占空96.378% | PASS，仅功能观察 |
| 直接CT→2.8k→CS→1k→0V |CT平衡1.37679V，不再振荡 | FAIL |
| 同一BJT缓冲候选 |78.084kHz，占空96.377%，CT恢复 | PASS，仅恢复振荡，不批准修复 |
| IDIS7.6/8.8mA敏感性 |79.310/79.513kHz，占空96.040/96.622% | INCONCLUSIVE，非完整角点 |
| 固定CS=.3/.6/.9V、COMP5V |三者占空相同 | 负对照：均未越1V阈值，不能测试PWM比例行为 |
| 独立无负载CT观察源产生CS斜坡，阈值.3/.6/.9V |占空约23.55/51.21/84.22%，无超过时钟上限的结果 | PASS，仅功能行为；周期pp约80/19/12ns提示数值定时误差 |

CT直接加载时COMP强制5V、CS低于阈值，使该功能模型输出锁定高，duty=100%，不能读作100%可用PWM；历史闭环夹具因COMP/CS不同而gate为0。这种差异与模型缺少停振故障保护相容，不是本轮推翻历史停振结论。真实芯片停振状态不能由此签核。

模型资格不足：来源为工程自建；A系列只调整IDIS假设，没有全部阈值/全温/驱动/放电特性。不同PWM条件下频率发生约1%数值变化，即使理想观察源没有电气加载，也不能把这些值当真实时钟抖动。缓冲BJT增益/温度/CT动态加载仍未知。

### C2 开环功率级 — INCONCLUSIVE

明确为 **受控PWM、初始电容172.183V、电感.5A的3ms热启动诊断**，不是自主启动、闭环稳压或实际UC3843。Vin11.4V，27mA高压负载加泄放/分压，研究D=.92/.935/.95；不使用无限接近100%的占空制造PASS。功率筛查是G0辅助模型资格检查，G0阻塞后未扩展整机稳态矩阵。

| D/模型 | 内部电容末.5ms均值 | 内部电容斜率 | 输出端pp | 解释 |
|---|---:|---:|---:|---|
|.920、无C10、generic |169.486V|−994V/s|.754V|目标储能下降，不能维持满载目标 |
|.935、无C10、generic |172.168V|−44.5V/s|55.48V|附近有转换能力，但换流异常，非稳态PASS |
|.950、无C10、generic |182.220V|+3583V/s|63.43V|继续积能与高电流，非可用设定 |
|.935、保留C10、generic |175.662V|+1336V/s|74.93V|能量/电流显著改变，不能解释为效率改善 |
|.935、25ns最大步长 |172.221V|−27.7V/s|56.15V|减半步长未消除约100A换流模型异常 |
|.935、Diotec研究二极管 |172.241V|−26.8V/s|8.19V|器件模型敏感，供应商未冻结 |

generic→Diotec二极管最大反向数值脉冲约−102.7→−15.7A；均不可当实际UF4007额定应力。官方模型只去除mfg/type兼容性标签，保留Rs/TT/Cjo等电气参数；Vpk/Iave不支持警告在日志保留。未为压平波形修改物理参数。

追加同参数开关控制参考对照：带0V电流探针，原gate-to-GND得到输出pp55.38V、MOS模型峰流约103.09A，瞬时VGS可达负值；改为gate-to-source后pp5.35V。**这是候选二值开关参考点错误的定位证据，不是修正版MOS模型已合格**。真实MOS Qgd、非线性Coss、恢复、寄生与饱和依然缺失；详见 `switch_reference_v1`。实际原接线源极GND不受这一参考差异影响，但自身无电流采样。

### C3 实际控制器与电流采样 — FAIL

保持SW=12V、已知电流.2/.8A：原R36/C13输出均约11.9997V；候选.15Ω分流给.03/.12V。实验同时保存物理电流、源极电压和CS，证明原采样错误。原R36不是“100k采样电阻”，不能分配为某个限流A值；其功耗/电压与CS钳位电流也需重设计。

.15Ω只是演示，其1V名义阈值对应6.67A，尚未计斜坡/滤波，不能据“电感标≥5A”批准。实际保护阈值/延迟、前沿干扰、MOS关断与饱和的联合验证BLOCKED。当前控制器不是可信电流内环，缓冲和Type-II都不能补偿这一事实。

### C4 闭环稳压 — BLOCKED；历史Type-II候选仍FAIL

没有新增闭环调参。历史原始数据重新分析而未重跑/延长150ms：

| 窗口 | 时间加权输出均值 |
|---|---:|
|120–125ms|162.865V|
|130–135ms|164.256V|
|140–145ms|165.461V|
|145–150ms|165.986V|

140–150ms周期均值约165.182→166.234V，拟合斜率105.124V/s。结论是**仍在上升的慢瞬态，同时叠加不可信换流尖峰**；没有证据把它归为已定常的稳压误差，也没有足够证据确定实际硬件闭环振荡。末点FB≈2.5V与瞬时HV/COMP耦合不能证明输出已稳。原波形未存v(cap)，所以不能精确分离历史内部电容纹波；未编造该指标。

RHP零点有限筛查低输入约16.2kHz，仅对简化电阻负载CCM适用；管负载非线性、模式边界与斜坡内环尚未合格，没有测得相位裕量/交越频率。不对当前切换B源模型的静态AC求解赋予物理环路意义。

### D 启动与稳态 — 原接线启动FAIL；正式稳态验收BLOCKED

本轮只作5ms短检查：原接线诊断模型输出峰16.937V、末16.868V，gate峰0，CS峰15.786V；未建立升压。此模型仍保留历史固定92%限制，不是AN资格模型；该5ms结果不能独立证明长期不启动，但与明确CS错误及历史80ms原始FAIL一致。历史15.5915V/80ms保持为历史测量，没有冒充本轮80ms重跑。

三个输入×实际负载的正式启动/稳态、UVLO/过冲/效率及完整应力矩阵因G0未通过而暂停；研究热启动点接近172V不计作启动成功。没有利用未批准阈值或末点取样宣布PASS。

## 6. 保护审查与三项Gate

实际CS错误、无限流再生锁存Q21/Q22、Q25缺硬件安全复位许可、OVP滤波/关断动态、比较器及控制域掉电状态仍未关闭。硬件COMP拉低和HV输入开关路径存在，不等于ESP32死机/复位/失电时已验证安全；GPIO保持高的死机状态尤其不能由普通下拉保证关闭。

OVP应独立处理反馈开路；当前未取得可靠正常工作点，不能完成可信自主FB故障保护峰值签核。正常Boost即使PWM关断仍有Vin→L→D→输出通路，输出短路不能只靠逐周期CS保护，需验证Q4输入切断能力、体二极管/SOA、保险与锁存动作。独立理想保护模型即使通过也不更改原系统FAIL。

沿用并核对Sprint01被动泄放原始结果：全连接20.3µF/50k到50V约1.256s；MAIN独立20µF/200k约4.947s；MAIN泄放开路实验未到50V、FAIL。模块独立.1µF/200k解析约24.7ms；容差、地线断开/模块拆卸、持续反灌与每支路单点开路仍需验证。MAIN单独假设C+20%、R+5%即约6.23s，因此标称接近5s不提供最坏裕量。50V仅继承测试参考，未经确认的触碰安全标准不能由RC时间代替。

| Gate | 状态 | 主要证据 |
|---|---|---|
| HV-G0 | **BLOCKED** | AN订购码找到，但厂商、输入、电感/换流/热/降额未知；所需D约93.7%、有效最大占空未获保证；模型资格未成立 |
| HV-G1 | **BLOCKED** | 无可信器件功率级或已批准稳定性指标；原接线启动FAIL，历史Type-II仍爬升；未开展新深度闭环 |
| HV-G2 | **FAIL** | 原CS不是电流采样；锁存/复位已知FAIL；OVP动态/失电未闭合；正常RC不覆盖泄放单故障 |

HV-G1 BLOCKED表示本轮签核前置不足，不把已有启动/闭环FAIL降级为“无问题”。整个NXT仍FAIL/HOLD。HV-G2虽非本轮强制完成条件，其已知失败不会被隐藏。

## 7. 文件、运行和Git

| 新文件/区域 | 内容与用途 |
|---|---|
| 本报告、COMPONENT_MODEL_MATRIX.csv/md、TOPOLOGY_FEASIBILITY.md | 架构结论、来源与假设、最坏筛查、缺项/改图影响 |
| calculations.json、SIMULATION_MATRIX.csv、final_results.json | 可机读计算、所有24次运行、执行与工程状态分离 |
| sim/sprint03/source | 原样继承功能模型、官方A系列PDF/网页及下载记录 |
| sim/sprint03/qualification_v1 |16次分层短实验，逐例完整deck/日志/参数/波形/耗时/rc |
| sim/sprint03/diagnostics_v1 |6次针对性跟进及历史Type-II周期统计/波形，不重复长仿真 |
| sim/sprint03/switch_reference_v1 |2次控制参考点对照、VGS/VDS/电流诊断指标 |
| sim/sprint03/baseline.json、native_*、两XML | 起始保护哈希、差异快照、原生连接证据 |
| design9/sprint03_audit.py、sprint03_hv.py、sprint03_diagnostics.py、sprint03_switch_reference.py、sprint03_report.py、sprint03_finalize.py | 可复现与追加证据脚本 |
| integrity.json、final-verification.json、manifest.json、git状态/差异摘要 | 初始/最终完整性核验与新文件清单 |

关键图：[历史Type-II再分析](../../sim/sprint03/diagnostics_v1/historical_type2_analysis.png)、[CT直接加载](../../sim/sprint03/qualification_v1/osc_direct/waveforms.png)、[开环分节点](../../sim/sprint03/qualification_v1/power_0.935/waveforms.png)、[VGS控制对照](../../sim/sprint03/switch_reference_v1/control_vgs/waveforms.png)。统计使用原生非均匀数据，不用绘图稀疏采样代替峰值。

所有正式工程、历史报告/失败deck与旧波形保持原字节，最终验证记录在 [final-verification.json](final-verification.json)。Git diff-stat仍显示继承的五个已跟踪修改，它们不属于本轮变更；新增Sprint03文件不会出现在普通git diff，完整新增列表由manifest和git-status提供。未自动commit/push。

复现，在根目录使用已有Python。audit是一次性基线捕获，当前会拒绝覆盖；不要重新生成旧baseline。

```powershell
& tools/review_venv/Scripts/python.exe design9/sprint03_hv.py --run NEW_SHORT_RUN
& tools/review_venv/Scripts/python.exe design9/sprint03_diagnostics.py --run NEW_DIAGNOSTIC_RUN
```

switch_reference脚本固定`switch_reference_v1`并拒绝覆盖；如需重跑先复制脚本并改成新目录名。最直接的单例复现是在该deck目录运行：

```powershell
& D:/PROJECTS/dsharness/QS30-1/tools/ngspice47/Spice64/bin/ngspice_con.exe -b -o replay_NEW.log circuit.cir
```

**deck内wrdata会写waves.txt，因此应先把完整单例文件夹复制到新的运行目录再执行。** 不直接在历史目录重放。每个实验保存原始deck与驱动快照；依赖h脚本与功能模型的最终哈希也在manifest。raw执行engineering=INCONCLUSIVE保守保留，报告中的PASS只限明确列出的功能观察，最终Gate不由这些局部标签自动提升。

## 8. 下一轮任务（按技术依赖）

1. 冻结适配器/AN厂商、真实磁件、MOS/二极管、电容/分流实体规格及允许负载、输出与降额要求。
2. 依据真实输入端压降、最坏RT/CT/驱动/恢复联合预算关闭G0；不足时优先研究两级非隔离Boost，确有隔离需求再评估反激。
3. 修正独立研究模型的VGS参考、门极/Miller、恢复、寄生与饱和；设计真正Kelvin采样/限流及不加载CT的有据斜坡，先重验各层模型。
4. 在前三层可信后计算补偿并用适用的环路注入/小信号和周期/窗口统计验证启动、稳态及线负载响应，提交最小正式改图清单再等工程批准。
5. 闭合限流锁存、独立OVP/反馈失效、硬件安全复位/失电、输入切断/短路与泄放单故障；批准后才考虑原生工程同步及PCB评审。
