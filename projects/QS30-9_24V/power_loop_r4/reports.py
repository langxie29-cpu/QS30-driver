"""Principal-reviewed R4 delivery; measurements are read, never synthesized here."""
from r4lib import *
import csv,collections
def md(name,s):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.strip()+'\n',encoding='utf8')
def table(name,rows):
 with(HERE/name).open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 design=json.loads((HERE/'EVT01/design_source.json').read_text());review=json.loads((HERE/'EVT01/latest_review.json').read_text());gen=json.loads((HERE/'EVT01/generation_receipt.json').read_text());calc=json.loads((HERE/'evidence/independent_calculations.json').read_text());measure=json.loads((HERE/'evidence/measurement_index.json').read_text());ledger=json.loads((HERE/'evidence/execution_ledger.json').read_text())
 usage=[]
 for p in sorted((HERE/'drafts').glob('*/execution.json')):
  x=json.loads(p.read_text());usage.append(dict(session=p.parent.name,**x))
 dump(HERE/'evidence/resource_summary.json',dict(utc=utc(),rounds=2,Flash_sessions=len(usage),Flash_session_cap=6,Flash_usage=usage,provider_tokens=sum(x['usage']['total_tokens']for x in usage),native_LT_calls=ledger['calls'],native_LT_cap=12,native_elapsed_s=sum(x['elapsed_s']for x in ledger['records']),child_Codex=0,additional_native_runs='Not justified by current gaps; unused quota is not a research target',E_review='finish_reason length; incomplete, never used as signoff',money='Provider billing/actual CNY UNKNOWN; session/token counts are not monetary hard caps'))
 md('ARCHITECTURE_DECISION_RECORD.md',r'''
# R4 架构决定 ADR-004 — 尚无合格的完整前级

2026-11-18；R3 冻结 98b6f81927592f0576e7eb4148e97fe2b14eab1c。主控独立审查；Flash 为草稿来源，不具有签核权。

**决定：架构冻结 HOLD。C（LM5069-1 外部功率开关）是下一步有限开发首选，尚未成为已选定、可保证的完整保护方案。** 不以 A 的加密模型失败为由宣称硬件失败，也不以 C 存在数据手册为由宣称替代成功。

## A / B / C 的取舍

A：U100 TPS26601 保留作总输入支路候选；原 R3 的 U101 TPS26601 不再被视为能够独立保证磁件故障峰流的器件。实际 MODE/ILIM、热态 SOA、带载关断最大时间和可运行模型仍缺证。R4 图中 U101 是 LM5069，不沿用旧的 RTN101。

B：33Ω 独立预充加旁路可以限制预充，但旁路闭合后不再限故障电流；旁路粘连、开断后下游储能、PWM 禁止时序仍需要第二套保护。最低输入 21.6V、R=33Ω 且−1%时，最大可交付负载功率 V²/(4R)=3.570W（标称3.535W）。原计算3.366W使用了+5%电阻，字段未注明该边界，见下述明确复算。永久串阻不能交付6W。永久12.4Ω在21.6V、R+1%时理论最大功率9.313W，不能错误声称它不能供6W；但26.4V短路持续耗散约56.8W，没有热态、单故障和阻燃资格，未选入正式候选。

C：LM5069-1 提供更可审查的电流比较器/计时器规格，但不能把典型电流环45µs、TIMER→GATE12µs当最大关断。数据手册电气表默认 VIN=48V；最大1.2µs仅对应150mV阶跃、GATE无负载的断路器测试，不包括真实Q101栅电荷、SOA或本项目21.6–26.4V全部条件。

## 一个决定性的可行窗口检查

保持 R3 原电流政策，启动峰流1.649249A；Rs容差±1%。不让最小48.5mV电流限制阈值干预启动，要求：

Rs_nom ≤48.5mV/(1.649249A×1.01)=29.116mΩ。

要在冷态3.1A参考点之前保证最大130mV断路器动作，即使暂时忽略所有延迟，要求：

Rs_nom ≥130mV/(3.1A×0.99)=42.359mΩ。

两条件无交集。因此，**直接替换控制器、保持R3电流政策、仅依赖快速断路器**的保证路线被否决。3.1A只是25°C降感10%的参考，既不是破坏电流，也不是热态安全上限；热态只会增加资格不确定性。这不证明所有 LM5069 架构不可行；降低正常/启动电流、改变频率/电感、或增加独立关断均需重新共同设计。

原50mΩ试算的最小稳定限流0.960A低于1.649A，不能偷换为已完成选型。原生图 **R111=HOLD_CURRENT_SETTING，Q101=DNP、型号和封装为空**。不在不成立的电流窗口上选择线性FET。

## 储能约束及执行决定

所有明确拟合的低压储能、12V/5V电源及 LT3757 VIN 去耦放在最终支路开关上游；L_FEED不拟合大电容。开关Coss、PCB、测量探头及吸收器件的有效后级能量仍UNKNOWN，绝不等同0。图纸受控禁用，不能靠此规划宣称已消除3.58A/14.17A反例。

47µF位置单变量实验，持续供电不切断：放在12.4Ω之后得到13.8627A，移到之前、之后保留1nF得到2.00490A。证明储能位置的重要性，不代表最终LM5069/热态磁件已合格；12.4Ω没有成为正式方案。

停止继续消耗仿真配额：缺失的是可实现电流窗口、真实开关与热态边界，不是更多理想延迟扫描。批准六项有限实验，未批准任何整机PASS、制造或HOLD解除。全部原始批准/否决见 evidence/codex_decisions_round1.json、codex_design_decision02.json、codex_round2_review.json。

明确复算：21.6²/(4×33)=3.534545W；R−1%=3.570248W。早期独立计算文件中 R33_max_deliverable_power_at21p6_V_W 的3.366W使用R+5%，不是标称值或最大交付功率的有利边界；原计算保留，标签澄清见 evidence/calculation_corrections.json。所有边界均小于6W，不影响否决结论。
''')
 # Explicit erratum, preserve the earlier calculation rather than silently rewriting evidence.
 dump(HERE/'evidence/calculation_corrections.json',dict(utc=utc(),field='R33_max_deliverable_power_at21p6_V_W',archived_value=calc['R33_max_deliverable_power_at21p6_V_W'],correct_nominal_W=21.6**2/(4*33),maximum_with_minus1pct_R_W=21.6**2/(4*33*.99),explanation='Earlier result3.366W used R34.65 (R+5%) in calculations.py but name did not state tolerance. This erratum makes nominal andminus1pct boundaries explicit; neither reaches6W. No source evidence overwritten.'))
 md('FRONTEND_ARCHITECTURE_COMPARISON.md',r'''
# 前级保护比较与故障能量边界

完整方案仍HOLD，下一步优先LM5069-1共同设计，不是合格替代声明。准确数值见 ADR、FAULT_ENERGY_BUDGET.csv、evidence/independent_calculations.json 与 calculation_corrections.json。

|维度|A TPS26601总输入+支路|B 独立预充/旁路|C LM5069-1外部FET|
|---|---|---|---|
|可保证峰流|ILIM静态条件可核查；下游储能不受其直接限流|预充路径可由R/V界定；旁路后无此界|48.5–61.5mV稳态限流，80–130mV断路器；R3政策下Rs窗口冲突|
|动作时间|真实带载最大动作/热态链未获保证|预充完成检测与旁路粘连后切断未完成|1.2µs仅无负载阶跃规格；45µs/12µs为典型，不是整链最大|
|故障能量|上游切断后仍有后级C/L/HV储能|旁路后C释放仍需处理|外FET可限定输入能量，不能消除其后的储能|
|单点故障|内部开关短路、RTN/SHDN异常、FLT未供电不能表示健康|旁路焊死、预充R开路/短路、误判完成|FET D-S短、Rs短、UVLO回路失效，独立第二切断仍需资格|
|重启|必须人工RESET后新START，不能自动恢复高压|预充失败锁存；旁路复位必须先确认残压|选-1锁存型；全链电源循环不得自动启动|
|获得性|准确TPS26601RHFR存在；本轮现货/价格UNKNOWN|继电器/背靠背开关未定型，UNKNOWN|LM5069MM-1/NOPB准确型号候选；Q101 UNKNOWN|
|复杂度/面积|双级较紧凑，热区约束未定|R脉冲能量+旁路+反馈，面积较大但未布局|额外FET、Rs、定时器、散热、单故障路径，面积UNKNOWN|
|成本|当前完整报价UNKNOWN|未选实物，UNKNOWN|控制器以外成本UNKNOWN|
|可测试性|需分域RTN探测，原模型加密受限|可测预充电流/旁路状态，但实体故障不在本轮授权内|外部Rs/GATE便于测量；最大延迟/SOA仍需厂家或授权实测|
|结论|保留U100候选，否决仅靠U101保证磁件故障安全|可做启动辅助，不能独立解决运行故障；不选永久33Ω|有规格优势但尚无闭合可实现窗口，有限开发首选/HOLD|

## 储能分区与返回路径

VIN接口→熔断器→U100前C/TVS→U100→中间C和偏置电源→U101/Q101→L_FEED残余C→电感→Boost开关/整流器→HV_BUS/输出C。低压功率返回PGND；控制、Kelvin和门驱通过专用星点网桥连接。U100 RTN100是其反接保护浮动参考，不能与PGND直接相连。

后级电容→电感→整流器→输出短路→PGND的回路不穿过前级限流开关。即使前级零延迟关断，已存储的½CV²仍可注入该回路；以输入支路电流替代电感电流会漏掉它。MOS D-S短时还有电容→电感→MOS→PGND路径。HV输出C的短路释放位于升压整流器之后，主要经负载/短路回路释放，不能混同为被U101限制的输入电流。

47µF、26.4V储能16.378mJ；1µF为0.34848mJ（均未加容差）。R3线性磁件下3.58A/14.17A反例保持。新受限位置试验只有低压C，没有HV输出C，没有真实开关延迟或控制器；135µH线性L、25°C和1nF后级残量为显式研究假设。持续输入永不关断，未使用有利的零延迟切断；仍没有热态饱和和真实后级寄生上界。

R3参数化前级含有利的理想动作/无限SOA假设，只可作为输出研究边界；R4 cap-only继承该限制。局部门驱12V也是刺激源，不是完整真实偏置供电。任何此类模型都不能用于宣称前级保护通过。

熔断器0451001.MRL、SMBJ33CA-E3/52仍是候选：源限流、熔断I²t、TVS夹压/能量、正常启动脉冲、U100/VIN绝对最大值及外FET热脉冲未协调。不能把1A熔断器等同1A电子限流。故障后必须锁存、残压有效且新人工命令；HOLD输入现为下拉阻断，未经资格不得跨接。
''')
 choices=[
 ('MOSFET','STP9NK50Z','RETAIN','STP9NK50Z + UCC27511DBVR + LM5164DDAR','外部真实12V驱动；内部7.2V不具有原10V RDS(on)保证','CANDIDATE/HOLD','TO220-3 / SOT23-6 / SO8 PowerPAD','真实12V轨/掉电/门极负脉冲/热态SOA未资格'),
 ('RECTIFIER','US1G-E3/61T','REPLACE','STPSC4H065D','SiC减少少子恢复；原厂未修改v13模型可运行，仍有Cj位移电流','CANDIDATE/HOLD','TO220AC','无BV模型；热态开关损耗/寄生/重复脉冲未资格；C3D04065A仅备选'),
 ('MAGNETICS','MSS1583-154KED','HOLD','MSS1583-154KED','正常研究保留；热态L(I,T)/磁芯损耗/故障允许时间未知','HOLD','14.8x14.8x8.6mm SMD','3.1A仅25C降感10%参考；不等同破坏阈值'),
 ('OUTPUT_CAP','ECQE2106JF','REPLACE','B32774D4106K000 x2','450V85C，105C计算330.3V，解决195V静态降额冲突','CANDIDATE/HOLD','31.5x15x24.5mm max P27.5 lead0.8mm','10u±10%；尺寸/成本增加；100kHz热态纹波与寿命未资格')]
 table('COMPONENT_SELECTION_DECISIONS.csv',[dict(category=a,before_MPN=b,decision=c,after_candidate=d,physical_basis=e,qualification=f,package=g,remaining_risk=h)for a,b,c,d,e,f,g,h in choices])
 derate=[
 ('Q20','STP9NK50Z','VDS500V; VGS±30V; RDS(on)保证VGS10V','外部12V局部VGS -11.3518..12.2607V；尚非整机','热态SOA/栅极负脉冲/门驱掉电UNKNOWN','HOLD'),
 ('U21','UCC27511DBVR','VDD4.5..18V；split4A/8A为器件驱动指标而非实际Qg速度保证','LM5164名义12.0938V；本轮局部宏模型成功','max传播/负输入/partial-power/12V过压链UNKNOWN','HOLD'),
 ('D20','STPSC4H065D','VRRM650V；4A在厂家Tc条件(约145C)，不是任意环境4A','局部VRpeak88.4949V、逆端口电荷5.53988nC','模型无BV；高温损耗/结温/重复换流/PCB寄生UNKNOWN','HOLD'),
 ('L20','MSS1583-154KED','150u±10%；DCRmax0.159Ω25C；3.1/3.6/3.9A为10/20/30%降感25C','R3 ILpeak1.649249A，Irms0.407808A，铜损约0.02644W25C','L(I,T)、磁损、热态故障峰流/时间UNKNOWN','HOLD'),
 ('C11/C12','B32774D4106K000','450V85C；105C330.3V；8Arms70C10kHz；ESR10.9mΩ/ESL24nH典型','195V静态要求低于330.3V；cap-only峰172.330V','非100kHz105C保证；寿命、实板温升/机械尺寸UNKNOWN','LIMITED_PASS_STATIC_VOLTAGE_ONLY'),
 ('RS20','WSL2512R0620FEA','62mΩ±1%；1W规定环境/焊盘条件','SENSE max0.103946V是cap-only，不代表完整新门驱回路','脉冲能量/Kelvin/热态阻值待资格；LT3757限流100/110/120mV','HOLD'),
 ('RB11..RB23','CRCW251249K9FKEG','系列1W70C/500V；100C线性功率约0.647W','单Rs短路最坏0.19243W；每串149.7k，双串','板上热阻/单点公共回流/误装/实体封装待核验','CANDIDATE/HOLD'),
 ('Q101/R111','UNKNOWN','没有已选线性FET和已闭合电流窗口','DNP / HOLD_CURRENT_SETTING','不能建立SOA或真实关断最大延迟','HOLD'),
 ('U100/F100/D100','TPS26601RHFR / 0451001.MRL / SMBJ33CA-E3/52','分别查各自额定，不能拼成已保证保护链','无本轮真实整链瞬态资格','源/熔断I2t/TVS/热态限流/RTN/单故障UNKNOWN','HOLD')]
 table('COMPONENT_DERATING_MATRIX.csv',[dict(ref=a,MPN=b,guarantee_and_conditions=c,observed_or_calculated=d,gap=e,status=f)for a,b,c,d,e,f in derate])
 md('BOM_CHANGE_IMPACT.md',r'''
# BOM与电路变更影响

本轮只是设计候选。MPN存在、模型运行、原理图可解析分别不是现货、器件电气合格或制造放行。

|变更|依据和具体参数|代价/新增风险|
|---|---|---|
|U101 TPS26601→LM5069MM-1/NOPB控制器候选|更多显式比较器规格；R111未定，Q101不装|电流窗口未闭合，不是可替换BOM；线性FET/SOA/面积/价格UNKNOWN|
|STP9NK50Z保留，增UCC27511DBVR|外部真实12V、上拉/下拉各22Ω、RGS10k；内部7.2V不声称10V导通保证|LM5164真实偏置支路/上掉电/12V过压/负VGS脉冲仍需资格|
|新增LM5164DDAR与TPS7A1601DGNR|68µH MSS1246T-683MLB；FB453k/49.9k→12.0938V；5V319k/100k→4.99867V|有效去耦、环路/纹波网络、旁路储能、偏置故障；无完整新供电SPICE通过|
|US1G升压整流→STPSC4H065D|650V4A SiC TO220AC，原厂v13模型|更大封装/成本；不能仅凭升耐压解释恢复；SiC仍有Cj损耗|
|2×ECQE2106JF→2×B32774D4106K000|10µF±10%、450V85C、330.3V105C；P27.5|体积与安装变化；本轮唯一可核实现时SKU/价格的材料项|
|反馈底臂1900.6Ω理想值→1.91k TNPW06031K91BEEA|真实E96候选，参考1.6V时输出169.1393V；0.1%与保守FB参考界165.43..172.86V|cap-only仍用1900.6Ω，不能将其169.985V移植为新图实际输出|
|泄放2×181.8k→2×149.7k|每串3×CRCW251249K9FKEG 49.9k；从1206草稿改2512，容纳单Rs短功率|170V总0.386W，195V总0.508W；与正常负载和热预算共同评估|
|独立保护器件化|TPS3700、TPS3808、SN74HCS74/14/08、实际光耦/三极管|最大延迟和诊断未闭合；四个HOLD下拉保持禁止|

升压二极管的REPLACE不禁止低频偏置支路DA1保留US1G；两处用途不同。LT3757 VIN和UCC VDD接V12；INTVCC继续内部7.2V，绝不接理想AUX12或强迫12V进入INTVCC。

既有33Ω永久串联路线否决；没有把12.4Ω研究元件悄悄写入正式BOM。没有为模型方便保留旧高温电容。普通阻容多数只确定值/封装，仍UNKNOWN准确订货号，未自动换为“相似件”。所有机械连接器、按钮、传感器安装件、Q101未定；测试焊盘为PCB_TEST_PAD，不冒充Keystone5000通孔件。
''')
 md('SAFETY_CIRCUIT_IMPLEMENTATION.md',r'''
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
''')
 # BOM rows retain UNKNOWN explicitly; inventory is not inferred from a design file.
 old=list(csv.DictReader((HERE.parent/'power_loop_r3/EVT01/EVT01_BOM_CANDIDATES.csv').open(encoding='utf-8-sig')));hist={r['MPN']:r['budget_unit_CNY_NOT_QUOTE']for r in old if r['budget_unit_CNY_NOT_QUOTE']not in['','UNKNOWN','PENDING']}
 b=[]
 for p in design['parts']:
  feature=p['kind']in['NT','FLAG','TP'];cap=p['mpn']=='B32774D4106K000';unknown=p['mpn'].startswith(('UNKNOWN','PENDING'))or p['mpn']=='DNP'
  b.append(dict(ref=p['ref'],MPN=p['mpn'],value=p['value'],quantity=1,footprint=p['footprint']or'UNKNOWN',group=p['group'],qualification=p['status'],MPN_state='PCB_FEATURE'if feature else'UNKNOWN'if unknown else'EXACT_CANDIDATE_NOT_RELEASED',reuse='PCB_FEATURE'if feature else'COMMON_DESIGN_CANDIDATE'if p['group']in['POWER','AUX','FRONTEND','INPUT']else'EVT01_SAFETY_OR_INTERFACE_CANDIDATE',physical_inventory='UNKNOWN',supplier='LCSC'if cap else'UNKNOWN',SKU='C3799662'if cap else'UNKNOWN',stock_snapshot='3545'if cap else'UNKNOWN',unit_USD='1.8139'if cap else'NOT_MATERIAL'if feature else'UNKNOWN',unit_CNY='NOT_MATERIAL'if feature else'UNKNOWN',verified_date='2026-11-18'if cap else'NOT_VERIFIED',price_source='https://www.lcsc.com/product-detail/C3799662.html'if cap else'UNKNOWN',historical_R3_unit_CNY_NOT_QUOTE=hist.get(p['mpn'],'UNKNOWN')if not feature else'NOT_MATERIAL',note=p['note']))
 table('EVT01_BOM_REVIEW.csv',b)
 material=[r for r in b if r['MPN_state']!='PCB_FEATURE'];unmapped=[r for r in material if r['MPN_state']=='UNKNOWN']
 dump(HERE/'evidence/BOM_summary.json',dict(utc=utc(),symbol_instances=len(b),material_instances=len(material),unknown_MPN_instances=len(unmapped),unknown_MPN_refs=[r['ref']for r in unmapped],verified_price_instances=2,verified_USD_subtotal=3.6278,complete_CNY_total='UNKNOWN',complete_USD_total='UNKNOWN',shared_instruments_excluded=True,PCB_assembly_shipping_tax='UNKNOWN and separate'))
 md('EVT01_COST_SCENARIOS.md',f'''
# EVT01 材料成本情景（2026-11-18）

**准确可采购完整BOM总价 UNKNOWN。** 当前{len(material)}个材料实例，{len(unmapped)}个实例仍缺准确MPN，另有封装/电气资格未闭合；即便型号准确也不能自动算作现货。全部逐项见 EVT01_BOM_REVIEW.csv。PCB特征、网桥和ERC标志不冒充购买器件。

|情景|已核实小计|其余/总价|工程解释|
|---|---|---|---|
|仅功率级|两只TDK输出电容 USD3.6278|控制器、MOS、SiC、磁件、阻容等价格UNKNOWN；总价UNKNOWN|只是比较，不推荐为裸板高压试验方案|
|功率级+必要安全保护|同上|前级功率FET/保护/偏置/锁存/检测/外罩等UNKNOWN；总价UNKNOWN|前级与诊断未资格，不能据此上电|
|完整EVT01候选|同上|接口、按钮、传感器安装、受控负载等UNKNOWN；总价UNKNOWN|非可下单制造包|

LCSC C3799662 页面确认为 TDK B32774D4106K000，库存快照3545，最小1，1–9只单价USD1.8139，两只USD3.6278；非大批量USD1.0738档。精确 __NEXT_DATA__ 路径、价格阶梯、页面SHA见 evidence/verified_cap_supplier.json。公开目录快照不是锁价报价，库存未预留。运费、税、汇率未知，不转换为虚构人民币金额。JLC装配目录不是独立元件零售报价。

R3约¥515.20含占位估价，只作为历史规划，不是R4报价。CSV仅对完全相同MPN保留历史单价单独列，不转移到更换后的器件，不把UNKNOWN加为0。设计复用不等同已有实物库存，库存均UNKNOWN。正式版/验证板共享候选以COMMON_DESIGN_CANDIDATE标识；测量/保护接口以EVT候选标识；尚无已核实库存可冲减。

项目材料成本单独统计。恒压恒流电源、示波器、焊台属于Σ实验室跨项目设备，未计入材料BOM；PCB、装配、外罩加工、运费和仪器均不能用已知电容小计代替。本轮未采购、未下单。
''')
 q=dict(baseline_R3=BASELINE,overall='HOLD',model_validity='LIMITED typical/local models; encrypted TPS model unavailable; no full new frontend/bias validation',electrical='INCONCLUSIVE; energy-after ELECTRICAL_FAIL preserved',EDA=dict(native=True,authority='KiCad10.0.8',sheets=gen['native_sheets'],devices=gen['parts'],pins=gen['pins'],review=review['run'],ERC=review['ERC'],pin_comparison=review['pin_comparison']['status'],GUI='First-run privacy/update prompt; project GUI open not observed',PCB=False,DRC=False,status='PARTIAL/HOLD'),manufacturing='HOLD',limits=dict(mean_V=[164.9,175.1],raw_ripple_Vpp=1,normal_peak_V=180,coldstart_s=1,load_recovery_s=.1,fault_peak_V=195),cases=measure,holds={**{f'H{i:02d}':'UNCHANGED_HOLD'for i in range(1,11)},**{f'24V-{i:02d}':'UNCHANGED_HOLD'for i in range(7,11)},'manufacture':'UNCHANGED_HOLD'},cost='Complete purchasable total UNKNOWN; verified2caps USD3.6278 only',model_text_is_evidence=False,qualification_basis='Actual native waveforms + explicit interval calculations, limited to listed scope')
 dump(HERE/'QUALIFICATION_MATRIX.json',q)
 md('EVT01/README.md',f'''
# NXT-PWR-EVT01 — 原生KiCad候选，禁止制造/高压上电

权威工程为 **NXT-PWR-EVT01.kicad_pro**，根图同名.kicad_sch。KiCad10.0.8原生CLI真实读取、导出XML网表和全部SVG；不是把CSV/JSON当原理图。工程共{gen['native_sheets']}页、{gen['parts']}个器件/声明实例、{gen['pins']}个物理针脚，包含明确HOLD/DNP区。

选择KiCad：本机实际安装CLI且有可读取原生封装库；嘉立创专业版既有文件不具有本轮完整导出/审查链，因此不设为R4权威。未改动旧工程。design_source.json是主控物理针脚/连接生成输入，最终可检查原生.sch才是图纸交付；pin_connections.csv与实际原生XML比较仅验证生成一致性，不能代替厂家针脚审查。

最新审查 **{review['run']}**：网表/SVG导出返回0，ERC返回5，**0错误、{review['ERC']['violations']}个lib_symbol_issues警告**。当前CLI配置未识别项目NXT自定义符号库登记；文件和嵌入缓存确实存在，独立sym upgrade解析返回0，但库配置问题未解决，不能宣称ERC干净通过。早期3错误/893警告、后续失败配置探测均完整保留，未增加自定义ERC排除。CLI默认ignored_checks（单次全局标签、四线交点、SPICE模型、封装过滤）原样记录在erc.json，不声称覆盖所有默认未启用规则。原生网表{review['pin_comparison']['expected_connected_pins']}个预期已连接引脚全部相同；其余显式NC。

真实图形预览位于上述审查目录/svg，证据快照含当次完整原生工程。UI首次启动停在更新/隐私选择页，未替用户选择；**未观察到GUI打开本项目**。因此交付可解析的真实原生文件，GUI首次打开检查仍待用户环境完成。此限制不被CLI成功掩盖。

关键器件厂商针脚详见 ../SAFETY_CIRCUIT_IMPLEMENTATION.md；footprint_audit.json核对本机实际.kicad_mod文件及pad集合，不等于热焊盘/焊接/本体机械资格。Q101、HV连接器、按钮/温度安装件等未定型，无封装的HOLD被显式列出。

Q101不装、R111未定、四个安全许可实物下拉，图纸不具备可运行完整前级。未提供PCB布局，没有.kicad_pcb，没有DRC或制造包。PCB_PLAN.svg只是无尺寸分区，不能据此采用2mm/3mm统一绝缘间距。所有原HOLD保持。

重新生成/检查步骤见 ../REPRODUCE.md。不要跨接HOLD节点或以导出成功当上电许可。
''')
 md('NEXT_ENGINEERING_DECISIONS.md',r'''
# 下一阶段必须解决的工程决定

1. **P0 前级与电流政策共同设计**：先关闭29.116/42.359mΩ窗口冲突，定义启动/正常峰流、真实最低L、频率/限流政策，再选Q101。厂家澄清21.6–26.4V最大限流/断路器/带载门极延迟、脉冲SOA、单点D-S短后的第二切断和熔断协调；不能继续扫描方便的理想延迟。
2. **P0 下游储能/磁件故障资格**：冻结实际Coss、MLCC、TVS、探头和布局寄生最大能量；获得Coilcraft热态L(I,T)、磁损、短脉冲允许时间或用保守新磁件路线。3.1A不是破坏值，线性模型不能给永久损伤/恢复资格。
3. **P0 偏置与故障关断**：独立12V过压防护、5V故障最大响应、partial-power、光耦热态CTR和最长关断；证明任一控制轨未供电不会健康放行。完成预充/旁路或明确不用旁路的真实输入方案。
4. **P1 安全有效性**：残压上下臂/地开路诊断、NTC脱落/热点滞后、手动按钮粘连、新请求/看门狗、锁存故障记录和开断状态见证。HOLD端不能直接接健康常量。静态阈值计算通过不等于全链峰值195V保证。
5. **P1 整机回归**：真实架构与真实偏置有足够模型/保证后，才做组合新门驱+SiC+电容+泄放+反馈R的输入/负载/故障回归；R4 cap-only不覆盖这一组合。热态开关/磁件/SiC损耗、RC吸收脉冲额定、Kelvin地弹需实体器件数据与将来另行授权的低能量实测。
6. **P1 EDA与制造审查**：解决本机NXT库配置警告，用户完成GUI首次初始化后打开复查；独立厂家逐针/热焊盘/封装审核；定义污染等级、材料组、海拔、过压类别、外罩/接插件/固定孔后才能建立间距规则。再布局、真实DRC、温升/绝缘与测试接口审核。目前无制造放行。
7. **P2 采购与负载**：补齐准确阻容/按钮/连接器/线性FET/安装件MPN，获取含税数量报价和库存。定义九只真实QS30动态/故障负载；5200Ω等效阻性负载不代表九管动态资格。

需要实际工程验证的项目是热耦合、热态磁件、封装温升、PCB寄生、可触及性/绝缘、实际短路关断与失效模式。继续跑典型SPICE不能产生这些保证。本轮没有授权任何实体高压/故障实验或制造；后续硬件活动须另行授权，H01–H10/制造HOLD不变。
''')
 md('REPRODUCE.md',r'''
# 复现入口与证据边界

冻结R3=98b6f81927592f0576e7eb4148e97fe2b14eab1c；R2=bd1762f6b801a004b01de0f31ba5bbb8e2a60a3d；R1=96a1afef5e55f84d002f754510b97d8cbd49334f。R4独立worktree/branch。evidence/preflight/baseline.json记录最初HEAD与2594个历史文件验证。禁止重新运行preflight.py覆盖原收据；收尾用final_verify.py。

## 读取与独立验算（不消耗LT/Flash调用）

Python解释器使用现有numpy环境：D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe。脚本r4lib.py明确标出本地历史路径，不声称任意机器零配置。需要先checkout冻结的R1/R2/R3或修改路径映射，再用SHA确认来源。

evidence/measurement_index.json与measurements/*.json是原始波形确定性提取。时间加权stats()包含窗口端点插值，峰峰值读取全部原采样点，不平滑/不挑低波动子窗。cap-only固定100–120ms，只有一个末段窗口；未声称完整新电路足够长稳态已资格。独立静态阈值/能量计算在calculations.py；先阅读calculation_corrections.json，不能覆盖旧计算证据。补充模型端口KCL/步长比较见supplemental_analysis.py及其输出（若存在）。

## 原生工程

在本目录执行：

```powershell
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' design_data.py
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' build_eda.py
& 'D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe' audit_eda.py
```

audit_eda每次新建时间戳目录，先快照再调用真实KiCad10.0.8 netlist、erc、svg，保留stdout/stderr与原生ERC JSON。CLI exe路径见r4lib。ERC返回5是存在违规，不能被视作0。当前NXT库配置警告未解决，配置探测失败保留；不修改用户全局库或自动豁免。GUI首次运行的更新/隐私页未代选，项目GUI加载未观察；原生CLI加载已证实。没有PCB/DRC。

## 六次原生LTspice

solver准确版本24.0.12.0 Windows Normal，exeSHA见preflight。每次实验都有执行前preregister.json：假设/唯一变量、完整网表/模型SHA、.tran、最大运行秒数、Gear与原容差、分析窗、预定义指标和输出路径；执行后日志/raw/SHA均保留。所有COMPLETED_UNREVIEWED只是进程状态；电气分类以measurements和QUALIFICATION_MATRIX为准。

experiments.py是已执行的六项定义，不是请求再执行。runner.py总台账最多12次，本轮已6次；继续调用需要有新的获批且可判别问题，不能因为剩余配额就自动运行。不要重新运行以覆盖既有目录。厂商模型不修改，未上传；从source_register*.json/ST_model_acquisition*.json的原厂URL取得并逐个SHA核对。授权模型使用条件仍由使用者遵守。LT .lib/.sub/EXE/PDF不在Git或release。

## 原始波形归档与恢复

所有R4 raw本地仍在；21个90MiB以内分卷存于GitHub私有草稿release qs30-power-loop-r4-evidence-20261118，未发布。清单evidence/raw_archive_manifest.json、github_artifacts.json包含原SHA、分卷SHA、远端digest和API地址。使用已授权git credential，不打印凭据：

```powershell
python download_evidence.py --list
python download_evidence.py --case sic_1ns --download-root NEW_DOWNLOAD_DIR --restore-root NEW_RESTORE_DIR
```

目的地必须新建，既有raw不覆盖。download_evidence解码R2原封不动QS30RAW1，少量mixed raw采用原字节gzip。只下载、校验、重建，不产生SPICE/API模型调用。final_verify.py核对历史2594文件、六个封存目录、七个已有解析/codec测试、21远端digest、一个远端下载恢复抽查；全部raw本地压缩重建也逐一验证。

保护：R1/R2原机制继承，R3与R4实验目录的Windows ACL禁止本账户写/删；Flash仅远端文本API，无工具/文件系统权限；执行器为主控。ACL不能抵抗管理员改ACL，不是独立安全账户沙箱。models/PDF在忽略的.local；raw无覆盖无删除。本轮新增缺失0；历史R2两份raw永久缺失照实登记，不伪造。

## Flash

两轮A/B/C与D/E/F，共六会话，0子Codex。prompts、drafts完整保存输入/响应/usage/终止原因；E达到4500输出token截断，审查不完整。不要自动重跑flash.py；会话数不等同token或人民币硬上限，账单UNKNOWN。主控所有采纳/否决见codex_*决策文件；任何草稿都不能解除HOLD。
''')
 md('ENGINEERING_REPORT.md',f'''
# QS30-9 POWER LOOP R4 — Hardware Design Convergence / HOLD

日期2026-11-18。冻结R3 **{BASELINE}**；独立分支 nxt/qs30-power-loop-engineering-r4。本轮完成有证据的取舍、六项有限LT研究和真实原生KiCad候选；**尚无可信闭合的完整前级保护架构，不允许制造/高压上电，原HOLD全部保持。** 交付允许保留不合格方案的明确否决，不能为了图纸完成率降低门槛。

## 状态分别报告

|领域|结论|
|---|---|
|模型有效性|原LT3757A/未修改SiC和UCC模型在有限夹具真实运行；TPS26601加密模型未解；SiC无BV；ST原MOS宏明确仅25°C；热态磁件与真实新前级/偏置缺失|
|电气资格|总体INCONCLUSIVE/HOLD；后级47µF反例ELECTRICAL_FAIL；输出电容单变量研究仅输出指标LIMITED_PASS|
|EDA完整性|真实KiCad10.0.8 {gen['native_sheets']}页/{gen['parts']}个器件与声明/{gen['pins']}针；CLI加载/导出成功；{review['pin_comparison']['expected_connected_pins']}个连接与源一致；ERC0错误/{review['ERC']['violations']}库配置警告，未干净通过；GUI首次初始化未完成|
|制造状态|HOLD；无PCB布局、无DRC、无制造包，Q101未定/不装、四许可下拉、部分MPN/封装缺失|
|数据保全|历史2594文件前后SHA核验；全部6份新增raw保留，21远端分卷digest核验和恢复抽查见final_verification；历史R2缺失2份不伪造|
|资金估算|完整采购总价UNKNOWN；仅核实2只输出电容SKU及公开目录价USD3.6278，不计税运汇率；R3¥515.20不是R4报价|

## 实质进展与定量对比

|研究项|R3/旧依据|R4新证据|资格边界|
|---|---|---|---|
|保护替代可行性|参数化理想前级不能保证热态/延迟|LM5069保持原峰流时Rs≤29.116mΩ与≥42.359mΩ无交集|否决直接替代保证；非普遍否决所有共同设计|
|储能位置|后级1/47µF线性夹具3.58/14.17A|47µF放12.4Ω后13.8627A、前2.00490A，持续输入从不切|只证明路径；实际开关Coss/热态边界未闭合|
|整流恢复局部对照|US1G端口负电荷约112.607nC、反压约399.972V|原厂STPSC4H065D模型5.53988nC、88.4949V；1ns/0.5ns shunt峰5.06356/5.04184A|Cj仍有瞬态；无BV不能评价雪崩，非系统/实体资格|
|真实门驱候选|内部7.2V不满足MOS10V RDS(on)保证|真实12V偏置原理图+UCC局部原厂宏；局部MOS VGS−11.3518..12.2607V|局部理想12V刺激不等于真实供电通过；负脉冲/热态/掉电HOLD|
|电容高温电压|ECQE2106JF250V高温与195V条件冲突|2×B32774D4106K000450V；105C330.3V|静态降额冲突已处理；100kHz热/寿命未证明|
|闭环电容单变量|R3 mean169.985183V、pp0.090472V、IL1.649249A|100–120ms mean169.985183V、pp0.188429V、峰172.329996V、SENSE0.103946V、IL1.649202A|原R3前级/7.2V/原泄放和反馈不变，非组合R4闭环资格|

本轮没有为了较小纹波重新调整补偿。新图1.91k反馈/149.7k双泄放/外部门驱/新前级组合未进行整机资格仿真。等效5200Ω负载不是九只QS30动态负载。输出波形通过不能代替应力和保护审查。

### SENSE与局部电流证据的实际意义

SiC 1ns/0.5ns窗口1.02–1.10µs，MOS三端口KCL为 i(VQD)+i(VQG)−i(VQS)=0；最大残差分别7.24e−10/5.15e−9A，低于执行前1mA条件，采样支路峰的步长变化约0.43%。电感电流不等于含门极/寄生位移/钳位分流的源极采样电流；保留原R2/R3根因证据，未通过降低灵敏度或改模型取得PASS。

外部封装VGS与模型内部芯片VGS不同。SiC半步局部外部−4.590..13.109V、内部约−0.000067..7.987V；UCC局部外部−11.352..12.261V、内部约−0.000041..11.907V。负栅钳位支路峰值分别约2.218A/5.422A，不能仅因VGS在±30V内就视钳位器件重复脉冲合格。厂商宏模型有限性、封装寄生和实际布局均影响推断；这些结果仍INCONCLUSIVE。原始名字、积分与SHA见 [补充提取](evidence/supplemental_waveform_analysis.json)，[实际波形图](evidence/figures/diagnostic_waveforms.svg)。

NTC初算采用名义100.9k并联负载；补上该负载±1%角点后电气trip81.5849..89.4152°C，见NTC_loading_corners.json。V5±3%是分析假设，未成为真实电源保证，热滞后依然UNKNOWN。

## 最终14项验收回答

1. **TPS26601还能继续？** 可保留U100总输入研究候选；不能再把其未知最大关断/热态边界作为电感故障保证。A完整保护未通过。
2. **更可信替代？** LM5069有更清晰部分规格，作为有限开发首选；没有找到已经闭合可实现窗口/真实开关SOA的完整替代。Q101 DNP、R111 HOLD。架构冻结HOLD。
3. **3.58A/14.17A已处理？** 已确认储能绕过前级限流的路径，并通过单变量试验证明搬移储能影响峰流；未在真实完整前级中解决，反例保持。
4. **MOS/驱动？** 条件保留STP9NK50Z，选真实外部12V+UCC27511。LM5164名义12.094V供LT3757 VIN和UCC，INTVCC仍7.2V。没有理想AUX系统PASS；12V过压/轨时序/热态SOA未通过。
5. **US1G？** 升压整流位置REPLACE为STPSC4H065D候选，C3D04065A为受限备选；不靠仅提高耐压证明恢复问题解决。偏置低频DA1另行保留US1G候选。
6. **磁件？** MSS1583-154KED故障资格HOLD；正常研究可用不证明热态故障安全。3.1A是25C降感参考，不是破坏电流。热态L(I,T)/磁芯损耗/允许脉冲未知。
7. **高温电容冲突？** 更换准确TDK型号，105°C静态330.3V大于195V，解决该静态冲突；热态纹波/寿命与机械装配仍HOLD。
8. **哪些已器件化？** 独立TPS3700 OVP、双残压、支路低见证、NTC开短窗口；TPS3808电源监视；HCS74故障/运行锁存和独立START/RESET；真实三极管/光耦关断；固定双泄放；12V域独立5V异常高关断。均有实物型号/针脚/网络，完整延迟/单故障资格未闭合，四HOLD端实际下拉。
9. **原生工程？** 有真实.kicad_pro/.kicad_sch/自定义库，CLI实际打开/导出/执行ERC；GUI首次隐私/更新初始化停留，未观察项目GUI加载。ERC仍库警告，部分HOLD元件未定，不能称可制造。无PCB/DRC。
10. **准确可采购成本？** 完整UNKNOWN。当前可核实TDK C3799662两只USD3.6278，公开目录库存3545，日期11-18，非锁价/非人民币报价。其他大部分当前报价/库存与若干MPN UNKNOWN，不能用历史¥515.20顶替。
11. **距制造审查差什么？** 可行前级及功率FET、真实最大时限/热态SOA、下游能量边界、磁件热态、轨OV/partial-power、残压地开诊断、实际九管负载、NTC热耦合、机械绝缘依据、完整MPN/封装、GUI/库/ERC独立复审、布局/DRC/热设计。
12. **需实际工程验证？** 热态磁件/核心损耗/允许脉冲、传感器贴合、PCB门源地弹及SiC寄生、器件结温、真实开断/熔断协调、防触碰/绝缘/泄放。典型SPICE不能提供保证；本轮没有实体实验授权。
13. **HOLD解除？** 没有。24V-07/08/09/10、H01–H10和制造HOLD均不变。局部静态降额修正不是原HOLD整体解除依据。
14. **R4实际推进？** 得到可复现架构否决与Rs不相容证明、储能位置证据、原厂SiC恢复对照、真实12V偏置/门驱设计、明确四类器件决定、实物保护针脚网络、原生工程/真实ERC、当前SKU/价格证据和全量raw保全。没有伪造保护通过。

## 执行、审查与资源

两协调轮、Flash六会话、**0子Codex**、**6/12次新原生LT调用**，实际LT墙钟合计{sum(x['elapsed_s']for x in ledger['records']):.3f}s。Flash费用UNKNOWN，会话/token不等于货币硬上限。A/B/C研究，主控独立决定；D/E/F对批准方案计算/逐针/对抗审查。E达到输出上限截断，不能视完整审查。主控拒绝多个错误公式、无保证时间和型号假设，原始草稿/usage与采纳否决完整保存。没有虚构另一个独立人类或子Codex签核。

所有实验执行前登记假设/变量/SHA/solver/时间窗/原容差/停止条件/输出；rc0只是完成，不是合格。分类沿用MODEL_FAIL/SOLVER_FAIL/EXECUTION_FAIL/ELECTRICAL_FAIL/INCONCLUSIVE/LIMITED_PASS。原始与失败ERC、源下载TLS/404、配置探测失败也保留。

## 工程入口

- [前级决定](ARCHITECTURE_DECISION_RECORD.md) / [比较](FRONTEND_ARCHITECTURE_COMPARISON.md) / [能量](FAULT_ENERGY_BUDGET.csv)
- [器件决定](COMPONENT_SELECTION_DECISIONS.csv) / [降额](COMPONENT_DERATING_MATRIX.csv) / [变更影响](BOM_CHANGE_IMPACT.md)
- [器件级安全](SAFETY_CIRCUIT_IMPLEMENTATION.md) / [原生EDA说明](EVT01/README.md) / [工程文件](EVT01/NXT-PWR-EVT01.kicad_pro)
- [BOM](EVT01_BOM_REVIEW.csv) / [成本](EVT01_COST_SCENARIOS.md) / [资格](QUALIFICATION_MATRIX.json)
- [复现](REPRODUCE.md) / [下一阶段](NEXT_ENGINEERING_DECISIONS.md) / [资源](evidence/resource_summary.json) / [收尾校验](evidence/final_verification.json)

Git提交以本报告所在commit为准；最终SHA另见交付回复与远端refs核查，避免自引用SHA。全部工作限软件/仿真/文档；未采购、未制造、未main合并、未实体高压操作。
''')
 print(json.dumps(dict(reports='WRITTEN',BOM_instances=len(b),unknown_MPN_instances=len(unmapped),native_sheets=gen['native_sheets'],Flash=len(usage),native_calls=ledger['calls']),ensure_ascii=False))
if __name__=='__main__':main()
