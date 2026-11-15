"""Exact STP9NK50Z primary25C model + TI controller direct-gate unit.
HV source is a resistor-load transistor bias only, no boost/COUT/precharged operating point.
"""
from pathlib import Path
import json,re,shutil,subprocess,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
ST=next(p for p in (ROOT/'sources/sprint06b/ST_model_cn/unpacked').rglob('*') if p.is_file())
UC=next((ROOT/'sources/sprint06/UCCx8C43_unencrypted/unpacked').rglob('*.lib'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def edges(t,y,level,up=False):
 k=np.where(((y[:-1]<level)&(y[1:]>=level)) if up else ((y[:-1]>level)&(y[1:]<=level)))[0]
 return np.array([t[j]+(level-y[j])*(t[j+1]-t[j])/(y[j+1]-y[j]) for j in k])
def main():
 dest=ROOT/'sim/s06b_real_gate_v1';dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py')
 pre={'date':'2026-11-15','scope':'TI UCC28C43_START driving exact ST model through resistor; 195V resistor drain bias only, no boost, no170V precharge or closed loop','ST_source':'https://www.st.com.cn/resource/en/spice_model/stp9nk50z_spice.zip','ST_sha256':hashlib.sha256(ST.read_bytes()).hexdigest(),'ST_model_pin_order':'D,G,S (different from physical G,D,S!)','temperature_C':25,'temperature_validity':'ST header expressly permits25C only; not hot/cold corners','criteria':{'stop_s':60e-6,'CS_to_VGS3V_s_max':370e-9,'peak_controller_output_A_max':1,'output_cap_energy_J_max':5e-6,'step_delta_s_max':10e-9},'stimulus':'CS forced1.2V step; actual0.82ohm source shunt included but not connected to CS in this device-cell stimulus. Does not qualify current-feedback loop.','cases':'Rgate15/22, VDD11.4/12.6, maxstep2ns/1ns','timeout_s':40}
 dump(dest/'preregister.json',pre);rows=[]
 for rg in [15,22]:
  for vdd in [11.4,12.6]:
   for step in [2e-9,1e-9]:
    d=dest/f'R{rg}_V{vdd}_{step*1e9:g}ns';d.mkdir();shutil.copyfile(ST,d/'st.lib');shutil.copyfile(UC,d/'uc.lib');(d/'.spiceinit').write_text('set ngbehavior=ps\n')
    s=f'''S06B exact ST transistor gate cell25C, not a boost workpoint
.include st.lib
.include uc.lib
VDD vdd 0 PWL(0 0 1u {vdd} 60u {vdd})
VBIAS bias 0 195
RLOAD bias drain 200
XQ drain gate src STP9NK50Z
RSHUNT src 0 .82
VPROBE out gr 0
RG gr gate {rg}
RGS gate src 10k
XU comp fb cs ct 0 out vdd vref UCC28C43_START
VFB fb 0 0
VCS cs 0 PULSE(0 1.2 30u 1n 1n 10u 20u)
RT vref ct 15.4k
CT ct 0 1n
CVREF vref 0 100n
CCOMP comp 0 1n
.temp 25
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
set numdgt=15
tran {step} 60u 0 {step} uic
meas tran native_end MAX time
wrdata waves.txt v(cs) v(out) v(gate) v(src) v(drain) i(vprobe) i(vbias) v(vref)
quit
.endc
.end
'''
    (d/'circuit.cir').write_text(s,encoding='ascii');cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'rg_ohm':rg,'VDD_V':vdd,'step_s':step}
    try:
     p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
     if (d/'waves.txt').exists():
      a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];cs,out,vg,vs,vd,ig,ibias,vref=a[:,1:].T;vgs=vg-vs
      r.update(end_s=float(t[-1]),finite=bool(np.isfinite(a).all()),peak_output_A=float(abs(ig).max()))
      if t[-1]>=59.999e-6:
       ce=edges(t,cs,.6,True);ge=edges(t,vgs,3);dd=[]
       for tc in ce:
        if np.interp(tc-2e-9,t,vgs)<6:continue
        z=ge[ge>=tc]
        if len(z):dd.append(float(z[0]-tc))
       # Positive delivered energy per complete gate charge, not power-stage efficiency.
       high=out>6; starts=edges(t,out,6,True);ener=[]
       for ts in starts:
        k=(t>=ts-100e-9)&(t<=ts+1e-6)
        if k.sum()>2:ener.append(float(np.trapezoid(np.maximum(out[k]*ig[k],0),t[k])))
       r.update(CS_to_VGS3V_s=dd,gate_charge_energy_max_J=max(ener) if ener else None,gate_VGS_min_V=float(vgs.min()),gate_VGS_max_V=float(vgs.max()),drain_peak_V=float((vd-vs).max()))
     r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=59.999e-6 else 'FAIL'
     r['engineering']='PASS_25C_DEVICE_CELL_ONLY' if r['execution']=='PASS' and r.get('CS_to_VGS3V_s') and max(r['CS_to_VGS3V_s'])<=370e-9 and r.get('peak_output_A',99)<=1 and r.get('gate_charge_energy_max_J',1)<=5e-6 else 'FAIL'
    except Exception as e:r.update(execution='FAIL',engineering='FAIL',error=str(e));dump(d/'exception.json',r)
    rows.append(r);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'preregister':pre,'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
