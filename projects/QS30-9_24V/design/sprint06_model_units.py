"""Append-only UCC28C43 primary model qualification, never a closed-loop boost.
Uses TI SLUM521 unencrypted model unchanged and ngspice PSpice compatibility mode.
"""
from pathlib import Path
import argparse,difflib,hashlib,json,re,shutil,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
EXE=REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
MODEL=next((ROOT/'sources/sprint06/UCCx8C43_unencrypted/unpacked').rglob('*.lib'))
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def crossings(t,y,level,rising=True):
 ix=np.where(((y[:-1]<level)&(y[1:]>=level)) if rising else ((y[:-1]>level)&(y[1:]<=level)))[0]
 return np.array([t[j]+(level-y[j])*(t[j+1]-t[j])/(y[j+1]-y[j]) for j in ix])
def main(run,gate_only=False,buffered=False):
 if not re.fullmatch(r'[a-zA-Z0-9_-]+',run):raise ValueError('invalid run name')
 dest=ROOT/'sim'/run;dest.mkdir(parents=True,exist_ok=False)
 prereg={'date':'2026-11-15','scope':'TI UCC28C43 standalone model, no boost, MOS, OVP or precharged HV','model_source':'https://www.ti.com/lit/zip/slum521','model_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'adaptation':'None to model bytes. Local .spiceinit enables ngbehavior=ps; no numerical value edits.',
 'execution_acceptance':'rc0, no error/aborted/timestep-too-small, native endpoint, finite waves','oscillator_acceptance_Hz':[93500,126500],'CT_buffer_load_frequency_delta_max_fraction':.02,'UVLO_model_nominal_V':[8.4,7.6],'UVLO_acceptance_V':[7.8,9,7,8.2],'CS_delay_acceptance_s':70e-9,'CS_to_gate_3V_alloc_s':170e-9,'gate_fixture':'64nC/12V equivalent linear cap 5.333nF, 22ohm series, 10k pulldown; OUT test cap reduced to1pF to avoid adding the separate 1nF timing-test load','step_s':[10e-9,5e-9],'step_sensitivity_frequency_max_fraction':.01,'step_sensitivity_delay_s_max':10e-9,'timeout_s_each':30,'model_temperature_note':'27C only in this run; model scope and lack of guaranteed corner coverage remain gate items'}
 dump(dest/'preregister.json',prereg);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py')
 driver_text=None
 if buffered:
  driver=next((ROOT/'sources/sprint06/UCC27511_unencrypted/unpacked').rglob('*.lib'))
  original=driver.read_text(encoding='cp1252')
  driver_text=original.replace('(5,52m)6,58m)','(5,52m)(6,58m)')
  dump(dest/'driver_adaptation.json',{'source':'https://www.ti.com/lit/zip/slum488','original_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),'change':'Insert one missing opening parenthesis at TABLE point (6,58m); no numeric changes. CP1252 comments retained.','diff':''.join(difflib.unified_diff(original.splitlines(True),driver_text.splitlines(True),fromfile='vendor_original',tofile='syntax_compat')),'engineering_scope':'new buffer UCC27511DBVR, R_on10/R_off2.2, surrogate Qg64nC/12V; not STP9NK50Z switching qualification'})
 results=[]
 for kind in (['cs_gate_buffered'] if buffered else ['cs_gate64nc'] if gate_only else ['osc_nominal','osc_load10k','osc_buffer1meg','uvlo','cs_step','cs_gate64nc']):
  for step in ([10e-9,5e-9] if kind in ['osc_nominal','cs_step','cs_gate64nc','cs_gate_buffered'] else [10e-9]):
   d=dest/(kind+'_'+str(int(step*1e9))+'ns');d.mkdir();shutil.copyfile(MODEL,d/'vendor.lib')
   (d/'.spiceinit').write_text('set ngbehavior=ps\n',encoding='ascii')
   vdd='PWL(0 0 10u 0 210u 12 260u 12 460u 0 500u 0)' if kind=='uvlo' else 'PWL(0 0 1u 12 500u 12)'
   cs='PULSE(0 1.2 300u 1n 1n 50u 100u)' if kind in ['cs_step','cs_gate64nc','cs_gate_buffered'] else '0'
   # Clock-synchronous CS step is NOT assumed; postprocess first edge while OUT was high.
   load='RLOAD ct 0 10k' if kind=='osc_load10k' else 'RLOAD ct 0 1meg' if kind=='osc_buffer1meg' else ''
   gate='RG out gate 22\nCG gate 0 5.333333n\nRGS gate 0 10k' if kind=='cs_gate64nc' else 'RG out gate 1m\nCG gate 0 1p'
   if buffered:
    (d/'driver_compat.lib').write_text(driver_text,encoding='cp1252')
    gate='.include driver_compat.lib\nVINHIBIT inhibit 0 PULSE(0 3.3 375u 1n 1n 20u 1m)\nXD out inhibit 0 vdd dh dl UCC27511_TRANS\nRGON dh gate 10\nRGOFF dl gate 2.2\nCG gate 0 5.333333n\nRGS gate 0 10k'
   deck=f'''S06 TI UCC28C43 standalone {kind}
.include vendor.lib
VDD vdd 0 {vdd}
VFB fb 0 0
VCS cs 0 {cs}
XU comp fb cs ct 0 out vdd vref UCC28C43_START
RT vref ct 15.4k
CT ct 0 1n
CVREF vref 0 100n
CCOMP comp 0 1n
COUT out 0 {'1p' if kind in ['cs_gate64nc','cs_gate_buffered'] else '1n'}
{gate}
{load}
.options reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step} 500u 0 {step} uic
meas tran native_end MAX time
wrdata waves.txt v(vdd) v(vref) v(ct) v(out) v(cs) v(comp) v(gate)
quit
.endc
.end
'''
   (d/'circuit.cir').write_text(deck,encoding='ascii');cmd=[str(EXE),'-b','-o','ngspice.log','circuit.cir'];start=time.monotonic()
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30)
    dump(d/'command.json',{'argv':cmd,'cwd':str(d),'rc':p.returncode,'seconds':time.monotonic()-start,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    log=(d/'ngspice.log').read_text(errors='replace');haserror=bool(re.search(r'(?im)^\s*(error|fatal)|timestep too small|analysis.*aborted',log))
    r={'case':kind,'step_s':step,'rc':p.returncode,'parsed_error':haserror,'execution':'FAIL','engineering':'NOT_EVALUATED'}
    if (d/'waves.txt').exists():
     a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];vddw,vr,ct,out,csw,comp,gatew=a[:,1:].T
     executed=p.returncode==0 and not haserror and np.isfinite(a).all() and t[-1]>=499.99e-6
     r.update(execution='PASS' if executed else 'FAIL',end_s=float(t[-1]),samples=len(t),max_out_V=float(out.max()))
     if executed and kind.startswith('osc'):
      z=crossings(t,ct,1.5);z=z[z>200e-6];f=1/np.median(np.diff(z)) if len(z)>3 else 0
      r.update(frequency_Hz=float(f),CT_min_V=float(ct[t>200e-6].min()),CT_max_V=float(ct[t>200e-6].max()),engineering='PASS_OSC_BAND' if 93500<=f<=126500 else 'FAIL_OSC_BAND')
     elif executed and kind=='uvlo':
      hi=vr>2.5;edges=np.where(hi[1:]!=hi[:-1])[0]+1
      transitions=[{'time_s':float(t[j]),'VDD_V':float(vddw[j]),'reference_on':bool(hi[j])} for j in edges]
      on=[x['VDD_V'] for x in transitions if x['reference_on']];off=[x['VDD_V'] for x in transitions if not x['reference_on']]
      ok=bool(on and off and 7.8<=on[0]<=9 and 7<=off[-1]<=8.2)
      r.update(transitions=transitions,engineering='PASS_UVLO_NOMINAL' if ok else 'FAIL_UVLO')
     elif executed and kind in ['cs_step','cs_gate64nc','cs_gate_buffered']:
      ce=crossings(t,csw,.6);oe=crossings(t,out,6,False);pairs=[]
      for tc in ce:
       if np.interp(tc-2e-9,t,out)<6:continue
       future=oe[oe>=tc]
       if len(future):pairs.append(float(future[0]-tc))
      r.update(CS_to_OUT_6V_delay_s=pairs,engineering='PASS_CS_DELAY' if pairs and max(pairs)<=70e-9 else 'FAIL_CS_DELAY_OR_UNOBSERVABLE')
      if kind in ['cs_gate64nc','cs_gate_buffered']:
       ge=crossings(t,gatew,3,False);gd=[]
       for tc in ce:
        if np.interp(tc-2e-9,t,gatew)<6:continue
        future=ge[ge>=tc]
        if len(future):gd.append(float(future[0]-tc))
       r.update(CS_to_gate_below3V_s=gd,gate_scope='64nC/12V equivalent linear capacitance, source grounded, no real MOS/Miller; diagnostic only',engineering='PASS_GATE_ALLOC_SCREEN' if gd and max(gd)<=170e-9 else 'FAIL_GATE_ALLOC_SCREEN')
       if buffered:r['gate_max_during_inhibit_V']=float(gatew[(t>375.5e-6)&(t<394.9e-6)].max())
    results.append(r)
   except Exception as e:
    dump(d/'exception.json',{'error':str(e),'seconds':time.monotonic()-start});results.append({'case':kind,'step_s':step,'execution':'FAIL','error':str(e)})
   dump(dest/'partial_results.json',results)
 summary={'preregister':prereg,'cases':results,'24V_07':'NOT_PASSED_UNTIL_ALL_REQUIRED_UNITS_QUALIFIED'}
 noms=[r for r in results if r['case']=='osc_nominal' and 'frequency_Hz' in r]
 if noms:
  f0=noms[0]['frequency_Hz'];summary['CT_loading_comparison']=[{'case':r['case'],'frequency_delta_fraction':(r['frequency_Hz']/f0-1) if f0 else None,'engineering':'PASS_LOAD_LIMIT' if f0 and abs(r['frequency_Hz']/f0-1)<=.02 else 'FAIL_LOAD_LIMIT'} for r in results if r['case'] in ['osc_load10k','osc_buffer1meg'] and 'frequency_Hz' in r]
 if len(noms)==2:summary['frequency_step_delta_fraction']=abs(noms[0]['frequency_Hz']/noms[1]['frequency_Hz']-1)
 dump(dest/'results.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--gate-only',action='store_true');p.add_argument('--buffered',action='store_true');args=p.parse_args();main(args.run,args.gate_only,args.buffered)
