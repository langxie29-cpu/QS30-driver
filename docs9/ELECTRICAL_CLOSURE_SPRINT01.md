# NXT / REV.A9 — Electrical Closure Sprint 01

日期：2026-11-10–11（Asia/Shanghai）。**总体：FAIL / HOLD，禁止投板与高压上电放行。**
本轮实际修复55项NC同步警告；没有修改电源拓扑。启动FAIL已重现。所有“执行PASS”仅指工具完成，工程验收状态另列。

## 1. 基线、范围与环境

- 根目录 `D:/PROJECTS/dsharness/QS30-1`；起始分支 `rev-a9-2-electrical-safety`，HEAD `9682439fe35636ed2c2928bc50d30858133e4c8a`；本轮分支 `nxt/reva9-electrical-sprint01`。
- 起始跟踪文件干净；已有未跟踪项：`design9/hv_analysis9.py`、`design9/hv_convergence9.py`、`docs9/INDEPENDENT_REVIEW_2026-11-08.md`、`docs9/review_20261108/`、`kicad/logs/a9_3_baseline/`、`sim/a9_3/`。全部保留，不纳入本轮修改或提交。
- 已读README、FINAL_REPORT9、GATES、EDA_STATUS、POWER9、DRC_TRIAGE_A9_2、OVP_REVIEW_A9_2、MODEL_LIMITS、接口/映射及2026-11-08审查；亦读六位HANDOVER/HOLD/open_issues作为历史边界。工作树及祖先目录无AGENTS.md；只读了本地远端跟踪引用 `origin/main:AGENTS.md`，未合并远端。
- 两套实际原生工程位于 `kicad/projects/QS30-9_MAIN/` 与 `QS30-9_DISPLAY/`，各有pro/sch/pcb；右模块由DISPLAY的L→R模板表示，不虚构第三块独立原生板。实际为ESP32-S3、3×HV5622PG-G、九位静态3+3+3；原生板上只表示中心/左模块及主板，右模块映射另审计。
- 与用户历史描述的差异：当前提交为A9.2；原生ERC是0错误/364警告，36/36是自定义结构规则；753项DRC本轮实测复现。阳极20k实际为每管两只10k/2W串联。旧README/EDA_STATUS仍含“原生未执行”等历史状态，以本报告新证据为准，未改写历史数据。
- 工具：`C:/Program Files/KiCad/10.0/bin/kicad-cli.exe`=10.0.8；`tools/ngspice47/Spice64/bin/ngspice_con.exe`=47；使用已有 `tools/review_venv/Scripts/python.exe`（numpy2.5.4、matplotlib3.11.2、kiutils可导入）。没有安装或更改系统依赖。
- 修改前基线：[sprint01_before](../kicad/logs/sprint01_before/results.json)，含命令、返回码及输入哈希。中间 `sprint01_after`、`sprint01_final`保留；最终为 [sprint01_verified](../kicad/logs/sprint01_verified/results.json)。

## 2. DRC / ERC

原生命令对两板均实际执行：

```powershell
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' pcb drc --format json --severity-all --schematic-parity --exit-code-violations -o OUTPUT BOARD.kicad_pcb
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' sch erc --format json --severity-all --exit-code-violations -o OUTPUT BOARD.kicad_sch
```

同时导出sexpr/XML，原生命令逐条argv/stdout/stderr/rc见各轮commands.log。ERC/DRC均rc=5（发现违规且报告成功），网表导出rc=0；不能把rc5当执行异常。

| 指标（MAIN+DISPLAY） | Before | After |
|---|---:|---:|
| DRC Errors | 508 | 508 |
| DRC Warnings | 245 | 190 |
| 全部DRC | 753 | 698 |
| Unconnected | 508 | 508 |
| 含HV类网络名的DRC项目 | 109 | 109 |
| 已配置规则下HV几何间距/短接报告 | 0 | 0 |
| ERC Errors | 0 | 0 |
| ERC Warnings | 364 | 364 |

