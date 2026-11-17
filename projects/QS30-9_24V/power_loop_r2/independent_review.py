"""Principal independent numerical review; raw evidence read only."""
import json,re
import lab,numpy as np
OUT=lab.HERE/'evidence/independent';OUT.mkdir(parents=True,exist_ok=True)
R=1/(1/5200+2/(90900+90900)+1/(100000+100000+1900.6))
def audit_case(p,windows=()):
 cmd=json.loads((p/'command.json').read_text());pr=json.loads((p/'preregister.json').read_text())
 if lab.sha(p/'circuit.cir')!=pr['netlist_sha256']:raise ValueError('Netlist changed after registration')
 if cmd['rc']!=0:return dict(case=str(p.relative_to(lab.HERE)),classification='EXECUTION_FAIL',command=cmd,raw_available=(p/'circuit.raw').exists())
 c=lab.native(p/'circuit.raw');t=c['time'];i=int(np.argmax(c['v(sense)']))
 target=float(pr['tran'].split()[2]);endpoint=abs(float(t[-1])-target)<1e-12
 m=dict(case=str(p.relative_to(lab.HERE)),endpoint_s=float(t[-1]),endpoint_reached=endpoint,points=len(t),raw_sha256=lab.sha(p/'circuit.raw'),peak_V=float(c['v(hv)'].max()),initial_V=float(c['v(hv)'][0]),sense_min_V=float(c['v(sense)'].min()),sense_peak_V=float(c['v(sense)'].max()),IL_peak_A=float(c['i(lpower)'].max()),shunt_peak_A=float(c['i(rsrc)'].max()),diode_reverse_A=float(c['i(drec)'].min()),VGS_min_V=float((c['v(gate)']-c['v(src)']).min()),VGS_max_V=float((c['v(gate)']-c['v(src)']).max()),windows=[dict(start_s=a,end_s=b,**lab.stats(c,a,b)) for a,b in windows],event={k:float(v[i]) for k,v in c.items()})
 # MOS package currents reconstructed strictly from top-level node KCL.
 qd=c['i(lpower)']-c['i(drec)']-c['i(rsnub)']
 qs=-c['i(rsrc)']-c['i(rf)']+c['i(rgs)']-c['i(rneg)']
 qg=(c['v(out)']-c['v(gate)'])/22-c['i(rgs)']+c['i(rneg)']
 m['MOS_reconstructed_peak_event_A']=dict(drain_in=float(qd[i]),source_in=float(qs[i]),gate_in=float(qg[i]),sum=float((qd+qs+qg)[i]))
 local=(t>=t[i]-1e-7)&(t<=t[i]+1e-7)
 m['KCL_max_local_200ns_A']=float(abs(qd+qs+qg)[local].max())
 m['KCL_max_whole_A']=float(abs(qd+qs+qg).max())
 if 'i(vqd)' in c:
  m['zero_probe_reconstruction_error_A']=dict(drain=float(abs(qd-c['i(vqd)']).max()),source=float(abs(qs+c['i(vqs)']).max()),gate=float(abs(qg-c['i(vqg)']).max()))
 # Duration measures interpolate threshold crossing, rather than count adaptive samples.
 def exceed_duration(y,limit):
  y=np.abs(y)-limit;ya,yb=y[:-1],y[1:];dt=np.diff(t)
  area=np.where((ya>0)&(yb>0),dt,0.0)
  cross=(ya>0)!=(yb>0);f=np.abs(ya[cross])/(np.abs(ya[cross])+np.abs(yb[cross]));area[cross]=dt[cross]*np.where(ya[cross]>0,f,1-f)
  return float(area.sum())
 m['sense_abs_over_0p3V_duration_s']=exceed_duration(c['v(sense)'],.3)
 if windows:
  # Delivered output is hv. This reconstructed ideal capacitor voltage is DIAGNOSTIC ONLY.
  icap=c['i(drec)']+c['i(rsnub)']-c['v(hv)']/R
  cap=c['v(hv)']-.1*icap
  m['ideal_C_voltage_diagnostic_windows']=[dict(start_s=a,end_s=b,**lab.stats(dict(time=t,cap=cap),a,b,'cap')) for a,b in windows]
  a,b=windows[-1];edges=np.arange(a,b-10e-6+1e-12,10e-6)
  spans=[lab.stats(c,float(x),float(x+10e-6))['pp'] for x in edges]
  m['fixed_10us_block_raw_Vpp_last_window']=dict(median=float(np.median(spans)),p95=float(np.percentile(spans,95)),maximum=float(max(spans)))
 # Maximum inductor current is not a thermal/saturation or full current-limit qualification.
 m['pin_absolute_screen_pass']=bool(endpoint and m['sense_peak_V']<.3 and m['sense_min_V']>-.3)
 m['classification']='LIMITED_PASS' if m['pin_absolute_screen_pass'] else 'ELECTRICAL_FAIL'
 m['scope']='Pin absolute-voltage screen in this fixture ONLY; full cycle-limit/fault, hardware, hotL, input device and loop acceptance remain HOLD'
 return m
