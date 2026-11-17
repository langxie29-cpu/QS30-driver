"""Principal corrected implementation; rejected Flash draft is retained unchanged."""
import lab,numpy as np
def build(p,kind):
 lab.full(p,stop=.020,step=5e-8,method='gear')
 s=(p/'circuit.cir').read_text()
 for old,new in [('REN1 in en 200k\nREN2 en 0 12.8k','VEN en 0 0'),('VINPUT vin 0 PWL(0 0 1m 24)','VINPUT vin 0 PWL(0 0 1u 26.4)'),('COUT hv 0 20.3u','COUT hv 0 24.36u'),('LPOWER in drain 150u','LPOWER in drain 135u')]:
  assert s.count(old)==1;s=s.replace(old,new)
 if kind=='precharge':
  # Series AFTER all input bulk, BEFORE L. No parallel bypass of the inductor.
  s=s.replace('LPOWER in drain 135u','RPRE in pre 31.35\nLPOWER pre drain 135u')
  s=s.replace('.save V(out)','.save I(RPRE) V(pre) V(out)')
 elif kind=='slew':s=s.replace('PWL(0 0 1u 26.4)','PWL(0 0 0.00849 26.4)')
 assert 'VEN en 0 0' in s and 'REN1' not in s
 (p/'circuit.cir').write_text(s,encoding='ascii')
def measure(p):
 c=lab.native(p/'circuit.raw');t=c['time'];i=c['i(lpower)'];v=c['v(hv)'];vgs=c['v(gate)']-c['v(src)']
 m=dict(endpoint_s=float(t[-1]),points=len(t),IL_peak_A=float(i.max()),IL_min_A=float(i.min()),Vout_peak_V=float(v.max()),Vout_end_V=float(v[-1]),VGS_peak_V=float(vgs.max()),diode_peak_A=float(c['i(drec)'].max()),diode_reverse_A=float(c['i(drec)'].min()),MOS_VDS_min_V=float((c['v(drain)']-c['v(src)']).min()),MOS_VDS_max_V=float((c['v(drain)']-c['v(src)']).max()),IL_rms_A=float(np.sqrt(np.trapezoid(i*i,t)/(t[-1]-t[0]))),raw_sha256=lab.sha(p/'circuit.raw'),classification='INCONCLUSIVE',scope='Passive linear25C fixture only; no real eFuse dynamics/hot magnetics/bypass or170V qualification')
 if 'i(rpre)' in c:
  ip=c['i(rpre)'];m.update(precharge_peak_W=float((ip*ip*31.35).max()),precharge_energy_J=float(np.trapezoid(ip*ip*31.35,t)),bound_A=26.4/31.35,bound_satisfied=bool(i.max()<=26.4/31.35),qualification='LIMITED_PASS for this finite passive fixture and resistor-bound calculation only; part pulse rating, short duration and bypass design HOLD')
 lab.dump(p/'metrics.json',m);return m
if __name__=='__main__':
 results=[]
 for kind in ['uncontrolled','precharge','slew']:
  p=lab.HERE/'evidence/principal/startup_bounds'/kind;build(p,kind)
  cmd=lab.execute(p,'Conservative26.4V/C24.36u/L135u passive scenario; compare truly series31.35ohm(33ohm-5%) precharge or datasheet-derived fastest slew8.49ms to uncontrolled1us. No real input device implied.', 'Series precharge resistor or source slew ONE variable relative uncontrolled reference; same fixed corner',60)
  results.append(dict(case=kind,command=cmd,**(measure(p) if cmd['rc']==0 else dict(classification='EXECUTION_FAIL'))));print(results[-1],flush=True)
 lab.dump(lab.HERE/'evidence/principal/startup_bounds/results.json',results)