**HV规则尚未建立，0项不能说明HV安全。** 109项按CSV `net_class=HV`与原生对象`[net]`交集统计，全部是未布线报告；不是全HV区域物理风险的完整计数。逐项网络、对象、优先分类可复核 [drc-items.csv](electrical_sprint01/drc-items.csv)。原生JSON中无网络标注的封装库问题不强行计入HV数字。

| 分类 | Before | After | 根因/处置 |
|---|---:|---:|---|
| Clearance | 0 | 0 | 默认低压规则，未证明高压间距 |
| Short circuit | 0 | 0 | 本轮未发现已配置规则下新铜短路 |
| Unconnected | 508 | 508 | P0关键电源/P1信号均无布线；同一“未布线占位板”根因，不能当508个遗漏原理图连接 |
| Via / Track | 0 | 0 | 无走线/过孔，不能证明可制造 |
| Pad / Footprint | 190 | 190 | 182个PRELIM器件+8个孔的库关联问题；真实封装仍未确认 |
| Courtyard | 0 | 0 | 缺真实庭院，且missing_courtyard原已忽略 |
| Silkscreen | 0 | 0 | 占位外形，不能作为装配审核通过 |
| Board outline | 0 | 0 | 未改板框/层数/孔径 |
| Schematic parity | 55 | 0 | 独立NC网络名未同步到PCB焊盘，已修复 |
| Other | 0 | 0 | — |

最高频只有三类：未布线508、封装库190、NC一致性55，不存在可列的第四/第五个非零类别。主板598→560，DISPLAY155→138。

### 本轮修复与边界

P0先审：真实CS错误、锁存、残余HV风险见下节；它们不能靠占位PCB局部移动修复。P1大规模布线被真实封装、磁件、连接器及控制架构输入阻塞。没有拿低风险修改替代P0关闭。

本轮对可局部安全修复的一项共同根因实施修复：原理图显式NC经KiCad自动产生单节点 `unconnected-(Ref-PinName-PadN)`；PCB对应pad未分配网络，产生55条net_conflict。为17个DISPLAY/38个MAIN焊盘各赋唯一、与原生XML完全相同的隔离网络。没有将NC互连，没有加铜，没有隐藏警告。生成器同步修正，避免重建丢失。

另修复工具路径失效（允许KICAD_CLI覆盖/自动探测），并加强检查器：PCB的全部NC集合与原生单节点集合必须逐脚相等。未修改原理图、CSV、BOM、电气拓扑、板层、钻孔、间距、严重度或exclusion。

[checks.json](electrical_sprint01/checks.json)实测确认：移除新增NC声明与赋值后，PCB几何/功能网络内容与起始HEAD一致；生成器产生的所有pad网络和局部几何与当前PCB一致；前后原生全部引脚成员完全相同；694个功能节点逐脚匹配。结构ERC36/36；最终 [12项电气审计](../kicad/logs/sprint01_verified/electrical_audit.json) 全部通过（90阴极、9独立阳极、36接口配对、96位链路、唯一地桥），仍不证明实物位序或功能安全。

项目pro几乎没有明确制造规则；六位 `docs/pcb_rule_matrix.csv` 的1mm是TBD占位，不能套用到九位安全验收。材料组/CTI、污染等级、海拔、瞬态/过电压类别、适用绝缘规范与板厂能力未冻结，故没有猜测数值或实施HV安全间距。既有5项ignored_checks前后相同：missing_courtyard、track_not_centered_on_via、tuning_profile_track_geometries、footprint_filters_mismatch、footprint_type_mismatch。未新增豁免。封装库190项不是可通过关闭规则解决的假警告；库关联和真实尺寸均需处理。

## 3. SPICE模型与供电目标

原始FAIL通过现有 `design9/safety_sim9.py`从本轮原生XML+现有CSV生成并重跑，保存 [sprint01_actual/results.json](../sim/a9_2/sprint01_actual/results.json)，9例均工具执行完成，工程保护签核均FAIL。没有采用未提交A9.3候选作为已实现电路。

