"""Sprint02 isolated diagnostics. Appends runs and snapshots all source inputs.
No KiCad/circuit-source edits and no reuse of historical PASS labels.
"""
from pathlib import Path
import importlib.util,json,argparse,hashlib,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'sim/sprint02'
spec=importlib.util.spec_from_file_location('s02_source',BASE/'source/hv_convergence9.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.ROOT=ROOT;h.BASE=BASE;h.MODEL=BASE/'source/uc3843_functional.lib';h.EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def classify(c,t,v):
    if c.get('stage')=='controller':
        d=h.ctrl_metrics(c,t,v);d['status']='MODEL_CHECK_PASS' if d['status']=='SIMULATED PASS' else 'FAIL'
        return d
    d=h.power_metrics(c,t,v)
    hv=v('v(hv)');il=v('i(l20)');late=t>c.get('stop',.15)-.01
    gate=v('v(gate)')>5
    d['late_gate_duty']=float(np.trapezoid(gate[late].astype(float),t[late])/(t[late][-1]-t[late][0]))
    d['feedback_end_V']=float(v('v(fb)')[-1]);d['comp_end_V']=float(v('v(comp)')[-1])
    d['current_window_A']=[float(il[late].min()),float(il[late].max())]
    d['reached_169V_s']=float(t[np.flatnonzero(hv>=169)[0]]) if np.any(hv>=169) else None
    d['load_active']=bool(np.any(hv>125))
    if c.get('closed'):
        good=169<=d['hv_late_average_V']<=175 and d['hv_late_pp_V']<2 and d['hv_peak_V']<220 and d['inductor_peak_A']<5
        d['status']='CANDIDATE_WINDOW_PASS' if good else 'FAIL'
    return d

def cases(stage):
 if stage=='controller':
  return [dict(id='max_duty',comp_force=5,stop=.004,step=50e-9),
   dict(id='cs_latch',comp_force=5,stop=.003,step=20e-9,cs='BCS cs 0 V=(v(ct)>1.8 && v(ct)<2.2) ? 1.2 : 0'),
   dict(id='uvlo',supply='PWL(0 0 3m 12 4m 12 7m 0 10m 0)',comp_force=5),
   dict(id='max_duty_idis_2p8m',comp_force=5,idis=.0028,stop=.004,step=50e-9),
   dict(id='max_duty_idis_8p3m',comp_force=5,idis=.0083,stop=.004,step=50e-9),
   dict(id='max_duty_rt22k',comp_force=5,rt=22000,ct=1e-9,stop=.004,step=50e-9)]
 if stage=='candidate':
  return [dict(id='ramp_ratio_derived_generic',closed=True,c10=0,buffer=True,compensation='type2',rt=22000,ct=1e-9,rramp=1500,stop=.3),
   dict(id='ramp_ratio_derived_vendor_diode',closed=True,c10=0,buffer=True,compensation='type2',rt=22000,ct=1e-9,rramp=1500,vendor_diode=True,stop=.3)]
 if stage=='power':
  return [dict(id='actual_cs_fixture',closed=True,wrong_cs=True,c10=10e-9,stop=.06),
   dict(id='direct_ramp_stalled',closed=True,c10=10e-9,stop=.06),
   dict(id='buffered_existing_c10',closed=True,c10=10e-9,buffer=True,stop=.12),
   dict(id='buffered_no_c10',closed=True,c10=0,buffer=True,stop=.12),
   dict(id='buffered_type2',closed=True,c10=0,buffer=True,compensation='type2',rt=22000,ct=1e-9,stop=.15),
   dict(id='open_original_c10',closed=False,c10=10e-9,duty=.93,resistive=True,stop=.03),
   dict(id='open_no_c10',closed=False,c10=0,duty=.93,resistive=True,stop=.03)]
 raise ValueError(stage)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['controller','power','candidate']);ap.add_argument('--run',required=True);ap.add_argument('--cases');a=ap.parse_args()
 assert Path(a.run).name==a.run
 dest=BASE/a.run;dest.mkdir(exist_ok=False)
 (dest/'driver.py').write_bytes(Path(__file__).read_bytes())
 cs=cases(a.stage);selected=a.cases.split(',') if a.cases else [c['id'] for c in cs]
 assert set(selected)<=set(c['id'] for c in cs)
 result={'stage':a.stage,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),BASE/'source/hv_convergence9.py',h.MODEL,h.EXE]},'results':[],'signoff':'HOLD'}
 for c in cs:
  if c['id'] not in selected:continue
  c=dict(c,stage=a.stage)
  deck=h.controller_deck(c) if a.stage=='controller' else h.power_deck(c)
  # Zero-voltage current probe is physical series instrumentation; keep native
  # differential vector computations in .control let expressions.
  if a.stage in ('power','candidate'):
   deck=deck.replace('let pmos=v(mos,src)*i(vswi)','let vds=v(mos)-v(src)\nlet vr=v(hv)-v(sw)\nlet pmos=vds*i(vswi)\nmeas tran vds_peak MAX vds\nmeas tran diode_reverse MAX vr')
  if c.get('rramp'):
   deck=deck.replace('RRAMP rampbuf cs 2.8k',f'RRAMP rampbuf cs {c["rramp"]}')
  if c.get('vendor_diode'):
   raw=(BASE/'source/diotec_uf4007_spice.lib').read_text(encoding='ascii').replace(' mfg=Diotec type=Rectifier','')
   deck=deck.replace('D20 sw hv UF','X20 sw hv UF4007').replace('.control',raw+'\n.control',1)
  r=h.simulate(dest/c['id'],deck,c.get('stop',.01 if a.stage=='controller' else .15),{'case':c,'fixture':'isolated; not complete actual protection/enable chain'},lambda t,v:classify(c,t,v))
  result['results'].append(r)
  (dest/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 return 0 if all(r['execution']=='PASS' for r in result['results']) else 1
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf-8');raise SystemExit(main())
