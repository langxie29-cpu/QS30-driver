"""Principal-owned physical pin/net source for native EVT01. No worker code execution."""
from r4lib import *
import csv
PARTS=[];TYPES={}
def typ(name,pins):TYPES[name]={str(n):(label,kind)for n,label,kind in pins}
def add(ref,kind,mpn,value,nets,group,footprint='',status='CANDIDATE',note='',source=''):
 pins={str(k):v for k,v in nets.items()};assert set(pins)==set(TYPES[kind]),(ref,set(TYPES[kind])-set(pins))
 assert not any(p['ref']==ref for p in PARTS)
 PARTS.append(dict(ref=ref,kind=kind,mpn=mpn,value=value,pins=pins,group=group,footprint=footprint,status=status,note=note,source=source))
def r(ref,value,a,b,g='POWER',size='0603',mpn=None,note=''):
 add(ref,'R',mpn or'UNKNOWN_ORDER_CODE_'+value,value,{1:a,2:b},g,f'Resistor_SMD:R_{size}_{dict(zip(["0603","0805","1206","2512"],["1608","2012","3216","6332"]))[size]}Metric',status='CANDIDATE_MPN_VERIFY'if not mpn else'CANDIDATE',note=note)
def c(ref,value,a,b,g='POWER',size='0603',mpn=None,note=''):
 add(ref,'C',mpn or'UNKNOWN_ORDER_CODE_'+value,value,{1:a,2:b},g,f'Capacitor_SMD:C_{size}_{dict(zip(["0603","0805","1206","1210"],["1608","2012","3216","3225"]))[size]}Metric',status='CANDIDATE_EFFECTIVE_C_HOLD',note=note)
def tp(ref,net,g='INTERFACES',note='LV observation only'):
 add(ref,'TP','PCB_TEST_PAD','TP_'+net,{1:net},g,'TestPoint:TestPoint_Pad_D1.5mm',status='HOLD_TEST_INTERFACE',note=note)
def init_types():
 for name in ['R','C','L','F','SW','NT']:typ(name,[(1,'1','passive'),(2,'2','passive')])
 typ('D',[(1,'K','passive'),(2,'A','passive')]);typ('Q',[(1,'G','input'),(2,'D','passive'),(3,'S','passive')]);typ('NPN',[(1,'B','input'),(2,'E','passive'),(3,'C','open_collector')]);typ('TP',[(1,'TP','passive')]);typ('PORT',[(1,'POS','passive'),(2,'RETURN','passive')]);typ('FLAG',[(1,'PWR','power_out')])
 typ('LT3757A',[(1,'VC','passive'),(2,'FBX','input'),(3,'SS','passive'),(4,'RT','passive'),(5,'SYNC','input'),(6,'SENSE','input'),(7,'GATE','output'),(8,'INTVCC','power_out'),(9,'SHDN_UVLO','input'),(10,'VIN','power_in'),(11,'GND_EP','power_in')])
 typ('UCC27511',[(1,'VDD','power_in'),(2,'OUTH','output'),(3,'OUTL','output'),(4,'GND','power_in'),(5,'IN-','input'),(6,'IN+','input')])
 pins=[]
 funcs={8:('IN','power_in'),9:('IN','power_in'),10:('UVLO','input'),12:('OVP','input'),13:('MODE','input'),14:('SHDN','input'),15:('RTN','passive'),17:('GND','power_in'),18:('IMON','output'),19:('ILIM','passive'),20:('dVdT','passive'),22:('FLT','open_collector'),23:('OUT','power_out'),24:('OUT_parallel23','passive'),25:('EP_to_RTN','passive')}
 for n in range(1,26):pins.append((n,*funcs.get(n,('NC','no_connect'))))
 typ('TPS26601',pins)
 typ('LM5069',[(1,'SENSE','input'),(2,'VIN','power_in'),(3,'UVLO','input'),(4,'OVLO','input'),(5,'GND','power_in'),(6,'TIMER','passive'),(7,'PWR','passive'),(8,'PGD','open_collector'),(9,'OUT','input'),(10,'GATE','output')])
 typ('LM5164',[(1,'GND','power_in'),(2,'VIN','power_in'),(3,'EN_UVLO','input'),(4,'RON','passive'),(5,'FB','input'),(6,'PGOOD','open_collector'),(7,'BST','passive'),(8,'SW','power_out'),(9,'EP_GND','passive')])
 typ('TPS7A1601',[(1,'OUT','power_out'),(2,'FB','input'),(3,'PG','open_collector'),(4,'GND','power_in'),(5,'EN','input'),(6,'NC','no_connect'),(7,'DELAY','passive'),(8,'IN','power_in'),(9,'EP_GND','passive')])
 typ('TPS3700',[(1,'OUTA','open_collector'),(2,'GND','power_in'),(3,'INA+','input'),(4,'INB-','input'),(5,'VDD','power_in'),(6,'OUTB','open_collector')])
 typ('TPS3808',[(1,'RESET_N','open_collector'),(2,'GND','power_in'),(3,'MR_N','input'),(4,'CT','passive'),(5,'SENSE','input'),(6,'VDD','power_in')])
 typ('HCS74',[(1,'CLR1_N','input'),(2,'D1','input'),(3,'CLK1','input'),(4,'PRE1_N','input'),(5,'Q1','output'),(6,'Q1_N','output'),(7,'GND','power_in'),(8,'Q2_N','output'),(9,'Q2','output'),(10,'PRE2_N','input'),(11,'CLK2','input'),(12,'D2','input'),(13,'CLR2_N','input'),(14,'VCC','power_in')])
 typ('HCS14',[(1,'A1','input'),(2,'Y1','output'),(3,'A2','input'),(4,'Y2','output'),(5,'A3','input'),(6,'Y3','output'),(7,'GND','power_in'),(8,'Y4','output'),(9,'A4','input'),(10,'Y5','output'),(11,'A5','input'),(12,'Y6','output'),(13,'A6','input'),(14,'VCC','power_in')])
 typ('HCS08',[(1,'A1','input'),(2,'B1','input'),(3,'Y1','output'),(4,'A2','input'),(5,'B2','input'),(6,'Y2','output'),(7,'GND','power_in'),(8,'Y3','output'),(9,'A3','input'),(10,'B3','input'),(11,'Y4','output'),(12,'A4','input'),(13,'B4','input'),(14,'VCC','power_in')])
 typ('VOS618A',[(1,'LED_A','passive'),(2,'LED_K','passive'),(3,'E','passive'),(4,'C','passive')])
