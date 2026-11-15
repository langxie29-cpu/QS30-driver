"""S06 full-error and power/PG analysis; all outputs isolated from S05 evidence."""
from pathlib import Path
import csv,hashlib,itertools,json,math
ROOT=Path(__file__).resolve().parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def table(p,rows):
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 c=json.loads((ROOT/'config/sprint06.json').read_text(encoding='utf8'));s=json.loads((ROOT/'config/sprint05.json').read_text(encoding='utf8'));out=ROOT/'docs/sprint06';f=c['feedback']
 tol=f['initial_tolerance']+f['TCR_abs_ppm_K']*1e-6*f['max_temperature_delta_K'];fbrows=[]
 for case,ru,rl in [('S05_2Meg',2000000,29853),('S06_200k',f['upper_each_ohm']*f['upper_count'],sum(f['lower_series_ohm']))]:
  for ref,tu,tl,bias in itertools.product(f['VFB_total_V'],[-tol,tol],[-tol,tol],f['input_bias_screen_A']):
   vu=ru*(1+tu);vl=rl*(1+tl);v=ref*(1+vu/vl)-bias*vu
   fbrows.append({'candidate':case,'VFB_V':ref,'upper_error_fraction':tu,'lower_error_fraction':tl,'bias_source_A':bias,'Vout_V':v,'within_mean_requirement':164.9<=v<=175.1})
 table(out/'FEEDBACK_CORNERS.csv',fbrows)
 fb={name:{'min_V':min(r['Vout_V'] for r in fbrows if r['candidate']==name),'max_V':max(r['Vout_V'] for r in fbrows if r['candidate']==name),'pass_this_error_budget':all(r['within_mean_requirement'] for r in fbrows if r['candidate']==name)} for name in ['S05_2Meg','S06_200k']}
 ru=f['upper_each_ohm']*f['upper_count'];rl=sum(f['lower_series_ohm']);v=175.1
 pHV=9*.003*v+4*v*v/(200000*.99)+sum(v*v/(r*.99) for r in [ru+rl,1519100,1514300])+v*.001
 iaux=.045+.010+.005+.020+.010+c['driver']['additional_bias_alloc_A']+c['driver']['Qg_alloc_C']*126500
 paux=12.6*iaux;p3=3.465*.8;p5=p3/.8;pin=pHV/.75+paux/.8+p5/.8+.35
 rails=[{'rail':n,'V_V':vv,'I_A':ii,'P_W':pp,'scope':note} for n,vv,ii,pp,note in [
  ('HV_BUS',v,pHV/v,pHV,'31mA-class load; changed feedback consumption included'),('DRV12',12.6,.055,.693,'subset of AUX12'),('AUX12',12.6,iaux,paux,'includes gate energy once and new driver bias1mA'),('3V3',3.465,.8,p3,'external24V allocation'),('5V_SYS',5,p5/5,p5,'upstream of3V3; do not add twice'),('VIN24',21.6,pin/21.6,pin,'total with efficiency allocations; not measured')]]
 table(out/'POWER_RAILS.csv',rails)
 # Unchanged mode envelope, changed P_HV; not a complete switching/thermal model.
 peaks=[]
 for vin,L,fr in itertools.product([20.5,24,26.4],[150e-6*.9*.9,150e-6,150e-6*1.1],[93500,110000,126500]):
  io=pHV/v;d=math.sqrt(2*L*fr*io*(v-vin))/vin;d2=vin*d/(v-vin);ip=vin*d/L/fr
  peaks.append({'Vin_V':vin,'L_H':L,'frequency_Hz':fr,'Ipk_A':ip,'Irms_A':ip*math.sqrt((d+d2)/3),'idle':1-d-d2})
 table(out/'HV_MAXLOAD_CORNERS.csv',peaks)
 rs=.82;lo=(.9-.05)/(rs*1.01);hi=(1.1+.05)/(rs*.99)
 Lmin=150e-6*.9*.9;talloc=22e-9+70e-9+c['driver']['turnoff_screen_budget_s'];ipeak=hi+26.4/Lmin*talloc
 pg=[];pt=c['PG']['resistor_tolerance']+c['PG']['resistor_TCR_ppm_K']*1e-6*c['PG']['resistor_temperature_delta_K']
 for window in c['PG']['windows']:
  for which in ['UV','OV']:
   rt=window[which+'_upper_ohm'];rb=10000
   for edge,refs in [('rising',c['PG']['reference_rising_V']),('falling',c['PG']['reference_falling_V'])]:
    vals=[]
    for ref,tr,br,ib in itertools.product(refs,[-pt,pt],[-pt,pt],[-25e-9,25e-9]):
     ru1=rt*(1+tr);rl1=rb*(1+br);vals.append(ref*(1+ru1/rl1)+ib*ru1)
    pg.append({'rail':window['rail'],'monitor':which,'sense_edge':edge,'min_rail_V':min(vals),'max_rail_V':max(vals),'scope':'initial0.1% plus25ppm*35K each resistor, full-temp threshold and +/-25nA bias reserve'})
 table(out/'PG_THRESHOLDS.csv',pg)
 sh=c['SHDN_interface'];R1=sh['series_ohm'];R2=sh['pulldown_ohm'];rt=sh['resistor_tolerance']
 off=sh['partial_logic_V_max_screen']*(R2*(1+rt))/(R1*(1-rt)+R2*(1+rt))+sh['SHDN_internal_pullup_A_alloc']/(1/(R1*(1+rt))+1/(R2*(1+rt)))
 on=sh['logic_VOH_min_V_alloc']*(R2*(1-rt))/(R1*(1+rt)+R2*(1-rt))
 floatoff=(sh['SHDN_internal_pullup_A_alloc']+sh['logic_unpowered_leak_A_alloc'])*R2*(1+rt)
 au=c['aux_buck'];at=au['resistor_tolerance']+au['resistor_TCR_ppm_K']*1e-6*au['resistor_delta_K_screen'];aru=sum(au['feedback_upper_series_ohm']);arl=au['feedback_lower_ohm']
 aux_range=[au['reference_V'][0]*(1+aru*(1-at)/(arl*(1+at))),au['reference_V'][1]*(1+aru*(1+at)/(arl*(1-at)))]
 result={'date':'2026-11-15','status':'BOUNDED_ANALYSIS_NOT_SYSTEM_PASS','config_sha256':hashlib.sha256((ROOT/'config/sprint06.json').read_bytes()).hexdigest(),'feedback':fb,'HV_W':pHV,'adapter_W':pin,'input_A_at21_6':pin/21.6,'AUX12_A':iaux,'normal_peak_max_A':max(p['Ipk_A'] for p in peaks),'normal_rms_max_A':max(p['Irms_A'] for p in peaks),'min_idle':min(p['idle'] for p in peaks),'CS':{'min_limit_A':lo,'delay_alloc_s':talloc,'max_peak_A':ipeak,'Isat10pct25C_A':3.1,'25C_headroom_fraction':1-ipeak/3.1,'required_hot_Isat_for20pct_headroom_A':ipeak/.8,'qualification':'hot L(I), real nonlinear gate current and transients remain pending'},'aux_bias_candidate':{'nominal_V':.8*(1+aru/arl),'resistor_reference_range_V':aux_range,'min_controller_V_after_allocated_ripple_and_path':aux_range[0]-au['controller_path_drop_V_alloc']-au['output_ripple_half_V_alloc'],'scope':'reference/ratio only, additional regulation error, layout and transient not certified'},'SHDN':{'on_min_V':on,'partial_power_off_max_V':off,'unpowered_highZ_max_V':floatoff,'pass_allocated_static_bounds':on>=1 and off<.55 and floatoff<.55,'scope':'depends on allocated logic voltage/leakage and RTN shift; not real partial-power validation'},'fixed_full_CCM_slope_screen':{'m_slope_half_down_V_per_us':.5*.82*(175.1-20.5)/Lmin*1e-6,'max_on_s_at_1V':1/(.5*.82*(175.1-20.5)/Lmin),'conclusion':'A fixed worst-CCM ramp alone consumes 1V CS range before normal DCM required ontime; reject naive CT injection as complete strategy'},'USB':{'preconfigured_3V3_continuous_A_max':.1*4.75*.8/3.465,'cap22u_hold_s_at800mA_3_135to3_0':22e-6*.135/(.8-.1*4.75*.8/3.135),'cap_for1ms_same_burst_F':(.8-.1*4.75*.8/3.135)*.001/.135,'conclusion':'No ESP32 boot/enum current trace; do not claim host compatibility'},'24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED'}
 sr=c['reset_3V3_revision'];vals=[]
 for vv,tr,br,ib in itertools.product(sr['reference_falling_V'],[-pt,pt],[-pt,pt],[-sr['input_bias_abs_A'],sr['input_bias_abs_A']]):
  rr=sr['sense_upper_ohm']*(1+tr);bb=sr['sense_lower_ohm']*(1+br);vals.append(vv*(1+rr/bb)+ib*rr)
 result['reset_3V3']={'rejected_G33_max_release_V':3.07*1.015*1.025,'new_mpn':sr['candidate_mpn'],'new_falling_interval_V':[min(vals),max(vals)],'new_rising_max_V_conservative':max(vals)*(1+sr['hysteresis_fraction_max']),'new_delay_min_s':sr['CT_F']*(1-sr['CT_tolerance'])*min(sr['CT_threshold_V'])/max(sr['CT_current_A']),'new_delay_max_s':sr['CT_F']*(1+sr['CT_tolerance'])*max(sr['CT_threshold_V'])/min(sr['CT_current_A']),'scope':'3V3 target3.135-3.465V, trip before3.0V on static bound; actual delay/droop/current condition and partial-power pending'}
 dump(out/'analysis.json',result)
 # A small, explicit delta to S05 core candidates. No native netlist export.
 old=list(csv.DictReader((ROOT/'netlist/candidate_power_pins.csv').open(encoding='utf-8-sig')))
 changes={'L20':'MSS1583-154KED','R34A':'TNPW1206100KBEEA','R34B':'TNPW1206100KBEEA','R35A':'TNPW06032K94BEEA','R35B':'TNPW060345R3BEEA','U110':'LMR51610XFDBVR','R_U101_OFF':'RC0603FR-078K2L'}
 for row in old:
  if row['ref'] in changes:row['mpn']=changes[row['ref']];row['route_note']='S06 delta; see config/sprint06.json; NOT approved'
  if row['ref']=='U110' and row['pin']=='3':row['route_note']='top143k+1k / bottom10k, 0.1%; old140k is superseded'
 for pin,signal,net in [('1','VDD','AUX12'),('2','OUTH','GATE_ON'),('3','OUTL','GATE_OFF'),('4','GND','GND_HV'),('5','IN-','DRV_INHIBIT_UNQUALIFIED'),('6','IN+','GATE_DRIVE')]:
  old.append(dict(ref='U201',mpn='UCC27511DBVR',pin=pin,pin_name=signal,net=net,layer='L3',route_note='new buffer candidate; R_on10/R_off2.2; supply100n+1u and actual G-S nonlinear behavior pending',review_status='UNREVIEWED_CANDIDATE_NOT_NATIVE'))
 old=[row for row in old if row['ref'] not in ['RG','R_U110_FBT']]
 for ref,mpn,net1,net2 in [('RGON','RC0603FR-0710RL','GATE_ON','HV_GATE'),('RGOFF','RC0603FR-072R2L','GATE_OFF','HV_GATE')]:
  for pin,net in [('1',net1),('2',net2)]:old.append(dict(ref=ref,mpn=mpn,pin=pin,pin_name=pin,net=net,layer='L3',route_note='pulse rating pending; not reviewed',review_status='UNREVIEWED_CANDIDATE_NOT_NATIVE'))
 for ref,mpn,net1,net2 in [('R_U110_FBT_A','TNPW0603143KBEEA','AUX12','AUX_FB_TOP_MID'),('R_U110_FBT_B','TNPW06031K00BEEA','AUX_FB_TOP_MID','U110_FB')]:
  for pin,net in [('1',net1),('2',net2)]:old.append(dict(ref=ref,mpn=mpn,pin=pin,pin_name=pin,net=net,layer='L1',route_note='S06 top143k+1k; bottom10k precision replacement remains required; not reviewed',review_status='UNREVIEWED_CANDIDATE_NOT_NATIVE'))
 for row in old:
  if row['ref']=='R_U110_FBB':row['mpn']='TNPW060310K0BEEA'
 table(ROOT/'netlist/s06_candidate_power_pins.csv',old)
 dump(ROOT/'netlist/s06_candidate_power_pins.meta.json',{'approved_for_native_generation':False,'scope':'S05 core plus explicit S06 delta; incomplete passives/PG/logic/protection; not an assembly netlist','current_config':'config/sprint06.json','row_count':len(old)})
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
