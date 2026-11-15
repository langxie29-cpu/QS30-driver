"""Reproducible S06B boundary audit, not a switched-system qualification."""
from pathlib import Path
import json,math,itertools,hashlib
ROOT=Path(__file__).resolve().parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'docs/sprint06b';s=json.loads((ROOT/'config/sprint05.json').read_text());c=json.loads((ROOT/'config/sprint06.json').read_text());a=json.loads((ROOT/'docs/sprint06/analysis.json').read_text());P=a['HV_W'];V=175.1;rows=[]
 for eta,vin,L,f in itertools.product([1,.85,.8,.75],[20.5,24,26.4],[121.5e-6,150e-6,165e-6],[93500,110000,126500]):
  d=math.sqrt(2*L*f*(P/eta/V)*(V-vin))/vin;d2=vin*d/(V-vin);ip=vin*d/(L*f)
  rows.append(dict(eta_screen=eta,Vin_V=vin,L_H=L,f_Hz=f,Ipk_A=ip,Irms_A=ip*math.sqrt((d+d2)/3),idle_fraction=1-d-d2,ton_s=d/f,toff_s=d2/f))
 dump(out/'LOSS_AWARE_DCM_CORNERS.json',rows)
 summary=[]
 for eta in [1,.85,.8,.75]:
  rr=[r for r in rows if r['eta_screen']==eta];summary.append(dict(eta=eta,max_Ipk_A=max(r['Ipk_A'] for r in rr),max_Irms_A=max(r['Irms_A'] for r in rr),min_idle=min(r['idle_fraction'] for r in rr),earliest_CS_limit_A=a['CS']['min_limit_A'],current_reserve_A=a['CS']['min_limit_A']-max(r['Ipk_A'] for r in rr)))
 # Off interval exact ideal LC after a single current-limited pulse. No load,
 # no feedback, no claim about startup time or a 170V operating point.
 starts=[];L=165e-6;C=20e-6*1.05+3e-7*1.10;vin=26.4;vd=.93341735425;ip=1.0263221444;z=math.sqrt(L/C);w=1/math.sqrt(L*C)
 for v0 in [vin-vd,30,40,80,170]:
  x=v0-vin+vd;theta=math.atan2(ip*z,x);toff=theta/w;vend=vin-vd+math.hypot(x,ip*z);ton=L*ip/vin
  starts.append(dict(Vout_initial_V=v0,L_H=L,C_F=C,Ipk_A=ip,Vin_V=vin,Vdiode_V=vd,ton_s=ton,off_to_zero_s=toff,Vout_end_single_pulse_V=vend,max_repetition_Hz=1/(ton+toff),scope='ideal single pulse, unloaded; voltage points are boundary bias conditions, not simulated operating points'))
 dump(out/'SINGLE_PULSE_DEMAG_BOUNDARIES.json',starts)
 fall=a['reset_3V3']['new_falling_interval_V'][0];margin=fall-3;pg=[]
 for load,C,esr in itertools.product([.25,.5,.8],[22e-6,100e-6,470e-6],[0,.02]):
  # 18us is a typical, CT-open,5% overdrive datum, not a bounded delay for this circuit.
  pg.append(dict(load_A=load,C_effective_F=C,ESR_ohm=esr,static_margin_V=margin,voltage_after_typical18us_V=fall-load*.000018/C-load*esr,available_time_to3V_s=max(0,(margin-load*esr)*C/load),interpretation='sensitivity only: typical propagation is not a guarantee; reset not qualified'))
 dump(out/'PG_DROOP_SENSITIVITY.json',pg)
 usb=[]
 for port in [.1,.5]:
  available=port*4.75*.8/3.465
  usb.append(dict(USB_input_limit_A=port,upper_bound_3V3_A=available,ESP_recommended_supply_capability_A=.5,reserve_before_other_3V3_loads_A=available-.5,limit_scope='USB2 design baseline; no cable/mux/IQ allowance, pre-enumeration and configured cases differ'))
 # Proposed isolated SHDN signal barrier, not a fast fault cutoff.
 rf=100000;rd=8200;t=.01;vsmin=(20.5-.4)*rd*(1-t)/(rf*(1+t)+rd*(1-t));vsmax=40*rd*(1+t)/(rf*(1-t)+rd*(1+t))
 iso={'candidate':'VOS618A-7T','pins':{'1':'LED_A via820ohm from qualified permit','2':'LED_K to logic GND','4':'collector via100k from same eFuse IN','3':'emitter to same eFuse SHDN'},'SHDN_pulldown_ohm_to_own_RTN':8200,'R_feed_ohm':100000,'resistor_tolerance':.01,'SHDN_on_min_V_if_VCEsat_le0p4':vsmin,'SHDN_on_max_V_at40V':vsmax,'required_off_leak_A_max_for0p55V':.55/(rd*(1+t))-10e-6,'LED_min_A_if_VF_le1p5_at_VOH2p4':(2.4-1.5)/(820*1.01),'collector_demand_A_max_at26p4V':26.4/(rf*(1-t)+rd*(1-t)),'qualification':'candidate topology only; VCEsat and CTR quoted25C, leakage at40V/hot and max turnoff delay unbounded. Do not use opto as cycle-by-cycle shutdown. U100 normal bootstrap must remain allowed, U101 default-off.'}
 result={'date':'2026-11-15','scope':'parameter and analytic boundary audit, not 24V07 qualification','inherited_config_hashes':{n:hashlib.sha256((ROOT/'config'/n).read_bytes()).hexdigest() for n in ['sprint05.json','sprint06.json']},'loss_screen_method':'multiply ideal equivalent transferred power by1/eta. Conservative allocation sensitivity, not an extracted nonlinear loss model; cannot infer actual measured efficiency or actual failure solely from this screen.','DCM_summary':summary,'minimum_eta_for_earliest_limit_in_ideal_shape_screen':(a['normal_peak_max_A']/a['CS']['min_limit_A'])**2,'current_candidate_decision':'0.82ohm and110kHz are NOT qualified for full-load capability. Do not lower shunt or raise frequency before real loss/hot-magnetic/delay qualification.','thermal':{'L_mpn':'MSS1583-154KED','new_web_DCR25_max_ohm':.16,'local_PDF_DCR25_max_ohm':.159,'review_DCR100_ohm_copper_alpha0p00393':.16*(1+.00393*75),'copper_loss_W_at_loss_screen_max_Irms':summary[-1]['max_Irms_A']**2*.16*(1+.00393*75),'required_hot_10pct_Isat_A':a['CS']['required_hot_Isat_for20pct_headroom_A'],'hot_L_min_required_H':121.5e-6,'qualification':'NO_HOT_LI_OR_CORELOSS_DATA; DCR copper-only estimate cannot qualify winding/core temperature. Current vendor webpage Isat is explicitly25C.'},'PG':{'lowest_falling_threshold_V':fall,'margin_to_MCU3V0_V':margin,'allowed_droop_V_per_s_at_typ18us_no_ESR':margin/18e-6,'minimum_C_F_at0p8A_typ18us_no_ESR':.8*18e-6/margin,'delay_limit':'18us typical atCTopen/5percent overdrive, no max; CT22n candidate differs. Not a qualification bound.','decision':'reject static-threshold-only PG/reset qualification; need earlier input-power-fail + bounded MCU reset/DRV/HV inhibit path and hold-up, or supervisor with guaranteed falling delay'},'USB':usb,'USB_decision':'ordinary unconfigured100mA host cannot be qualified from a0.5A recommended source-capability requirement. Configured500mA has only48mA ideal upper reserve at3V3max; startup/current traces, mux loss, enumeration, inrush and 5V fault protection remain open. Retain offline-programming requirement.','isolated_SHDN_candidate':iso,'24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','manufacturing':'HOLD'}
 dump(out/'boundary_analysis.json',result)
 delta={'schema_version':1,'baseline':'sprint06.json','date':'2026-11-15','status':'S06B_QUALIFICATION_AUDIT_NOT_APPROVED','manufacturing':'HOLD','parameter_change_policy':'S06 retained unchanged; no production electrical values approved by this audit','source_additions':['ST exact25C MOS model and PDF','Vishay exact US1G model','Espressif module supply capability0.5A','TPS2660 reverse polarity interface application report','VOS618A primary25C candidate data'],'interpretation_changes':['normal ideal0.943A is not a loss-aware capability proof','0.82ohm/110kHz normal-load reserve unqualified','ST transient model fails first transition in isolation','direct logic-GND to eFuse RTN interface and direct FLT-to3V3 pullup rejected for reverse sequence'],'candidates':{'SHDN_signal_barrier':iso,'startup_policy':'passive front-end charge with PWM off, current-limited pulse with verified demagnetization before another pulse; fixed110kHz and CCM allowed only after explicit mode qualification. No hardware candidate released.'},'USB_offline_required':True,'native_export':{'approved':False},'evidence':'docs/SPRINT06B_REPORT.md','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED'}
 dump(ROOT/'config/sprint06b.json',delta);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