[QS30-1原厂扫描](../docs/source_scans/QS30-1_原厂说明书_p2_基本参数表.png)本轮实际查看：起辉≤150V、熄灭≥100V、Ea170V、工作电流1.5/2.25/3mA、170V推荐20k；它不提供本批次实物维持电压分布。当前反馈目标172.183V。全亮九管按规格电流的负载包络为13.5/20.25/27mA，母线约2.32/3.49/4.65W；空白为0管电流但仍有泄放/分压。另有至少0.593W四路泄放，故满载输出至少5.24W再加分压等；输入/热/功率裕量未签核。以3mA计每管20k耗散0.18W（每只10k 0.09W），短管且172.183V时整支路1.482W（每只0.741W）；2W标识不替代实际型号、耐压、温升和环境降额。当前CSV未冻结阳极电阻容差；若仅作R±1%假设，短管单只最坏约0.749W，不能据此写成BOM公差已验证。

125V维持压仅为现有负载模型假设，172.183V/20k模型电流约2.359mA/管；忽略驱动压降，不是实物规格。未含起辉/熄灭迟滞，低于125V时所有负载均不导通。

| 模型 | 当前状态与可验证边界 |
|---|---|
| 输入 | 12V，0.5Ω夹具源阻；11.4/12.6V沿用现有设计±5%测试包络；未取得适配器确切规格，不能当已验证供电允许范围 |
| UC3843 | 自建功能模型，UVLO迟滞、误差放大、COMP/CS；78kHz和92%最大占空是假设。12→172V理想约93%，此模型不能证明目标可行；无完整PWM锁存/斜坡补偿 |
| IRF740 | .55Ω控制开关，不是真实MOS模型，无体二极管/Coss/雪崩/SOA；供应商/后缀未冻结。A9.3有Vishay资料，但本轮未用其替代实际器件验证 |
| UF4007 | 通用D模型：RS=.5Ω、TT75ns、CJO15p、BV1000V；不是确切厂商模型，恢复/尖峰不能签核 |
| L20 | 220µH、假设DCR.3Ω，无饱和；标注≥5A不是已取得磁件规格 |
| C11/C12 | 各10µF/250V理想电容，无实测ESR/公差；模块另3×.1µF。C10实际10nF跨SW/HV母线，不是已验证RC吸收 |
| 保护 | 分立通用BJT、LM393/TL431功能模型；不能覆盖全温失调、芯片失电钳位、MOS反灌或过额定破坏 |
| 来源 | 现有工程原创模型，见 [MODEL_LIMITS](../sim/a9_2/MODEL_LIMITS.md)；未冒充厂商。厂商UCC28C43候选不是已冻结UC3843的直接替代模型 |

### 六项工程测试

| 测试 | 工程状态 | 实测/阻塞 |
|---|---|---|
| SIM-01 启动 | **FAIL** | 12V九管，0–80ms；末值15.5915V，原生峰值16.9379V；未到目标，启动时间>80ms或无有效启动，不能给出目标过冲百分比 |
| SIM-02 稳态 | **FAIL** | 60–80ms均值15.7562V、变化0.330727Vpp，是启动失败的低压衰减窗口，不是172V稳态纹波 |
| SIM-03 负载变化 | **BLOCKED** | 空载/六管/九管和25ms六→九均已执行，末值同为15.5915V；HV低于模型125V，负载没有导通，无法验收负载瞬态；1管轻载尚未独立运行，无有效恢复时间 |
| SIM-04 输入变化 | **FAIL** | 11.4/12/12.6V末值14.7638/15.5915/16.4192V；11.4→12.6V阶跃末值14.7643V；均未建立目标，包络非适配器认证 |
| SIM-05 过流/故障 | **FAIL** | CS拓扑不是电流采样，不能形成可信限流阈值/响应；复位卡高的230V外部注入例完成，锁存末值9.5348V、COMP约.00596V，但电流支路过额定，不能称保护通过。自主过载/短路响应BLOCKED，未人为造PASS |
| SIM-06 关断/残余HV | **BLOCKED** | 转换器20ms输入掉电例执行，80ms输出15.5860V；没有先达到HV，不能验收整机关断。下列独立被动RC子试验执行PASS；单故障放电判据FAIL |

### 定量测量与波形

