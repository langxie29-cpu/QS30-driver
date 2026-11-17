from r3lib import *
import csv
D=HERE/'EVT01';D.mkdir(exist_ok=True)
def csvout(name,headers,rows):
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(headers);w.writerows(rows)
csvout('EVT01_MODULE_MAPPING.csv',['formal_module','formal_reference','EVT01_module','reuse','change_or_gap','status'],[
 ['Input','F100/U100/D100','INPUT','保护体系和RTN边界','上游1A与支路候选1.5A需协调','HOLD'],
 ['HV branch','U101','FRONTEND','TPS26601RHFR及SHDN默认关','MODE402k/ILIM8k研究候选;原20k/MODE开路不改历史','HOLD'],
 ['Controller','U20 previous UCC candidate','PWM','LT3757A闭环研究候选','不导入旧UCC28C43物理引脚;LT3757A重新逐针建图','SCHEMATIC_INPUT'],
 ['Controller supply','AUX12/DRV12','CTRL_SUPPLY','供电有效/失电禁止需求','比较外12V偏置与内部7.2VLDO;未冻结','HOLD'],
 ['Power switch','Q20','Q20','STP9NK50Z TO220','封装LS/LD/LG与PCB额外L分开;热/SOA待证','RETAIN_RESEARCH'],
 ['Rectifier','D20','D20','US1G-E3/61T SMA','原模型保留;400V恢复/雪崩样事件阻塞','HOLD'],
 ['Magnetics','L20','L20','MSS1583-154KED','热L(I,T)/磁损缺失;不能用旧MSS1260替代','HOLD'],
 ['Current sense','R230/R36/CCS old values','RSRC/RF/CF','62mohm/22ohm/4.7nF','旧.82ohm/100ohm/220p数据不是R2候选','HOLD'],
 ['Gate loop','RG/RGS/XNEG/RNEG','GATE','22ohm/10k/SS14/2ohm','负栅分支MPN和重复脉冲资格','HOLD'],
 ['Compensation','VC','COMP','22k/6.8nF/100pF','物理值公差/布局/环路裕度待证','RETAIN_RESEARCH'],
 ['Feedback','R34A/B/R35','FB','2x100k plus1900.6ohm equivalent','1.9006k用可制造串联组合且误差重算','HOLD'],
 ['Storage','C11/C12 plus display caps','COUT','2xECQE2106JF','模块300n按独立可选模拟;ESR.1不是器件保证','HOLD'],
 ['Bleed','two181.8k branches','BLEED','两条独立2x90.9k','模块拆除不移去主板泄放;单开路重算','HOLD'],
 ['Independent protection','OVP/LATCH/THERMAL/RESIDUAL','SAFETY','独立硬件保护和人工事件','逐针实现未完整;不能用软件或行为源放行','HOLD'],
 ['Display','9xQS30/3xHV5622','NONE','不集成','以额定封闭负载接口接测试负载','OUT_OF_SCOPE'],
 ['Host','ESP32/USB','NONE','不集成正式主控','如接PC记录必须审仪器地与隔离;不供许可','OUT_OF_SCOPE']])
