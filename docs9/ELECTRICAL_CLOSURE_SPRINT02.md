# NXT / REV.A9 — Electrical Closure Sprint 02

日期：2026-11-11（Asia/Shanghai）。**结果：FAIL/HOLD；Gate 1未关闭，不回写电源原理图/PCB，不放行制造。**

## 1. 范围与基线

本轮执行了控制器时序核验、现有启动FAIL重放、局部CS/斜坡/补偿候选的隔离瞬态实验、官方二极管模型获取与兼容性验证。未改用一套无关理想电源。原电路、局部候选、器件模型单测分开记录。

起始分支 `nxt/reva9-electrical-sprint01`，新分支 `nxt/reva9-electrical-sprint02`，HEAD仍为 `9682439fe35636ed2c2928bc50d30858133e4c8a`。Sprint01全部修改与此前A9.3未跟踪候选保留，未stash/reset/清理或改写它们。初始Git状态、既有输入哈希及完整跟踪文件diff已先存入 [baseline.json](../sim/sprint02/baseline.json)、[inherited-worktree.patch](../sim/sprint02/inherited-worktree.patch)。本轮新数据都在sprint02命名空间。

工具继续使用KiCad10.0.8、ngspice47及已有review_venv。原生前后均实际执行DRC/ERC、XML导出和12项映射审计，见 `kicad/logs/sprint02_before/`、`sprint02_after/`。CLI的ERC/DRC rc5表示发现违规且报告成功；网表导出rc0。自定义功能一致性不等于电气安全。

| 原生指标 | Before | After |
|---|---:|---:|
| DRC总计 | 698 | 698 |
| DRC Errors / Warnings | 508 / 190 | 508 / 190 |
| Unconnected | 508 | 508 |
| ERC Errors / Warnings | 0 / 364 | 0 / 364 |
| 原生/CSV/PCB引脚一致性 | PASS | PASS |
| 90阴极、9阳极、接口/96位链路12项审计 | PASS | PASS |

本轮没有更改Sprint01修复后的PCB网络或几何，没有新增exclusion/修改严重度或降低规则。上轮109项含HV类网络的未布线报告仍未解决；高压绝缘规则仍未冻结，不能因clearance报告为0宣称安全。

## 2. Gate 1：器件、占空比与拓扑结论

**结论：单级Boost尚不能批准；不是已经证明物理上绝对不可行。** 当前MPN只有UC3843、IRF740、UF4007和220µH/≥5A等泛称，缺输入电源确切规格、控制器厂商/后缀、磁件DCR/Isat/温度及真实MOS换流模型。已向用户收集这些信息；未获得的项目保持UNKNOWN，没有自动写入一个假定型号。