新增0V串联电流探针仅用于开关等效测量；保留原始连接及全部参数。v2使用原生时间点的meas统计，未用10µs线性重采样推断开关峰值。初次测量v1因差分向量语法失败（rc0但日志报错），明确判为NETLIST_ERROR、执行FAIL；v2显式let差值修正后重跑完成，原失败deck/log未删除。两轮结果在 `sim/a9_2/sprint01_measurements*`。v1不是电路修复，未改变物理参数或求解容差。

| 参数 | 原生meas结果 | 限制/风险 |
|---|---:|---|
| HV output steady-state | 无合格稳态；晚窗口均值15.7562V | 目标172.183V失败 |
| Startup overshoot | 输出峰值16.9379V | 不报告“负过冲”或0%过冲来掩盖启动失败 |
| Startup time | 80ms内未达到目标 | 恢复/软启动未验收 |
| Output ripple | 晚窗口0.330727Vpp | 非开关稳态纹波 |
| MOSFET max VDS | 等效开关17.675V | 不能与400V标识比较后宣称实际裕量合格 |
| MOSFET peak ID | 等效开关1.7675e−8A | 未正常开关，仅漏电；不是真MOS启动/满载应力 |
| Inductor peak current | 2.54771A | 启动充电，模型不含饱和，不能批准5A磁件 |
| Diode reverse voltage | 9.75704V | 失败启动条件；不代表172V运行应力 |
| Output capacitor peak | 16.9379V | 不证明250V额定在故障时有裕量 |
| Input power | 晚窗口0.115271W | 仅模型输入源供电，不是整机功耗 |
| Output power | 管负载0W；目标功率未实现 | 泄放约V²/50k、另有分压/储能变化；不计算虚假效率 |
| Overcurrent response | FAIL / 限流响应UNKNOWN | 没有正确电流采样 |

[启动波形](../sim/a9_2/sprint01_actual/startup_9/waveforms.png)、[负载阶跃](../sim/a9_2/sprint01_actual/six_to_nine/waveforms.png)、[输入阶跃](../sim/a9_2/sprint01_actual/line_step/waveforms.png)、[复位卡高注入](../sim/a9_2/sprint01_actual/reset_stuck/waveforms.png)。注入源230V不是升压器达到或被保护限制的电压。

独立RC子试验从172.183V初始化，只保留现有泄放与电容，去掉管电流及分压，不给转换器任何持续能量。50V仅为测试参考，非接触安全认证。

| 场景 | t≤50V | V(1s) | V(5s) | V(12s) | 判据/正常泄放损耗 |
|---|---:|---:|---:|---:|---|
| 全连接20.3µF/50k | 1.25596s | 64.2856V | 1.24913V | .001263V | 被动模型≤5s PASS；.59294W总计 |
| 主板独立20µF/200k | 4.94696s | 134.096V | 49.3313V | 8.57249V | 标称≤5s PASS但余量小；.14823W |
| 主板泄放开路 | 未到 | 172.183V | 172.183V | 172.183V | FAIL；仅保留1e15Ω数值泄漏 |

[t50/RC解析交叉检查及结果](../sim/a9_2/sprint01_measurements_v2/results.json)、[泄放曲线](../sim/a9_2/sprint01_measurements_v2/all_connected/discharge.png)。主板t50解析4.94614s与工具4.94696s一致；未含公差，不能批准最坏情况≤5s。单泄放失效案例还保守忽略了分压/其他泄漏，说明缺独立冗余泄放，不声称实际故障必精确保持172.183V。

## 4. 保护专项审查与剩余风险

**P0 / TOPOLOGY_ERROR：** 原生网表Q20.S直接GND；R36=100k从SW_HV接CS_FILT，C13=470p到GND。RC=47µs，仅滤波开关电压，不能检测电感/源极电流，没有可定义的A/V转换或电流阈值。12V启动CS采样峰约15.69V，超TI UC3843模拟输入6.3V绝对最大值；模型未含损坏。阈值容差、限流延迟、恢复与短路持续功耗均UNKNOWN；必须源极采样/Kelvin、限流、斜坡补偿和磁件一起评估，未贸然猜分流电阻回写原理图。