tests=[
 ('T01','不加高压的逐针/失电缺省','0..26.4V, all rail sequences','SHDN/GATE/BL or absent display permit, RTN','电阻限流/低压注入+差分电压','保护未有效期间支路与PWM禁用;无自动运行','H01/H02/H07'),
 ('T02','真实0V启动','21.6/24/26.4V fast and normal input','VIN,HV_IN24,IL,GATE,SENSE,HV,INTVCC,Iin','合格差分+校准电流探头;从输入首次建立记录','<=1s;164.9..175.1V;全程<=180V;各器件脉冲合格','H02/H06'),
 ('T03','连续稳态与功耗','6W等效电阻,各输入/温度','HV原始波形,Pin/Pout,器件温度,各支路RMS','连续整段波形与独立功率测量','均值164.9..175.1;<=1Vpp;各器件热/电额定及预定降额合格','H06'),
 ('T04','快速断电再接','短中长断电;实际残压分别记录','HV,branch,INTVCC,FAULT,RUN_TOKEN','人工新许可/自动恢复分别测试','无新人工许可不重启;无误许可;峰<=180V;非0V案例单列','H01/H02'),
 ('T05','PWM禁止被动路径','输入快接/PWM硬件关闭','IL,D20电流,HV,branch','电流探头及输入支路波形','不超热态磁件和器件脉冲边界;不得称输出已隔离','H03/H06'),
 ('T06','受控启动转闭环','预充/使能边界及公差','branch,IL,SHDN,SS,HV,FLT','多通道同步捕获','转接无电流/电压超额定;无假PG','H02/H06'),
 ('T07','输入保护开关热/SOA','正常浪涌及指定故障','Vds*I pass energy,case/board temperature','差分与电流同步去偏斜,热标定','总最大延迟与脉冲热边界有证据;无仅典型值放行','H02/H03'),
 ('T08','MOS/整流换流','最坏恢复相位/输入/温度','外VDS/VGS/Id/Is/Ig,D20 VR/IR/Qneg','高带宽差分,电流探头,去偏斜;记录探头寄生','外/本征推断分开;重复SOA与反向额定通过;不把30A半正弦套用ns恢复','H06'),
 ('T09','过载与输出短路','持续过载/不同故障时刻/CIN','IL,IeFuse,HV,FLT,关断能量','先低能量缩放;高压注入须另行批准','过载掉压另列;指定故障<=195V;器件限流/热/SOA合格且锁存','H02/H03/H06'),
 ('T10','MOS短与支路卡通','单故障及指定双故障','实际输入切断/被动通路/源熔断I2t','能量预审后独立受控夹具','不能依赖PWM;未容错情况明确失败并HOLD','H03'),
 ('T11','独立OVP','FB开路/上臂短/阈值公差','HV,独立检测,锁存,门驱,支路','独立分压/基准;从物理越阈计时','指定HV峰<=195V;总最大延迟与剩余能量闭合','H05'),
 ('T12','失电/偏置异常','AUX/INTVCC/监控轨欠压/掉电/异常先后','GATE/VGS,branch,HV,permit','可编程低压轨/差分,禁止地夹到RTN','无未定义许可/反灌超额定;故障置位优先','H01/H07'),
 ('T13','负载阶跃','R10400->5200->10400;随后真实范围','HV,IL,IN','封闭额定电子负载/电阻切换','恢复<=100ms;正常峰<=180V;纹波窗口预登记','H06'),
 ('T14','空载/最小负载','保留泄放/FB;模块模拟连接/拆除','HV,gate bursts,纹波','高阻差分探头负载计入','均值/纹波/峰值满足适用正常指标','H06'),
 ('T15','泄放单故障','195V/最大C/任一泄放开路/模块拆除','HV实际下降/独立残压有效性','输入支路确认关;独立高阻测量','沿用5s到60V工程门槛并含误差;未证明可触摸','H04/H08'),
 ('T16','残压/参考故障','检测上臂/下臂/返回地断开','检测有效性/RESET/START','先低压故障缩放,高压另审','未知/不一致禁止复位;不能谎报低压','H04/H08'),
 ('T17','温感与热态磁件','传感器开短/高低温/负载','磁件L(I,T),表温/结温估算,阈值','温箱与校准传感/损耗模型','真实热饱和/温度降额及传感有效窗通过','H06/H09'),
 ('T18','机械/探头/接地','盖闭/盖开/仪器多地/维护','防触及路径、额定、残压指示','机械检查+绝缘/接线图独立评审','无裸HV排针;仪器地不短RTN/SW;额定/间距依据冻结','H10'),
]
csvout('EVT01_TEST_MATRIX.csv',['id','test','conditions','expected_observables','method','pass_condition','hold_dependency','authorization'],[list(t)+['FUTURE_TEST_REQUIRES_SEPARATE_HARDWARE_AUTHORIZATION'] for t in tests])
rows=[]
def bom(ref,mpn,package,qty,value,budget,channel,status,note):rows.append([ref,mpn,package,qty,value,budget,channel,status,note])
bom('U20','LT3757AEMSE#PBF','MSE MSOP10 EP',1,'controller',65,'ADI authorized distributors / DigiKey / Mouser','RESEARCH_CANDIDATE','准确封装针脚见ADI RevH p2;预算非报价')
bom('Q20','STP9NK50Z','TO-220',1,'500V7.2A',8,'ST authorized / DigiKey / Mouser','RETAIN_RESEARCH_HOLD','7.2V门驱RDSon保证及脉冲SOA未闭合')
bom('D20','US1G-E3/61T','SMA DO-214AC',1,'400V1A',2,'Vishay authorized / DigiKey / Mouser','RETAIN_MODEL_HOLD','反恢复/雪崩样事件未资格')
bom('L20','MSS1583-154KED','14.8x14.8x8.6mm SMD',1,'150uH10%',35,'Coilcraft direct / Mouser','RETAIN_RESEARCH_HOLD','热态L(I,T)/磁损缺失')
bom('RSRC','WSL2512R0620FEA','2512',1,'62mohm1%1W',7,'Vishay authorized / DigiKey','NEW_CANDIDATE_NOT_ORIGINAL','公开列表仅可订购且长交期;不能称现货;脉冲保证待证')
bom('U100/U101','TPS26601RHFR','RHF VQFN24 5x4mm EP',2,'input protection',42,'TI direct / authorized DigiKey / Mouser','HOLD','MODE/ILIM协调;RTN/EP;原厂模型受限')
bom('F100','0451001.MRL','SMD fuse 2410',1,'1A',5,'Littelfuse authorized','HOLD','I2t/源限流/故障协调;不得单凭标称1A')
bom('D100','SMBJ33CA-E3/52','SMBJ DO-214AA',1,'bidirectional33VTVS',3,'Vishay authorized','HOLD','浪涌条件和最大钳位待审')
bom('C100','EEUFR1J470','radial electrolytic',1,'47uF63V upstream',4,'Panasonic authorized','CANDIDATE','上游位置明确;不自动放在U101后')
bom('C11/C12','ECQE2106JF','radial27.5mm pitch',2,'10uF250V5%',25,'Panasonic authorized / DigiKey / Mouser','HOLD_ESR_RIPPLE','31x15.9x25.8mm;85C以上电压降额;不是耐压无限的安全电容')
bom('RF/RG','RC0603FR-0722RL','0603',2,'22ohm1%',.2,'Yageo authorized','CANDIDATE','RF与栅电阻各自脉冲/寄生审查')
bom('CF','GRM1885C1H472JA01D','0603',1,'4.7nF50V5%C0G',.8,'Murata authorized','CANDIDATE_MPN_VERIFY','全温C0G与公差待逐料确认')
bom('RNEG','RC0805FR-072RL','0805',1,'2ohm1%',.3,'Yageo authorized','HOLD_PULSE','RNEG重复脉冲不得仅凭平均功率')
bom('XNEG','SS14-E3/61T','SMA',1,'40V1ASchottky',2,'Vishay authorized / LCSC C47460','CANDIDATE_MODEL_MATCH_HOLD','原SS14模型不自动证明Vishay实物匹配;不替换历史字节')
bom('RGS','RC0603FR-0710KL','0603',1,'10kohm1%',.1,'Yageo authorized','CANDIDATE','默认关栅')
bom('RB1A/B/RB2A/B','TNPW120690K9BEEA','1206',4,'90.9kohm0.1%',2,'Vishay authorized','CANDIDATE_MPN_VERIFY','两条各181.8k;耐压/爬电/故障短路审查')
bom('RFB1/RFB2','TNPW1206100KBEEA','1206',2,'100kohm0.1%',2,'Vishay authorized','CANDIDATE','上臂各自耐压;FB不能兼作独立OVP')
bom('RFB3a','TNPW06031K90BEEA','0603',1,'1.9kohm0.1%',2,'Vishay authorized','CANDIDATE','与.6ohm串联形成1900.6ohm;组合误差需回归')
bom('RFB3b','PENDING_0R6_QUALIFIED_MPN','0603 candidate',1,'.6ohm',1,'authorized channel pending','BLOCKER','不得把理想1900.6ohm当现成料号')
bom('RCOMP','RC0603FR-0722KL','0603',1,'22kohm1%',.1,'Yageo authorized','CANDIDATE','保持补偿研究值')
bom('CCOMP','GRM1885C1H682JA01D','0603',1,'6.8nF50V5%C0G',.8,'Murata authorized','CANDIDATE_MPN_VERIFY','容差需回归')
bom('CHF','GRM1885C2A101JA01D','0603',1,'100pF100V5%C0G',1,'Murata authorized','CANDIDATE_MPN_VERIFY','低压VC滤波;准确库存/尺寸待证')
bom('CSNUB','PENDING_100pF_630V_C0G','1206/1210 pending',1,'100pF high voltage',3,'authorized pending','BLOCKER','恢复时吸收支路电压远高于正常直流;不得装100V料件')
bom('CSS','GRM188R71H104KA93D','0603',1,'100nF50V10%X7R',.5,'Murata authorized','CANDIDATE','SS时序温度/偏压')
bom('CINT','GRM21BR71E106KA73L','0805',1,'10uF25V10%X7R',2,'Murata authorized','HOLD_EFFECTIVE_C','偏压/温度后必须>=4.7uF;未证明')
bom('CIN local','PENDING_1u_50V_MIN_C','0805/1206 pending',1,'1uF研究值',2,'authorized pending','BLOCKER','总下游电容包括VIN旁路,与故障能量一起冻结')
bom('RRT','RC0603FR-07140KL','0603',1,'140kohm1%',.1,'Yageo authorized','CANDIDATE','100kHz量级;实际频率记录')
bom('MODE101','RC0603FR-07402KL','0603',1,'402kohm1%',.1,'Yageo authorized','CANDIDATE','只回RTN101')
bom('ILIM101','PENDING_8K000_1PCT','0603',1,'8kohm1%',1,'authorized pending','BLOCKER','8.06k不是8k,值改变需计算;无虚构料号')
bom('CdVdT101','PENDING_47n_C0G_50V','0805/1206 pending',1,'47nF10%orbetter',3,'authorized pending','BLOCKER','以真实有效Cmin/Cmax替代纯假设')
bom('OVP/LATCH/UV/THERMAL/RESIDUAL','PENDING_REVIEWED_SAFETY_BOM','mixed',1,'independent safety assembly allowance',120,'authorized suppliers pending','BLOCKER','不能由一个behavioralFAULT元件代表')
bom('HV ports/cover/interlock','PENDING_RATED_TOUCH_PROTECTED_PARTS','enclosed',1,'protected interfaces allowance',100,'rated connector vendors pending','BLOCKER','禁止普通裸排针;额定/机械评审')
csvout('EVT01_BOM_CANDIDATES.csv',['references','MPN','package','quantity','value','budget_unit_CNY_NOT_QUOTE','candidate_channel','status','notes'],rows)
dump(D/'budget_summary.json',dict(currency='CNY',components_allowance=sum(float(r[5])*int(r[3]) for r in rows),PCB_assembly_shipping_instruments_excluded=True,not_supplier_quote=True,no_purchase=True,incomplete_safety_parts=True))
print('Generated',len(rows),'BOM rows and',len(tests),'test rows')
if __name__=='__main__':pass
