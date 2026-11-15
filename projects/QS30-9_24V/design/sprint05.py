"""Isolated S05 calculations/review tables. No legacy generator import or EDA output.
Run: tools/review_venv/Scripts/python.exe projects/QS30-9_24V/design/sprint05.py
"""
from pathlib import Path
import csv, hashlib, itertools, json, math
ROOT=Path(__file__).resolve().parents[1]
def destination(relative):
 p=(ROOT/relative).resolve()
 if not p.is_relative_to(ROOT) or p==ROOT: raise ValueError('Write outside 24V project')
 p.parent.mkdir(parents=True,exist_ok=True)
 return p
def dump(relative,obj): destination(relative).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def table(relative,rows):
 with destination(relative).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run():
 c=json.loads((ROOT/'config/sprint05.json').read_text(encoding='utf8'))
 hv=c['HV_candidate'];load=c['loads'];eta=c['efficiency_allocations']
 rails=[]; cases=[]; points=[]
 # Feedback is reselected to 2x1M / (29.4k+453); OVP/ADC remain budget placeholders.
 dividers=[2000000+29853,1500000+19100,1500000+14300]
 def hv_power(v,i,worst=False):
  bleedt=1-load['bleed_resistor_tolerance'] if worst else 1
  return 9*i*v+4*v*v/(200000*bleedt)+sum(v*v/(r*(.99 if worst else 1)) for r in dividers)+v*load['HV_extra_leakage_A']
 for v,i,worst in itertools.product([164.9,170,175.1],[0,.0015,.00225,.003],[False,True]):
  p=hv_power(v,i,worst)
  cases.append(dict(Vout_V=v,tube_each_A=i,resistor_worst=worst,HV_W=p,HV_A=p/v))
  for vin,L,f in itertools.product([20.5,24,26.4],[hv['L_H']*(1-hv['L_tolerance'])*(1-hv['L_extra_drop']),hv['L_H'],hv['L_H']*(1+hv['L_tolerance'])],[110000*.85,110000,110000*1.15]):
   io=p/v;d=math.sqrt(2*L*f*io*(v-vin))/vin;d2=vin*d/(v-vin);ip=vin*d/L/f
   points.append(dict(Vout_V=v,Vin_V=vin,L_H=L,f_Hz=f,HV_W=p,tube_A=i,worst=worst,D=d,D2=d2,idle=1-d-d2,Ipk_A=ip,ILrms_A=ip*math.sqrt((d+d2)/3),IQrms_A=ip*math.sqrt(d/3),IDrms_A=ip*math.sqrt(d2/3),Iin_A=ip*(d+d2)/2,energy_error_W=vin*ip*(d+d2)/2-p))
 pmax=max(x['HV_W'] for x in cases);pnom=hv_power(170,.00225)
 # All AUX consumers, including gate energy, counted exactly once outside HV stage efficiency.
 iaux=sum(load[k] for k in ['DRV_HV5622_alloc_A','DRV_level_shift_alloc_A','controller_bias_alloc_A','protection_PG_bias_alloc_A','other_AUX_alloc_A'])+load['controller_gate_charge_alloc_C']*110000*1.15
 paux=12.6*iaux;p3=3.465*.8;p5=p3/eta['3V3_buck_min']
 padapter=pmax/eta['HV_power_stage_min']+paux/eta['AUX_buck_min']+p5/eta['5V_buck_min']+eta['front_end_loss_W']
 for name,v,i,p,scope,evidence in [
  ('HV_BUS',175.1,pmax/175.1,pmax,'all HV loads; driver drain conduction included','calculated load envelope; tubes unmeasured'),
  ('DRV12',12.6,.055,12.6*.055,'subset of AUX12; do not add twice','HV5622 45mA datasheet test bound plus level shifts 10mA allocation'),
  ('AUX12',12.6,iaux,paux,'includes DRV12/controller/gate/protection/other','allocation at upper voltage, not measured current'),
  ('3V3',3.465,.8,p3,'MCU/logic/peripherals, external power mode','800mA inherited allocation at upper voltage; measurement pending'),
  ('5V_SYS',5,p5/5,p5,'upstream of 3V3, no duplicate addition','eta3V3=0.80 allocation'),
  ('VIN24',21.6,padapter/21.6,padapter,'total at connector, includes all conversion budgets','efficiency floors are requirements, not verified'),
  ('USB_VBUS_configured',4.75,(3.465*.45/.8+.03)/4.75,3.465*.45/.8+.03,'USB-only scenario, excludes AUX/HV','500mA configured USB; pre-enumeration unresolved')]:
  rails.append(dict(rail=name,voltage_V=v,current_A=i,power_W=p,scope=scope,evidence=evidence))
 rs=hv['RCS_ohm'];rt=hv['RCS_tolerance'];lmin=hv['L_H']*.9*.9
 limitmin=(.9-hv['noise_budget_V'])/(rs*(1+rt));limitmax=(1.1+hv['noise_budget_V'])/(rs*(1-rt))
 delay=hv['CS_filter_R_ohm']*hv['CS_filter_C_F']+hv['CS_comparator_delay_max_s']+hv['gate_turnoff_budget_s']
 overshoot=26.4/lmin*delay
 caps=hv['COUT_F']+hv['module_C_F']
 capsmax=hv['COUT_F']*1.05+hv['module_C_F']*1.10
 calc={
  'status':'ANALYTIC_SCREEN_NOT_COMPONENT_OR_SYSTEM_PASS','config_sha256':hashlib.sha256((ROOT/'config/sprint05.json').read_bytes()).hexdigest(),
  'HV_nom_typ_W_with_1mA_reserve':pnom,'HV_max_W':pmax,'AUX12_A_alloc':iaux,'adapter_W_alloc':padapter,'input_max_A_at21_6':padapter/21.6,'adapter_W_at_nominal_LV_rails':pmax/.75+12*iaux/.8+(3.3*.8/.8)/.8+.35,
  'DCM_screen':{'points':len(points),'max_D':max(x['D'] for x in points),'min_idle':min(x['idle'] for x in points),'max_Ipk_A':max(x['Ipk_A'] for x in points),'max_ILrms_A':max(x['ILrms_A'] for x in points),'max_IDrms_A':max(x['IDrms_A'] for x in points),'max_energy_error_W':max(abs(x['energy_error_W']) for x in points),'startup_scope':'Excluded: near-Vin startup and output-short are not covered by steady 165-175V DCM equations'},
  'CS':{'ideal_limit_min_A':limitmin,'ideal_limit_max_with_50mV_error_A':limitmax,'filter_tau_s':22e-9,'total_delay_alloc_s':delay,'delay_current_increment_A':overshoot,'screen_peak_max_A':limitmax+overshoot,'legacy_0_15ohm_1_1V_A':1.1/.15,'Isat10pct25C_A':1.58,'qualification':'FAIL_PENDING_TEMPERATURE_SATURATION_NOISE_GATE_MODEL_AND_CCM_RAMP'},
  'C10':{'legacy_halfCV2_J_at170':.5*1e-8*170**2,'legacy_halfCV2f_W_at110k':.5*1e-8*170**2*110000,'legacy_CV2f_W_at110k':1e-8*170**2*110000,'note':'Energy scale, not measured resistor dissipation; waveform/topology determines recovery and loss','snubber_CV2f_W_at180':1e-10*180**2*126500},
  'storage':{'Ctotal_nom_F':caps,'Ctotal_max_screen_F':capsmax,'E170_J':.5*caps*170**2,'E195_J_max_C':.5*capsmax*195**2,'charge0to170_J':.5*caps*170**2,'charge_Vin_to170_J':.5*caps*(170**2-26.4**2),'bleed_all_to60_s':50000*caps*math.log(170/60),'bleed_one_open_to60_s':(200000*1.01/3)*capsmax*math.log(195/60),'bleed_main_only_one200k_to60_s':200000*1.01*20e-6*1.05*math.log(195/60),'module_100n_one200k_to60_s':200000*1.01*100e-9*1.1*math.log(195/60),'note':'Cmain +5%, module C +10%, remaining bleed R +1%; no temperature drift credit. Divider leakage not credited; a disconnected module with its only bleed open has no guaranteed decay'},
  'feedback':{'upper_ohm':2000000,'lower_ohm':29853,'nominal_V':2.5*(1+2000000/29853),'worst_V':[2.475*(1+2000000*.999/(29853*1.001)),2.525*(1+2000000*1.001/(29853*.999))],'note':'0.1% feedback resistors; includes reference initial error only, bias/drift pending'},
  'eFuse':{'main_RILIM_ohm':12000,'main_ILIM_typ_A':1,'HV_RILIM_ohm':20000,'HV_ILIM_typ_A':.6,'UVLO_nom_V':1.19*(1+160000/10000),'UVLO_interval_V':[1.175*(1+160000*.99/(10000*1.01)),1.225*(1+160000*1.01/(10000*.99))],'OVLO_nom_V':1.19*(1+240000/10000),'OVLO_interval_V':[1.17*(1+240000*.99/(10000*1.01)),1.225*(1+240000*1.01/(10000*.99))],'C_dVdt_F':47e-9,'ramp26_4_s_typ':26.4*47e-9/(24.6*4.7e-6),'note':'Independent dividers, both to RTN. No vendor dynamic simulation; IO-limit precision at .6A must be qualified'},
  'buck_ripple_screen':{'AUX12_L_H':100e-6,'5V_L_H':33e-6,'AUX12_deltaI_A_at26_4':12*(1-12/26.4)/(100e-6*400000),'5V_deltaI_A_at26_4':5*(1-5/26.4)/(33e-6*400000),'note':'CCM triangular approximation, not PFM light-load ripple or loop qualification'},
  'qualification_gate_24V_07':'NOT_PASSED_NO_ENTRY_TO_24V_08'}
 calc['eFuse'].update(HV_UVLO_nom_V=1.19*16,HV_UVLO_max_V=1.225*(1+150000*1.01/(10000*.99)),input_fuse_path_drop_alloc_V=.15)
 dump('docs/sprint05/calculations.json',calc);table('docs/sprint05/POWER_RAILS.csv',rails);table('docs/sprint05/HV_LOAD_CASES.csv',cases);table('docs/sprint05/DCM_CORNERS.csv',points)
 old=list(csv.DictReader((ROOT/'baseline_snapshot/legacy12_netlist.csv').open(encoding='utf-8-sig')))
 refs={}
 for row in old: refs.setdefault(row['ref'],[]).append(row)
 replacements={
 'C1':('REPLACE','EEUFR1J470','47u/63V input bulk; real radial footprint and ripple pending'),
 'C2':('REPLACE','GRM188R72A104KA35D','100n/100V; raw-input bypass'),
 'F1':('RESELECT','0451001.MRL','1A/125V fast fuse candidate; I2t/TVS/adapter fault clearing pending'),
 'D1':('REMOVE_REARCHITECT','TPS26601RHFR','reverse polarity handled by integrated back-to-back FETs; not a shorted diode substitution'),
 'Q4':('REMOVE_REARCHITECT','TPS26601RHFR','U101 separately disconnects HV input; no pull-gate-to-ground circuit on 24V'),
 'Q5':('REMOVE_REARCHITECT','none','replace with default-off SHDN hardware permit'),
 'Q2':('REPLACE','TPS22810DBVR','AUX12 to DRV12 load switch; shutdown backfeed qualification pending'),
 'Q3':('REMOVE_REARCHITECT','none','old PFET gate pull-down removed'),
 'U5':('REPLACE','LMR51610XDBVR','24P to 5V; never leave TPS54202 VIN on 24V envelope'),
 'U1':('REPLACE','TPS62162DSGR','5V_SYS to 3V3; real WSON8 pin map'),
 'U20':('REPLACE','UCC28C43DR','AUX12 bias only, source-Kelvin GND; oscillator and CS rebuilt'),
 'Q20':('RESELECT','STP9NK50Z','500V TO220 1G 2D/tab 3S; no old footprint assumed'),
 'D20':('RESELECT','US1G-E3/61T','400V SMA, vendor recovery model pending'),
 'L20':('REPLACE','MSS1260-154KLD','150uH +/-10%; not old 220u/5A placeholder'),
 'C10':('REMOVE_IN_CANDIDATE','DNP','remove 10n direct SW-HV capacitor; separate optional RC 100p/330ohm across Q20 D-S'),
 'C11':('REPLACE_CANDIDATE','ECQE2106JF','10u/250V film, large THT; ripple/dVdt/thermal and full primary dimensional table pending'),
 'C12':('REPLACE_CANDIDATE','ECQE2106JF','second 10u/250V film; summed storage explicit'),
 'R36':('REPLACE_CONNECTION','RC0603FR-07100RL','100ohm from shunt Kelvin+ to CS; no SW connection'),
 'R34':('REPLACE_SPLIT','TNPW12061M00BEEA','two 1M 0.1% physical resistors'),
 'R35':('REPLACE_SPLIT','TNPW060329K4BEEA + TNPW0603453RBEEA','29.4k+453ohm 0.1%; nominal 169.986V'),
 'R32':('REPLACE','RC0603FR-0715K4L','RT=15.4k to controller VREF, no external CT injection yet'),
 'C9':('REPLACE','GRM1885C1H102JA01D','CT=1n C0G; 110k TI example; local CT qualification required')}
 migration=[]
 for ref,rows in sorted(refs.items()):
  nets=sorted({r['net'] for r in rows});action='RETAIN_REVIEW';mpn=rows[0]['mpn'];reason='Unchanged function candidate only; pin/footprint/interface and power-off review still required'
  if ref in replacements: action,mpn,reason=replacements[ref]
  elif ref.startswith('R_AN'): action='RETAIN_VALUE_RESELECT_MPN';reason='Each physical 10k resistor 0.09W at3mA; at175.1V and shorted tube branch worst requires fault thermal review'
  elif ref.startswith('R_MOD') or ref=='R33': action='RETAIN_VALUE_FAULT_REDESIGN';reason='200k branches retained in budget only; module single-open and isolated-ground fault not passed'
  elif ref.startswith('C_MOD') and 'DRV_VDD' in nets: reason='Keep at regulated DRV12 only; replace16V capacitor with25V candidate after footprint/DC-bias check'
  elif ref.startswith('U_LS') or ref.startswith('U_DS') or ref in ['U_L','U_C','U_R']: reason='Remain DRV12/3V3; six CD40109 plus three HV5622, no EXT24 connection; sequencing/backfeed pending'
  elif ref.startswith('J_'): reason='Audit every pin; HV/DRV12/3V3/GND interfaces unchanged by default, no24V exported; ratings/keying/ground-loss unresolved'
  elif any(n.startswith(('EXT12','HV_EN_G')) for n in nets): action='REDESIGN_DOMAIN';reason='Review each legacy EXT12 pin: AUX12 bias, raw24 sensing, switched24, or deleted; no net-wide substitution'
  elif rows[0]['sheet'] in ['MB_OVP','MB_LOGIC'] or ref in ['R37','C13']: action='REDESIGN_PROTECTION_CONTROL';reason='Inherited FAIL; hardware reset permit/OVP/OC latch and power loss require S06 redesign'
  migration.append(dict(ref=ref,old_mpn=rows[0]['mpn'],sheet=rows[0]['sheet'],old_pin_count=len(rows),old_pin_nets=';'.join(r['pin']+':'+r['net'] for r in rows),action=action,candidate_mpn=mpn,rationale=reason,status='NOT_CONNECTED_NOT_APPROVED'))
 table('docs/sprint05/DEVICE_MIGRATION.csv',migration)
 dump('docs/sprint05/coverage.json',{'baseline_rows':len(old),'baseline_unique_refs':len(refs),'migration_rows':len(migration),'all_refs_covered':set(refs)=={r['ref'] for r in migration},'blanket_EXT12_rename':False,'native_24V_schematic':False})
 assert max(abs(x['energy_error_W']) for x in points)<1e-10
 assert all(x['idle']>0 for x in points)
 assert len(migration)==len(refs)
 try: destination('../outside.txt')
 except ValueError: pass
 else: raise AssertionError('write boundary failed')
 print(json.dumps({'rails':rails,'key_calculations':calc,'migration_refs':len(migration)},ensure_ascii=False,indent=2))
if __name__=='__main__': run()