**P0 / TOPOLOGY_ERROR、MODEL_ERROR：** Q21.C→Q22.B、Q22.C→Q21.B直接再生，缺完整限流；Q25复位直接对抗锁存，无“安全电压+请求关断”的硬件许可。卡高注入的原生日志中q21_peak=−.915058A、q22_peak=.834991A（原生meas），已超通用小信号BJT有效额定范围，模型外推不能作器件应力预测。没有把卡高下未清锁判为安全复位PASS；持续危险功耗、恢复策略FAIL/UNKNOWN。

**P0 / PERFORMANCE_FAIL、模型边界：** R41/R42=1.5M/19.1k与100nF形成约1.886ms检测滤波，COMP有22µF；静态OVP标称约198.44V不证明动态峰值受限。反馈目标需要约93%占空，而旧模型最大92%；C10跨SW/HV与真实MOS换流损耗、环路/补偿尚未闭合。厂商模型与自主高压稳态是后续故障测试前置，不能凭外部强制HV源审批整机。

**P0 / 残余高压：** 无已验证主动放电，主板独立标称t50已近5s；泄放/连接器拔离/断电顺序需单故障评估。绝缘/防触碰/实际孔位与铜皮间距没有冻结输入，当前0条clearance不能作安全结论。

**C2 复位/使能：** HV_EN_REQ有100k外部下拉，Q3/Q5有基极下拉、PMOS门极源极上拉；说明静态默认关断路径存在。ESP32未初始化/复位时必须保持DISP_ALLOW低、POL固定DRV_VDD、BL12V域100k下拉；96bit初始化并锁存后才允许显示。实际掉电过渡、驱动VDD下降但HV残留、3.3V先掉、CD40109反向供电与GPIO钳位仍BLOCKED；现有功能模型不能覆盖。GPIO卡高不能靠软件保证关闭，无独立心跳关断。本轮没有新增硬件保护或虚构复位时序保证。

**C3 HV5622：** 逻辑VDD10.8–13.2V，高电平要求≥VDD−2V，3.3V GPIO不能直驱；当前各DIN/CLK/LAT/BL经CD40109升压，DOUT经下转换回3.3V。原生审计确认MCU→L→C→R串行、CLK/LAT/BL并行、POL=DRV_VDD；HVOUT1–30映射90阴极，NC/31/32保持独立。下降沿移位，LE高透明/低保持；BL低且POL高全关。≤8MHz只是HV5622自身上限，不能视为含CD40109及线缆的可用频率。建立/保持和锁存脉宽、上下转换传播延迟与walking-one仍待逻辑分析仪实测。

HV5622推荐输出≤220V、绝对最大230V，封装耗散和温度降额亦受限；手册100mA测试下VOL≤15V不是给所有通道无限连续电流的许可。工作点2.25–3mA低于该测试电流但仍需实际VOL、整片热及灭灯泄漏验证。此处只作接口/额定审查，非台架PASS。