def averaged():
 V=170.;vin=24.;L=150e-6;C=20.3e-6;f=100e3;beta=1900.6/201900.6
 ip=np.sqrt(2*V*(V-vin)/(R*L*f));d=L*ip*f/vin;d2=L*ip*f/(V-vin)
 fp=(2*V-vin)/(2*np.pi*R*C*(V-vin));gip=L*f*ip/(V-vin);gvc=gip/(5.5*.062);rout=R*(V-vin)/(2*V-vin)
 return dict(R_effective_ohm=R,output_load_W=V*V/R,feedback_beta=beta,constant_power_fp_Hz=1/(np.pi*R*C),DCM_assumed_frequency_Hz=f,DCM_Ipk_A=float(ip),DCM_on_fraction=float(d),DCM_off_fraction=float(d2),DCM_valid_under_assumptions=bool(d+d2<1),DCM_output_pole_Hz=float(fp),DCM_Ipk_to_Iout_AperA=float(gip),DCM_Vc_to_Iout_AperV=float(gvc),DCM_Vc_to_Vout_DC=float(gvc*rout),CCM_RHP_zero_ideal_duty_Hz=R*(vin/V)**2/(2*np.pi*L),comp_zero_Hz=1/(2*np.pi*22000*6.8e-9),comp_highpole_Hz=(6.8e-9+100e-12)/(2*np.pi*22000*6.8e-9*100e-12),derivation='DCM Iout=L*f*Ipk^2/[2*(Vout-Vin)]. C*dV/dt=Iout-V/R. Linearize aboutVo: pole(2Vo-Vin)/[2piRC(Vo-Vin)], gainLfIpk/(Vo-Vin). Assumes fully demagnetized triangular positive currents; parasitic recovery and source ringing excluded. CCM zero uses idealD=.859, not measured duty.',classification='INCONCLUSIVE',decision='Explanatory model only; no Bode measurement or phase/gain-margin qualification. Compensation unchanged pending P0 credibility.')
def fft_history():
 c=lab.native(lab.BASE/'circuit.raw');t=c['time'];a=.04;b=.06;fs=5e6;grid=np.arange(a,b,1/fs);y=np.interp(grid,t,c['v(hv)']);trend=np.polyval(np.polyfit(grid-a,y,1),grid-a);w=np.hanning(len(y));sp=2*np.abs(np.fft.rfft((y-trend)*w))/w.sum();freq=np.fft.rfftfreq(len(y),1/fs)
 indices=np.argsort(sp[1:])[::-1][:12]+1
 return dict(window_s=[a,b],resample_fs_Hz=fs,nyquist_Hz=fs/2,bin_Hz=fs/len(y),window='Hann',detrend='linear',amplitude='single-sided peak amplitude, not rawVpp',largest_bins=[dict(f_Hz=float(freq[k]),peak_amplitude_V=float(sp[k])) for k in indices],native_average_rate_Hz=(len(t)-1)/(t[-1]-t[0]),caveats=['First50Hz bins may be unresolved startup trend, cannot establish physical oscillation frequency','Interpolation does not supply missing subns bandwidth; rawVpp remains acceptance metric','No established steady window in60ms; spectra are descriptive only'])
if __name__=='__main__':
 results=[]
 for p in sorted((lab.HERE/'runs/20261117T150846Z/round_01/sense_root').glob('run_*')):
  if (p/'command.json').exists():results.append(audit_case(p))
 for p in sorted((lab.HERE/'evidence/principal/minimum_cell').glob('*')):
  if p.is_dir():results.append(audit_case(p))
 for name,windows in [('filter22R_4p7n_60ms',[(.04,.05),(.05,.055),(.055,.06)]),('unchanged_200ms',[(.06,.10),(.10,.15),(.15,.20)])]:
  p=lab.HERE/'evidence/principal'/name
  if (p/'command.json').exists():results.append(audit_case(p,windows))
 lab.dump(OUT/'review.json',dict(cases=results,averaged_model=averaged(),history_fft=fft_history()))
 print(json.dumps({k:v for k,v in averaged().items() if isinstance(v,(float,int,bool))},indent=2))