在线复核 [TI UC3843 SLUS223H](https://www.ti.com/lit/ds/symlink/uc3843.pdf)：DMAX表为92%最小、97%典型、100%最大，具有手册规定的测试条件；Rev.H修订记录明确最小值从95%改为92%。因此旧行为模型的固定92%不能被当作所有器件标称能力，也不能把新功能模型的约95%当生产保证。手册测试条件RT10k/CT3.3nF、VCC15V，与现有10k/2.2nF、约12V并不完全相同，不直接外推成新工作点的保证下限。

现有反馈目标172.183V，理想占空比在11.4/12/12.6V分别约93.38/93.03/92.68%；11.4–12.6V只是继承的±5%探索包络，尚不是已核实适配器规格。含假设DCR=.3Ω、MOS等效Ron=.55Ω、二极管1V和效率.75–.9的筛查，最高所需占空约93.706%。该筛查不是已测效率或精确CCM解，数值见 [calculations.json](../sim/sprint02/calculations.json)。

[TI DN40](https://www.ti.com/lit/an/slua173/slua173.pdf)说明RT/CT频率与最大占空会受到放电电流变化影响。所用2.8/6/8.3mA是探索值，其中上下界不是UC3843保证规格。

| 隔离控制器功能模型 | 频率 | 测得最大占空 |
|---|---:|---:|
| RT10k/CT2.2nF，IDIS6mA | 77.972kHz | 94.977% |
| 同上，探索IDIS2.8mA | 73.218kHz | 89.176% |
| 同上，探索IDIS8.3mA | 78.967kHz | 96.412% |
| RT22k/CT1nF，IDIS6mA候选 | 80.245kHz | 97.756% |

这些是自建模型的工具实测，不是厂商模型验证。参考电压约4.9997V；UVLO测试显示供电降到关断区后输出关闭。CS脉冲测试155个有效边沿，最大模型关断延迟182.81ns、同周期再触发0；只通过预设模型行为检查，不证明真实器件的全角点响应。

拓扑处置：不未经评估换成两级或反激；同时不继续按“单级已可行”开展PCB布线。后续评估可比较保持单级并取得最坏条件时序保证、12→48→172V两级、或变比约8的反激。仅作理想转换比比较：低输入11.4V时两级占空约76.25%/72.12%，变比8反激约65.37%；尚无器件/磁件/控制/效率与安规设计，不是可直接实施方案。

## 3. 局部候选与新增根因

实际电路启动重放：[sprint02_actual_baseline](../sim/a9_2/sprint02_actual_baseline/results.json)，80ms输出15.5915V、CS采样约15.6902V，原FAIL再次复现。原Q20.S直接GND、R36从SW_HV接CS仍未修正，不能检测源极电流；未回写猜定分流电阻。

本轮复用此前未提交A9.3的**源文件快照**建立隔离夹具，未调用其会覆盖旧native_audit.json的入口。每个新run保存驱动脚本快照、独立deck、局部模型副本、原生meas及执行结果。隔离夹具没有完整实际门控/保护链，输入夹具阻抗.05Ω、近端电容、ESR等均为假设；不能用其结果替代实际整机。

### S02-R01：斜坡直接加载CT导致振荡停止

源极采样候选使用.15Ω分流、1k到CS、2.8k从CT到CS、100p滤波。源极电压接近0时，CT新增约3.8k到地负载；通过现有10k从5V充电，平衡仅约1.377V，低于模型2.7V上阈值。瞬态验证late gate duty=0、未达到169V。故“直接改CS并取CT斜坡”本身还会引入振荡停摆，不能作为可回写修复。

### S02-R02：缓冲恢复开关，但闭环和补偿尚不合格

增加显式通用NPN射随缓冲，仅作为候选，与直取CT对比。保留C10时120ms末值134.492V；去掉C10的隔离诊断末值153.882V、曾达到191.159V。后者建立了高压而非合格稳压。

采用此前Type-II候选（RT22k/CT1nF；R37=10k；C14=4.7µF、C15=1nF接反馈）150ms平均165.723V、终值166.229V，仍不满足169–175V/晚窗口<2Vpp判据；某一时刻FB约2.5V不能代替稳态验收。

### S02-R03：斜坡幅度也必须定量设计

原1k/2.8k求和使源极权重约.737、斜坡权重约.263。以名义CT末段最小斜率2.3/(RT·CT)及11.4V→172V估算，原注入斜率约.0275V/µs，小于这一简化电流模式稳定性筛查所需约.0375V/µs。不能仅确认“接了斜坡”就批准。

由同一不等式得到RRAMP上界约2.05kΩ，故设置1.5kΩ作为**有计算依据的探索候选**，并保留BJT缓冲；不是已冻结阻值。BJT增益/温度/负载、实际电感和控制器模型仍需评估。这组与厂商二极管对照均尝试运行300ms，以覆盖4.7µF×10k的多倍时间常数；两例均在120s执行预算内未完成300ms瞬态，已记录执行FAIL、工程BLOCKED；无终点测量，不输出稳态指标。未用截断曲线宣称稳定。

### S02-R04：开关换流模型不足以签核应力

隔离模型采用二值开关+.55Ω、150pF Coss、通用UF恢复、假设.5Ω输出ESR，没有完整MOS的Qgd/非线性电容、寄生电感或真实磁件饱和。原生meas产生约78–191A的部分开关换流峰值；这些是该简化网络的数值解，不能读作实际IRF740精确电流或耐受结论。输出终端v(hv)还含ESR瞬态，不等同于内部电容电压v(cap)。没有凭平均电压合格来忽略尖峰，亦未随意增大容差来压平。

C10=10nF跨SW_HV/HV_BUS的½CV²f硬充放电量级约11.56W，大于数瓦负载；原模型开环对照中保留/移除C10的MOS等效平均损耗约16.09/.483W，但均受换流模型限制，不能作实际热设计或删除C10的授权依据。原生电路C10保持原样。

## 4. 厂商模型与失败处理

找到 [Diotec UF4007官方产品页](https://diotec.com/en/product/UF4007.html)及模型。网页相对链接路径请求404，修正为同厂商根路径 `https://diotec.com/request/spice/uf4007.zip` 下载成功；ZIP SHA256 `ac34d16d7912b650d6418c1e4f1d80d15079ad0ffc2705c9fdd8039a834b8055`。原ZIP/lib/符号和失败请求记录保留于 `sim/sprint02/source/`。

- 未修改原lib。第一次原样ngspice执行因 `mfg=Diotec`/`type=Rectifier`元数据被当符号参数，报Undefined parameter，rc1，分类MODEL_ERROR/语法不兼容，保留diode_v1。
- 在派生副本只去除mfg/type标签后重跑，原生瞬态终点1ms、3mA测试电压0.893149V；diode_v2执行完成。ngspice仍警告Vpk/Iave额定注记不识别并忽略，明确保留警告。电气参数Rs、TT、Cjo、N等未为追求PASS调整。
- 该单测仅确认模型可执行及一个工作点，不是全特性模型校准，也未冻结Diotec为实际供应商。
- 检查Vishay IRF740官方产品页，未在所查资源中取得电气SPICE模型；ECAD几何模型不充当电气模型。TI产品页提供的SLUM521指向UCC28C43，不改名冒充现有UC3843。
- 未将运行超时归为CONVERGENCE_ERROR：无步长/收敛错误日志时，仅记录UNSUPPORTED（执行超时）与未到终点。所有有效运行需同时检查返回码、错误文本及原生end_time。

## 5. 六项整机测试状态与工程边界

| 测试 | 本轮工程状态 | 原因 |
|---|---|---|
| SIM-01 启动 | FAIL | 实际网表重跑仍约15.59V；隔离候选未满足闭环判据 |
| SIM-02 稳态 | FAIL | 无被接受的稳态，换流/器件应力模型未合格 |
| SIM-03 负载变化 | BLOCKED | Gate1/正常工作点未关闭，未扩大完整负载矩阵 |
| SIM-04 输入变化 | BLOCKED | 确切电源范围及占空最坏裕量未冻结；Sprint01原FAIL保留 |
| SIM-05 过流/故障保护 | BLOCKED | 正常运行前置未关闭；实际CS/锁存已知FAIL，没有实施新保护架构 |
| SIM-06 关断残余HV | BLOCKED | 无可信自主高压启动供完整掉电测试；Sprint01被动RC证据保留，不冒充整机PASS |

保护专项仍然存在：Q21/Q22再生支路缺完整限流、Q25缺硬件安全复位许可、OVP检测/COMP延迟与全链路储能峰值未闭合、掉电反灌与HV残留未验证。为了遵循前置依赖，本轮未在这些问题上继续做无正常工作点支撑的“保护通过”实验；没有改原理图掩盖FAIL。

预设判据在实验前保存为 [acceptance.json](../sim/sprint02/acceptance.json)。MODEL_CHECK_PASS仅为控制器功能模型检查，CANDIDATE_WINDOW_PASS仅指有限窗口，均不等同于整机PASS；本轮不得制造/高压上电放行。

## 6. 文件、复现、Git及后续依赖

本轮实际新增：

| 路径 | 用途/验证 |
|---|---|
| `design9/sprint02_hv.py` | 自包含源快照驱动、控制器/功率/斜坡候选；原生终点/日志判定 |
| `design9/sprint02_vendor.py` | 厂商二极管兼容性对照；物理参数未改 |
| `design9/sprint02_review.py` | 汇总、源哈希、继承文件不变、原生前后和波形压缩校验 |
| `sim/sprint02/` | 预设判据、起始状态、输入快照、计算、所有新deck/日志/波形/失败证据 |
| `sim/a9_2/sprint02_actual_baseline/` | 现有实际电路启动重放 |
| `kicad/logs/sprint02_before/`、`sprint02_after/` | 原生前后DRC/ERC/XML与12项审计 |
| 本报告、`docs9/electrical_sprint02/` | 人读结论、机器结果、完整清单/哈希 |

此前文件不修改，README继续保留Sprint01入口，本轮链接由本报告直接交付，避免改动上一轮证据。详细诊断表/六项状态见 [results.json](electrical_sprint02/results.json)，文件哈希见 [manifest.json](electrical_sprint02/manifest.json)。

复现：在仓库根使用既有 `tools/review_venv/Scripts/python.exe`；每次NEW_RUN使用不同目录名。`sprint02_hv.py`只从本轮source快照读取模板/模型；不调用旧A9.3会写入历史目录的main。

```powershell
& tools/review_venv/Scripts/python.exe design9/sprint02_hv.py controller --run NEW_CONTROLLER_RUN
& tools/review_venv/Scripts/python.exe design9/sprint02_hv.py power --run NEW_POWER_RUN
& tools/review_venv/Scripts/python.exe design9/sprint02_hv.py candidate --run NEW_CANDIDATE_RUN
& tools/review_venv/Scripts/python.exe design9/sprint02_vendor.py --run NEW_DIODE_RUN --compat
```

每个完整deck亦可在其目录直接用ngspice `-b -o replay.log circuit.cir`重放。源模型副本和完整原生日志均保存，未删除失败运行。波形统计使用非均匀原生时间点，峰值优先采用原生meas。

本轮尚未形成可靠电气修复候选，因此不创建电路闭合commit；修改和证据保留在独立分支工作区。没有push、制造订单、Gerber输出、其他Σ/ELBridge修改。

下一步依赖：①取得确切输入/控制器/磁件信息；②完成控制器最坏占空与实际MOS/二极管换流可行性，决定单级继续或提交拓扑变更评估；③通过源极采样/缓冲斜坡/补偿的自主正常运行矩阵；④再设计并验证限流锁存、安全复位和故障/关断链；⑤候选满足判据后同步原生工程、重做DRC/ERC与布局评审。当前不要求用户批准一个未经验证的电路改动。

波形入口：[控制器CS测试](../sim/sprint02/controller_v1/cs_latch/waveforms.png)、[直取斜坡停振](../sim/sprint02/power_v1/direct_ramp_stalled/waveforms.png)、[Type-II候选](../sim/sprint02/power_v1/buffered_type2/waveforms.png)。这三份图已由实际工具生成；本轮查看Type-II图确认包含输出尖峰，未以稀疏抽样图替代原生峰值。

最终执行清点：18次ngspice调用，15次完成；1次原厂模型语法失败、2次120秒超时。完成不等于电气PASS。[最终完整性核验](electrical_sprint02/final-verification.json)确认源/模型/脚本快照哈希、元数据唯一变更、已有输入未变及Git diff检查均通过；所有失败原始记录保留。