官方依据：[Microchip HV5622 DS20005854A](https://ww1.microchip.com/downloads/en/DeviceDoc/20005854A.pdf)、[TI UC3843 Rev.H](https://www.ti.com/lit/ds/symlink/uc3843.pdf)，本轮在线核对；CD40109B及厂商PDF原件/哈希已在 `docs9/sources/A9_1/manifest.json`。QS30规格以仓库原厂扫描为依据，不用经销商摘要替代。

## 5. 文件变更与复现

| 文件/目录 | 原因/对应问题 | 验证与风险 |
|---|---|---|
| `kicad/projects/QS30-9_MAIN/QS30-9_MAIN.kicad_pcb` | 38个NC单节点同步 | 最终原生DRC/全引脚核对；仍为PRELIM无布线 |
| `kicad/projects/QS30-9_DISPLAY/QS30-9_DISPLAY.kicad_pcb` | 17个NC单节点同步 | 同上；保持左右模板接口 |
| `design9/kicad_gen.py` | 生成时保留同名独立NC | 生成pad网络/几何与实际文件一致；更改引用/引脚名后须重新导出验证 |
| `design9/reconcile9.py` | 工具路径探测、严格NC集合核对 | 10.0.8全流程执行；基线旧PCB将触发新增NC检查，非历史结果重写 |
| `design9/electrical_sprint01.py` | 精确局部修复脚本 | 只允许空net NC赋值，断言全部55项，保留CRLF；对已修复PCB重跑将拒绝，避免重复应用 |
| `design9/sprint01_sim.py` | 原生应力测量和独立泄放实验 | v1语法失败保留、v2完成；等效模型限定 |
| `design9/sprint01_report.py` | 全量分类、几何/网表/生成器检查、哈希与压缩 | 实际运行rc0；只写本轮派生报告，不覆写原生报告 |
| `kicad/logs/sprint01_*` | before/中间/final/verified及NC逐脚记录 | 原生命令与输入哈希全部保留；只有verified为最终严格NC验收 |
| `sim/a9_2/sprint01_actual/` | 9例现有电路重跑 | decks、日志、执行记录、波形与压缩数据 |
| `sim/a9_2/sprint01_measurements/`、`sprint01_measurements_v2/` | 失败及修正测量、3个RC实验 | 不删除旧失败；波形原始文本仍在磁盘，gzip保留精确字节 |
| `docs9/electrical_sprint01/` | drc-before.json/drc-after.json/erc-after.json、逐项CSV、checks、manifest | 聚合JSON按board键保留原生数组，不丢未连接/一致性段 |
| 本报告、README | 当前证据入口 | 不改历史PASS/FAIL、其他Σ/ELBridge/BOM/机械记录 |

复现用已有隔离Python；先新命名运行目录，原生捕获拒绝覆盖历史：

```powershell
$env:KICAD_CLI='C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
& tools/review_venv/Scripts/python.exe design9/reconcile9.py --run NEW_NATIVE_RUN
& tools/review_venv/Scripts/python.exe design9/validate_freeze9.py --run NEW_NATIVE_RUN
& tools/review_venv/Scripts/python.exe design9/safety_sim9.py --run NEW_SIM_RUN --native-run NEW_NATIVE_RUN --cases startup_9,startup_no_load,startup_6,input_11_4,input_12_6,line_step,six_to_nine,reset_stuck,input_poweroff
& tools/review_venv/Scripts/python.exe design9/sprint01_sim.py --run NEW_MEASURE_RUN
```

sprint01_sim的参照deck固定指向本轮实际startup_9（见其source_sha256），用于可复现本轮电路，不会自动冒用后续设计版本。核心脚本/模型/可执行文件哈希见 [manifest](electrical_sprint01/manifest.json)。压缩波形与原始文本可交叉解压校验。

辅助执行问题如实记录：第一次Kiutils按Windows GBK读UTF8失败，改显式UTF8；派生报告重跑比较tuple/list类型失败，改JSON规范化；结构ERC首次调用漏nets参数，补正确签名；最后控制台GBK编码失败改ASCII转义打印。均为本轮报告脚本问题，无电路改动/数据伪通过。首次PCB写入换行变LF后恢复原CRLF，保留after中间捕获，final/verified重新捕获字节哈希。`git diff --check`须用 `-c core.whitespace=cr-at-eol`尊重仓库原有-text/CRLF，未借此忽略真实空格错误。

## 6. Git与下一轮

本轮只在本地独立分支工作，无push/force/reset/历史重写。由于高压控制、保护与真实封装未达到可靠工程验收，本轮不创建完整电气闭合commit，所有修改与证据留在工作区供审查；NC局部修复已可靠验证，但不以此提交整机通过声明。未下单、未生成制造订单或发送Gerber。

下一轮依赖顺序：

1. 冻结UC3843确切型号、输入规格、磁件与MOS/二极管模型，先判断12→172V拓扑/死区/占空和损耗可行性。
2. 评估源极Kelvin采样、限流与斜坡/补偿候选，证明自主启动/空载/轻载/九管及输入包络闭环；再同步局部原理图。
3. 重设计受限电流锁存、硬件复位许可、快速OVP/第二关断链；通过自主过载/短路/反馈故障与掉电矩阵。
4. 获取真实封装/管座、HV连接器、材料/污染等级/适用规范/板厂能力，冻结绝缘和泄放单故障要求。
5. 批准布局方案后真实放置/布线，再消除未布线/库/庭院/丝印问题并执行原生DRC/ERC及实物位序验证。