def generate():
 init_types()
 # References are a new EVT01 namespace; historical design is untouched.
 add('J100','PORT','UNKNOWN_ENCLOSED_24V_CONNECTOR','24V_INPUT',{1:'VIN_CONNECTOR',2:'PGND'},'INPUT',status='HOLD_MECHANICAL')
 add('F100','F','0451001.MRL','1A',{1:'VIN_CONNECTOR',2:'VIN_RAW'},'INPUT','Fuse:Fuse_Littelfuse-NANO2-451_453',note='Actual451/453familyfootprint; I2t/source coordination HOLD')
 add('D100','D','SMBJ33CA-E3/52','TVS_33V_BIDIR',{1:'VIN_RAW',2:'PGND'},'INPUT','Diode_SMD:D_SMB',note='Bidirectional physicaldevice; not proof24P<40V during surge')
 un={n:None for n in TYPES['TPS26601']};un.update({'8':'VIN_RAW','9':'VIN_RAW','10':'U100_UV','12':'U100_OV','14':'U100_SHDN','15':'RTN100','17':'PGND','19':'U100_ILIM','20':'U100_DVDT','22':'U100_FLT_LOCAL','23':'V24P','24':'V24P','25':'RTN100'})
 add('U100','TPS26601','TPS26601RHFR','TPS26601_MAIN',un,'INPUT','Package_DFN_QFN:Texas_RHF0024A_VQFN-24-1EP_4x5mm_P0.5mm_EP2.65x3.65mm',status='HOLD_FRONTEND_TIMING',note='MODE open =>circuitbreaker latch; RTN100 never shorttoPGND; EPlogical25 is physicalPAD')
 for ref,val,a,b in [('R101','160k','VIN_RAW','U100_UV'),('R102','10k','U100_UV','RTN100'),('R103','240k','VIN_RAW','U100_OV'),('R104','10k','U100_OV','RTN100'),('R105','12k','U100_ILIM','RTN100'),('R106','8.2k','U100_SHDN','RTN100'),('R107','100k','VIN_RAW','U100_OPTC')]:r(ref,val,a,b,'INPUT')
 c('C101','47n','U100_DVDT','RTN100','INPUT',note='Cmin/T/leakage stillHOLD')
 add('OP100','VOS618A','VOS618A-3X001T','ISOLATED_MAIN_PERMIT',{1:'LED_MAIN',2:'GND_CTRL',3:'U100_SHDN',4:'U100_OPTC'},'INPUT','Package_SO:SSOP-4_4.4x2.6mm_P1.27mm',status='HOLD_CTR_TIMING',note='100..200%at1mA25C; no guaranteed max turnoff for this use')
 r('R108','1.8k','BRANCH_PERMIT','LED_MAIN','INPUT')
 # FLT is isolated diagnostic only: lack of LED is NEVER interpreted as health.
 add('OP102','VOS618A','VOS618A-3X001T','MAIN_FAULT_DIAG',{1:'LED_FLT',2:'U100_FLT_LOCAL',3:'GND_CTRL',4:'MAIN_FAULT_DIAG_N'},'INPUT','Package_SO:SSOP-4_4.4x2.6mm_P1.27mm')
 r('R109','10k','VIN_RAW','LED_FLT','INPUT',size='1206');r('R110','10k','V5','MAIN_FAULT_DIAG_N','INPUT');tp('TP101','MAIN_FAULT_DIAG_N','INPUT','DIAGNOSTIC ONLY; not PG/health. No RTN100 cross')
 add('C100','C','EEUFR1J470','47u_63V',{1:'V24P',2:'PGND'},'INPUT','Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',status='HOLD_EXACT_DIMENSIONS',note='All bulk upstream final branch switch; check exactcase before PCB')
 # LM5069 preferred development route. Q101 remains visibly DNP / unselected.
 add('U101','LM5069','LM5069MM-1/NOPB','LM5069_LATCH',{1:'PASS_D',2:'V24P',3:'U101_UV',4:'U101_OV',5:'PGND',6:'U101_TIMER',7:'U101_PWR',8:'U101_PGD_DIAG',9:'L_FEED',10:'PASS_GATE'},'FRONTEND','Package_SO:MSOP-10_3x3mm_P0.5mm',status='HOLD_LOADED_CUTOFF',note='1.2usmax only150mVstep/no-load/VIN48test; tFAULT12usTYP')
 r('R111','HOLD_CURRENT_SETTING','V24P','PASS_D','FRONTEND',size='2512',note='50mtrial settingNOTselected: minimumcurrentlimit.960A belowR3startup1.649A. Guaranteedbreaker-only Rswindowdisjoint; value/MPN remainsHOLD')
 add('Q101','Q','UNKNOWN_LINEAR_SOA_PASS_FET','HOLD_DNP_PASS_FET',{1:'PASS_GATE',2:'PASS_D',3:'L_FEED'},'FRONTEND',status='HOLD_DNP_UNSELECTED',note='NOT FITTED. No exactpassFET or loaded/hotSOA qualification. Seriespath physicallyOPEN until review')
 r('R112','10k','PASS_GATE','L_FEED','FRONTEND');r('R113','10k','U101_UV','PGND','FRONTEND');r('R114','68k','V24P','U101_OPT_C','FRONTEND')
 add('OP101','VOS618A','VOS618A-3X001T','ISOLATED_BRANCH_PERMIT',{1:'LED_BRANCH',2:'GND_CTRL',3:'U101_UV',4:'U101_OPT_C'},'FRONTEND','Package_SO:SSOP-4_4.4x2.6mm_P1.27mm',status='HOLD_LOADED_CUTOFF')
 r('R115','1.8k','BRANCH_PERMIT','LED_BRANCH','FRONTEND')
 r('R116','100k','V24P','U101_OV','FRONTEND');r('R117','10k','U101_OV','PGND','FRONTEND');r('R118','75k','U101_PWR','PGND','FRONTEND',note='Exploratory PLIMIT value only; actualMOS/powerlimit qualification HOLD')
 c('C110','10n','U101_TIMER','PGND','FRONTEND',note='Timer charges with min/maxcurrent; timer-to-gatelow stilltypical, not totaldelaymax');c('C111','100n','V24P','PGND','FRONTEND',note='Controllerinputbypass UPSTREAM Q101; included in storedenergybudget')
 r('R119','10k','V5','U101_PGD_DIAG','FRONTEND');tp('TP110','U101_PGD_DIAG','FRONTEND','RawPGD diagnostic, unpowered open-drain isNOThealthy')
 # No deliberately fitted capacitor at L_FEED. Controller and auxiliary decoupling moved upstream.
 # Real external rail, from fused raw input, with reverse DC diode.
 add('DA1','D','US1G-E3/61T','BIAS_REVERSE_DIODE',{1:'BUCK_IN',2:'VIN_RAW'},'AUX','Diode_SMD:D_SMA',note='Reusedpart in DCbias path, NOT Boostrectifier recoveryqualification')
 add('UA1','LM5164','LM5164DDAR','BIAS12_BUCK',{1:'PGND',2:'BUCK_IN',3:'BUCK_EN',4:'BUCK_RON',5:'BUCK_FB',6:'BUCK_PG_DIAG',7:'BUCK_BST',8:'BUCK_SW',9:'PGND'},'AUX','Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm',status='CANDIDATE_RAIL_HOLD',note='Real TI12V application circuit, not idealAUX; applicationBOM inconsistency448k/453k not copied blindly')
 for i in [1,2]:c('CAIN'+str(i),'2.2u','BUCK_IN','PGND','AUX','1206','CGA6N3X7R2A225K230AB',note='100V, effectiveC underbias must verify')
 r('RA1','100k','BUCK_IN','BUCK_EN','AUX');r('RA2','10k','BUCK_EN','PGND','AUX');r('RA3','100k','BUCK_RON','PGND','AUX')
 c('CAB','2.2n','BUCK_BST','BUCK_SW','AUX',mpn='GCM155R71H222KA37D')
 add('LA1','L','MSS1246T-683MLB','68u',{1:'BUCK_SW',2:'V12'},'AUX','Inductor_SMD:L_Coilcraft_MSS1246T-XXX',status='CANDIDATE_RAIL_HOLD')
 for i in [1,2]:c('CAOUT'+str(i),'22u','V12','PGND','AUX','1210','TMK325B7226KMHT')
 r('RA4','453k','V12','BUCK_FB','AUX');r('RA5','49.9k','BUCK_FB','PGND','AUX');r('RA6','453k','BUCK_SW','BUCK_RIPPLE','AUX')
 c('CARA','3.3n','BUCK_RIPPLE','V12','AUX');c('CARB','56p','BUCK_RIPPLE','BUCK_FB','AUX');r('RA7','10k','V5','BUCK_PG_DIAG','AUX');tp('TPA1','BUCK_PG_DIAG','AUX','DIAGNOSTIC ONLY; separate supervisorauthorizesrails')
 add('UA2','TPS7A1601','TPS7A1601DGNR','SAFETY5_LDO',{1:'V5',2:'LDO_FB',3:'LDO_PG_DIAG',4:'GND_CTRL',5:'V12',6:None,7:None,8:'V12',9:'GND_CTRL'},'AUX','Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm',status='CANDIDATE_RAIL_HOLD',note='Adjustable1.193Vreference; do notassumeunlistedfixed5VMPN')
 r('RA8','319k','V5','LDO_FB','AUX');r('RA9','100k','LDO_FB','GND_CTRL','AUX');c('CALDOIN','10u','V12','GND_CTRL','AUX','0805');c('CALDOOUT','10u','V5','GND_CTRL','AUX','0805');r('RA10','10k','V5','LDO_PG_DIAG','AUX')
 # Boost power / physical feedback, with genuine external buffer, no external INTVCC drive.
 add('L20','L','MSS1583-154KED','150u_10pct',{1:'L_FEED',2:'SW_HV'},'POWER','Inductor_SMD:L_Coilcraft_MSS1583-XXX',status='HOLD_HOT_FAULT')
 add('Q20','Q','STP9NK50Z','500V_MOS',{1:'GATE_PWR',2:'SW_HV',3:'SRC'},'POWER','Package_TO_SOT_THT:TO-220-3_Vertical',status='RETAIN_EXTERNAL12_CANDIDATE',note='Tab2isDrain, exposedHV; gatebuffer12rail, not7.2RDSguarantee')
 add('D20','D','STPSC4H065D','650V_SiC',{1:'HV_BUS',2:'SW_HV'},'POWER','Package_TO_SOT_THT:TO-220-2_Vertical',status='REPLACE_CANDIDATE_HOLD',note='Pin1K/2A; factorymodelnoBV/avalanche; hot/repetitivePCB qualification HOLD')
 add('RS20','R','WSL2512R0620FEA','62m',{1:'SRC',2:'PGND'},'POWER','Resistor_SMD:R_2512_6332Metric',status='HOLD_PULSE',note='Kelvin sense posfrompad1, negativeviaNT1 atpad2;1Wavg not pulsepermission')
 add('NT1','NT','PCB_NET_TIE','KELVIN_STAR',{1:'PGND',2:'GND_KELVIN'},'POWER','NetTie:NetTie-2_SMD_Pad0.5mm',note='Layout constraint, not arbitrarygroundplaneconnection')
 add('NT2','NT','PCB_NET_TIE','CONTROL_STAR',{1:'PGND',2:'GND_CTRL'},'POWER','NetTie:NetTie-2_SMD_Pad0.5mm')
 add('NT3','NT','PCB_NET_TIE','DRIVER_RETURN_STAR',{1:'PGND',2:'GND_DRV'},'POWER','NetTie:NetTie-2_SMD_Pad0.5mm',note='Wide independentgatedrive return, not Kelvinthintrace')
 add('U20','LT3757A','LT3757AEMSE#PBF','LT3757A',{1:'VC',2:'FB',3:'SS',4:'RT',5:'GND_KELVIN',6:'SENSE',7:'PWM_RAW',8:'INTVCC',9:'PWM_SHDN',10:'V12',11:'GND_KELVIN'},'POWER','Package_SO:MSOP-10-1EP_3x3mm_P0.5mm_EP1.68x1.88mm',note='VIN fromreal12rail upstreambranch; INTVCC internalLDO only, VIN+.3absolute respected structurally')
 add('U201','UCC27511','UCC27511DBVR','12V_GATE_BUFFER',{1:'V12',2:'GATE_ON',3:'GATE_OFF',4:'GND_DRV',5:'DRV_INHIBIT',6:'PWM_RAW'},'POWER','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_RAIL_AND_PULSE',note='PhysicalpinoutDIFFERSfromSPICEorder; independentinputthreshold, outputlowUVLO')
 r('RGON','22','GATE_ON','GATE_PWR',mpn='RC0603FR-0722RL');r('RGOFF','22','GATE_OFF','GATE_PWR',mpn='RC0603FR-0722RL');r('RGS','10k','GATE_PWR','SRC',mpn='RC0603FR-0710KL')
 add('DGNEG','D','SS14-E3/61T','NEGATIVE_GATE_CLAMP',{1:'NEG_DAMP',2:'SRC'},'POWER','Diode_SMD:D_SMA',status='HOLD_MODEL_AND_PULSE')
 r('RNEG','2','NEG_DAMP','GATE_PWR',size='0805',mpn='RC0805FR-072RL',note='Actual0805sizechecked separately; repetitivepulseHOLD')
 r('RF','22','SRC','SENSE',mpn='RC0603FR-0722RL');c('CF','4.7n','SENSE','GND_KELVIN',mpn='GRM1885C1H472JA01D')
 for ref,val,a,b in [('RCOMP','22k','VC','VC_COMP'),('RRT','140k','RT','GND_KELVIN'),('REN1','82.5k','V12','PWM_SHDN'),('REN2','12.4k','PWM_SHDN','GND_KELVIN')]:r(ref,val,a,b)
 c('CCOMP','6.8n','VC_COMP','GND_KELVIN',mpn='GRM1885C1H682JA01D');c('CHF','100p','VC','GND_KELVIN',mpn='GRM1885C2A101JA01D');c('CSS','100n','SS','GND_KELVIN',mpn='GRM188R71H104KA93D')
 c('CINT','10u','INTVCC','GND_KELVIN',size='0805',mpn='GRM21BR71E106KA73L',note='Needmin4.7ueffective7.2Vbias/fullT;HOLD')
 c('CVIN','1u','V12','GND_KELVIN',size='0805',note='Upstreambranch storage, not L_FEED capacitor')
 c('CDRV','4.7u','V12','GND_DRV',size='0805');c('CDRVHF','100n','V12','GND_DRV')
 r('RINH','10k','V12','DRV_INHIBIT');r('RBEN','22k','PWM_PERMIT','QEN_BASE')
 add('QEN','NPN','MMBT3904LT1G','DEFAULT_INHIBIT',{1:'QEN_BASE',2:'GND_DRV',3:'DRV_INHIBIT'},'POWER','Package_TO_SOT_SMD:SOT-23')
 r('RBSD','22k','DRV_INHIBIT','QSD_BASE')
 add('QSD','NPN','MMBT3904LT1G','PWM_SHUTDOWN_CLAMP',{1:'QSD_BASE',2:'GND_KELVIN',3:'PWM_SHDN'},'POWER','Package_TO_SOT_SMD:SOT-23')
 for ref,a,b in [('RFB1','HV_BUS','FB_MID'),('RFB2','FB_MID','FB')]:r(ref,'100k',a,b,size='1206',mpn='TNPW1206100KBEEA')
 r('RFB3','1.91k','FB','GND_KELVIN',mpn='TNPW06031K91BEEA',note='Deliberate manufacturableE96value replacingideal1900.6ohm; nominal169.1393V, recompute fullreference/tolerance')
 r('RSNUB','330','SW_HV','SNUB',size='1206',note='Originalvalue, pulsepowerqualificationHOLD');c('CSNUB','100p_630V_C0G','SNUB','HV_BUS',size='1206',note='ExactMPN/voltagepulseHOLD, never substitute100V')
 for i in [11,12]:add('C'+str(i),'C','B32774D4106K000','10u_450V_10pct',{1:'HV_BUS',2:'PGND'},'POWER','Capacitor_THT:C_Rect_L31.5mm_W15.0mm_P27.50mm_MKS4',status='REPLACE_VOLTAGE_CANDIDATE',note='450V85C,330.3V105Carithmetic;8Arms70C10k,ESR10.9mohm/ESL24nHtyp;not fullT100kguarantee')
 for branch in [1,2]:
  for j in [1,2,3]:r(f'RB{branch}{j}','49.9k','HV_BUS'if j==1 else f'BLEED{branch}_{j-1}',f'BLEED{branch}_{j}'if j<3 else'PGND',size='2512',mpn='CRCW251249K9FKEG',note='Independent149.7kstring; ownreturn. Upgradefrom1206 for single-resistor-short power;1W70C/500Vdatasheetseries, exactorder/stockverification remains')
 # OVP independent divider and internalref, not normalfeedback/reference.
 add('U430','TPS3700','TPS3700DDCR','INDEPENDENT_OVP',{1:None,2:'GND_CTRL',3:'GND_CTRL',4:'OVP_SENSE',5:'V5',6:'FAULT_RAW_N'},'MONITORS','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_MAX_DELAY',note='400mVinternalref, outputB pullsLOW onOV; 18/29usTYP notmax')
 for j in [1,2,3,4]:r('ROV'+str(j),'100k','HV_BUS'if j==1 else'OVP'+str(j-1),'OVP_SENSE'if j==4 else'OVP'+str(j),'MONITORS','1206','RC1206FR-07100KL')
 r('ROV5','430','OVP_SENSE','OVP_BOT','MONITORS',mpn='RC0603FR-07430RL');r('ROV6','430','OVP_BOT','GND_CTRL','MONITORS',mpn='RC0603FR-07430RL')
 # Two independent low-asserting residual channels. Their validity is intentionally blocked.
 for suffix,ref in [('A','U431'),('B','U432')]:
  add(ref,'TPS3700','TPS3700DDCR','RESIDUAL_'+suffix,{1:'RES_'+suffix+'_N',2:'GND_CTRL',3:'RES_'+suffix+'_SENSE',4:'GND_CTRL',5:'V5',6:None},'MONITORS','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_DIVIDER_GROUND_DIAGNOSTICS',note='LOWassertedonlybelow56.57V; unpoweredoutputfloating isNOTlow proof; upperopen/commonreturn gaps remain')
  r('RR'+suffix+'1','330k','HV_BUS','RES_'+suffix+'_MID','MONITORS','1206');r('RR'+suffix+'2','330k','RES_'+suffix+'_MID','RES_'+suffix+'_SENSE','MONITORS','1206');r('RR'+suffix+'3','4.7k','RES_'+suffix+'_SENSE','GND_CTRL','MONITORS');r('RR'+suffix+'4','10k','V5','RES_'+suffix+'_N','MONITORS')
 add('U433','TPS3700','TPS3700DDCR','BRANCH_OFF_WITNESS',{1:'BRANCH_OFF_N',2:'GND_CTRL',3:'BRANCH_SENSE',4:'GND_CTRL',5:'V5',6:None},'MONITORS','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_GROUND_OPEN_COVERAGE')
 r('RBRO1','30.1k','L_FEED','BRANCH_SENSE','MONITORS');r('RBRO2','10k','BRANCH_SENSE','GND_CTRL','MONITORS');r('RBRO3','10k','V5','BRANCH_OFF_N','MONITORS')
 for suffix,ref in [('Q','U440'),('L','U441')]:
  add(ref,'TPS3700','TPS3700DDCR','THERMAL_WINDOW_'+suffix,{1:'FAULT_RAW_N',2:'GND_CTRL',3:'TEMP_'+suffix,4:'TEMP_'+suffix+'_HI',5:'V5',6:'FAULT_RAW_N'},'MONITORS','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_THERMAL_COUPLING',note='Sensoropen orshort assertsfault; nominal trip~86C leaves100Cengineeringlimit, maximumhotspotlagUNKNOWN')
  r('RNT'+suffix,'12k','V5','TEMP_'+suffix,'MONITORS');r('RNTH'+suffix,'90.9k','TEMP_'+suffix,'TEMP_'+suffix+'_HI','MONITORS');r('RNTL'+suffix,'10k','TEMP_'+suffix+'_HI','GND_CTRL','MONITORS')
  add('RT'+suffix,'R','NTCLE100E3103JB0','NTC10k_B3977',{1:'TEMP_'+suffix,2:'GND_CTRL'},'MONITORS',status='HOLD_OFFBOARD_SENSOR_ASSEMBLY',note='Off-boardthermalattachment andcable/connectorMPNpending; do not useas on-boardambient proxy')
 # Supervisors see rail voltage while powered by V5; no unpoweredexternalOD health assumption.
 for ref,mpn,net in [('U500','TPS3808G50DBVR','V5'),('U501','TPS3808G01DBVR','BIAS12_SENSE'),('U502','TPS3808G01DBVR','RAW24_SENSE')]:
  add(ref,'TPS3808',mpn,'POWER_VALID_SUPERVISOR',{1:'FAULT_RAW_N',2:'GND_CTRL',3:'V5',4:ref+'_CT',5:net,6:'V5'},'SAFETY','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_FULL_SEQUENCE')
  c(ref+'_CT','10n',ref+'_CT','GND_CTRL','SAFETY')
 r('RPG1','261k','V12','BIAS12_SENSE','SAFETY');r('RPG2','10k','BIAS12_SENSE','GND_CTRL','SAFETY');r('RPG3','475k','VIN_RAW','RAW24_SENSE','SAFETY');r('RPG4','10k','RAW24_SENSE','GND_CTRL','SAFETY')
 r('RFAULT','10k','V5','FAULT_RAW_N','SAFETY')
 add('U510','HCS14','SN74HCS14DR','SCHMITT_EVENTS',{1:'START_N',2:'START_CLOCK',3:'RESET_N',4:'RESET_CLOCK',5:'RES_A_N',6:'RES_A_LOW',7:'GND_CTRL',8:'RES_B_LOW',9:'RES_B_N',10:'RESET_DISALLOW',11:'RESET_QUAL',12:'BRANCH_OFF_LOW',13:'BRANCH_OFF_N',14:'V5'},'SAFETY','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
 add('U511','HCS08','SN74HCS08DR','RESIDUAL_QUAL',{1:'RES_A_LOW',2:'RES_B_LOW',3:'RES_BOTH_LOW',4:'RES_BOTH_LOW',5:'BRANCH_OFF_LOW',6:'RES_OFF',7:'GND_CTRL',8:'RESET_A',9:'RES_OFF',10:'HOLD_RESIDUAL_VALID',11:'RESET_QUAL_RAW',12:'RESET_A',13:'START_N',14:'V5'},'SAFETY','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
 add('U512','HCS08','SN74HCS08DR','TOKEN_CLEAR',{1:'FAULT_FREE',2:'STOP_OK',3:'TOKEN_CLR_N',4:'RESET_QUAL_RAW',5:'HOLD_FULL_SAFETY_VALID',6:'RESET_QUAL',7:'GND_CTRL',8:None,9:'GND_CTRL',10:'GND_CTRL',11:None,12:'GND_CTRL',13:'GND_CTRL',14:'V5'},'SAFETY','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
 add('U513','HCS08','SN74HCS08DR','DUAL_PERMIT',{1:'RUN_TOKEN',2:'FAULT_RAW_N',3:'RUN_INPUT_GOOD',4:'RUN_INPUT_GOOD',5:'FAULT_FREE',6:'RUN_CLEAN',7:'GND_CTRL',8:'PWM_PERMIT',9:'RUN_CLEAN',10:'HOLD_PRECHARGE_OK',11:'BRANCH_PERMIT',12:'RUN_CLEAN',13:'HOLD_INPUT_CUT_VALID',14:'V5'},'SAFETY','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
 add('U514','HCS74','SN74HCS74DR','FAULT_AND_RUN_LATCH',{1:'V5',2:'RESET_DISALLOW',3:'RESET_CLOCK',4:'FAULT_RAW_N',5:'FAULT_LATCH',6:'FAULT_FREE',7:'GND_CTRL',8:None,9:'RUN_TOKEN',10:'V5',11:'START_CLOCK',12:'HOLD_FULL_SAFETY_VALID',13:'TOKEN_CLR_N',14:'V5'},'SAFETY','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',status='HOLD_EVENT_FMEA',note='FAULT asynchronousPREdominatesclock; CLR1neverasserted. Resetclockdataqual, never gateclockwithhealth. RUN requiresfreshSTARTafterclear')
 for name in ['START','RESET']:
  add('SW_'+name,'SW','UNKNOWN_PANEL_NO_SWITCH',name,{1:name+'_N',2:'GND_CTRL'},'INTERFACES',status='HOLD_PANEL_MPN')
  r('RSW_'+name,'10k','V5',name+'_N','INTERFACES');c('CSW_'+name,'100n',name+'_N','GND_CTRL','INTERFACES',note='SchmittRC debounce only, not completefresh-request/watchdogproof')
 add('SW_STOP','SW','UNKNOWN_PANEL_NC_STOP','STOP_NC',{1:'V5',2:'STOP_OK'},'INTERFACES',status='HOLD_PANEL_MPN');r('RSTOP','10k','STOP_OK','GND_CTRL','INTERFACES')
 # Missing functions are explicit pulled-low HOLD inputs. No abstract physical blocks.
 for i,net in enumerate(['HOLD_FULL_SAFETY_VALID','HOLD_RESIDUAL_VALID','HOLD_PRECHARGE_OK','HOLD_INPUT_CUT_VALID'],1):
  r('RHOLD'+str(i),'10k',net,'GND_CTRL','INTERFACES',note='MustremainLOW; nojumperorautorununtilmissingphysicalfunctionreviewed');tp('TPH'+str(i),net,'INTERFACES','HOLD ONLY; no power-up permission. Missingdiagnostic/function not implemented')
 add('JHV','PORT','UNKNOWN_TOUCH_PROTECTED_HV_PORT','HOLD_ENCLOSED_HV_LOAD',{1:'HV_BUS',2:'PGND'},'INTERFACES',status='HOLD_NO_EXPOSED_HV_CONNECTOR',note='No footprint. Cover/ratedconnector/loaddischargequalification absent. COUT shortenergy remainsindependentdanger')
 for i,net in enumerate(['FAULT_LATCH','RUN_TOKEN','BRANCH_PERMIT','PWM_PERMIT','V12','V5'],1):tp('TP'+str(500+i),net)
 # Decoupling is real and belongs in the storage budget. Never add it to L_FEED.
 # Independent safety5 overvoltage response powered from V12, not the failing logicrail.
 # It can withdraw commands even if HCS logic is damaged. NOT a guaranteed V5clamp.
 add('U520','TPS3700','TPS3700DDCR','V5_OV_HARD_SHUTDOWN',{1:None,2:'PGND',3:'PGND',4:'V5_OV_SENSE',5:'V12',6:'V5_OV_N'},'SAFETY','Package_TO_SOT_SMD:SOT-23-6',status='HOLD_MAX_DELAY_AND_SINGLEFAULT',note='12Vdomain, independentof5Vlogic; typdelayNOTa guarantee HCSpinsremainbelow6V')
 r('R5OV1','127k','V5','V5_OV_SENSE','SAFETY');r('R5OV2','10k','V5_OV_SENSE','PGND','SAFETY')
 r('R5OV3','33k','V5_OV_N','Q5P_BASE','SAFETY');r('R5OV4','100k','V12','Q5P_BASE','SAFETY')
 typ('PNP',[(1,'B','input'),(2,'E','passive'),(3,'C','passive')])
 add('Q5P','PNP','MMBT5401LT1G','V5_FAULT_LEVEL_SHIFT',{1:'Q5P_BASE',2:'V12',3:'V5_FAULT_HIGH'},'SAFETY','Package_TO_SOT_SMD:SOT-23',status='CANDIDATE_STATIC_ONLY',note='ManufacturerSOT23 1B2E3C, cachedprimarysource; not switchpinorder')
 r('R5OV5','100k','V5_FAULT_HIGH','PGND','SAFETY')
 for suffix,target in [('A','PWM_SHDN'),('B','U101_UV')]:
  r('R5B'+suffix,'22k','V5_FAULT_HIGH','Q5'+suffix+'_BASE','SAFETY');r('R5PD'+suffix,'100k','Q5'+suffix+'_BASE','PGND','SAFETY')
  add('Q5'+suffix,'NPN','MMBT3904LT1G','INDEPENDENT_DISABLE_'+suffix,{1:'Q5'+suffix+'_BASE',2:'PGND',3:target},'SAFETY','Package_TO_SOT_SMD:SOT-23',status='CANDIDATE_STATIC_ONLY')
 add('OP520','VOS618A','VOS618A-3X001T','V5_OV_MAIN_CUT',{1:'V5_OV_LED',2:'PGND',3:'RTN100',4:'U100_SHDN'},'SAFETY','Package_SO:SSOP-4_4.4x2.6mm_P1.27mm',status='HOLD_HOT_CTR_AND_DELAY',note='Detector/LED poweredV12, sinkSHDNrelativeRTN100 via opticalbarrier, never tieRTN100toPGND')
 r('R5LED','8.2k','V5_FAULT_HIGH','V5_OV_LED','SAFETY');c('C5OV','100n','V12','PGND','SAFETY')
 for p in list(PARTS):
  if p['kind']in ['TPS3700','TPS3808','HCS74','HCS14','HCS08'] and p['ref']!='U520':c('CD_'+p['ref'],'100n','V5','GND_CTRL',p['group'])
 r('RQENOFF','100k','QEN_BASE','GND_DRV',note='Defaultbasepulldown when5Vlogicunpowered')
 for net,ref in [('VIN_CONNECTOR','PF1'),('PGND','PF2'),('GND_CTRL','PF3'),('GND_KELVIN','PF4'),('GND_DRV','PF5'),('V12','PF6'),('VIN_RAW','PF7'),('BUCK_IN','PF8')]:
  add(ref,'FLAG','ERC_DECLARATION','PWR_FLAG',{1:net},'INTERFACES',note='Externalinput / actualnettie / buckinductor source declaration forERC, not validity/safetyproof')
 return PARTS
if __name__=='__main__':
 generate();dump(HERE/'EVT01/design_source.json',dict(types=TYPES,parts=PARTS,scope='Native schematic source only; Q101DNP/missingphysicaldiagnostics block operation/manufacture'))
 rows=[dict(ref=p['ref'],MPN=p['mpn'],pin=n,pin_name=TYPES[p['kind']][n][0],pin_type=TYPES[p['kind']][n][1],net=net or'NC',group=p['group'],footprint=p['footprint'],status=p['status'])for p in PARTS for n,net in p['pins'].items()]
 with(HERE/'EVT01/pin_connections.csv').open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps(dict(parts=len(PARTS),pins=len(rows),groups=sorted({p['group']for p in PARTS}))))
