"""Exact alternate MOS + original TI direct-drive CS pulse cell, no boost."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import numpy as np
from s06b_real_gate import edges
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06c_vishay_direct_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');st=ROOT/'sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB';uc=next((ROOT/'sources/sprint06/UCCx8C43_unencrypted/unpacked').rglob('*.lib'));rows=[]
 dump(out/'preregister.json',{'scope':'SiHP8N50D-GE3 alternate candidate; UCC28C43 original START +22ohm direct gate.195V resistor-load device cell, not boost or precharged output. ForcedCS is not source-current feedback.','temperature_scope':'MOS electrical25/100C model; TI behavioral thresholds/delays nominal and not full-temperature guarantees','criteria':{'stop_s':60e-6,'CS_half_to_VGS3_s_max':370e-9,'peak_controller_OUT_A_abs_max':1,'positive_charge_energy_J_max':5e-6,'half_step_delay_delta_s_max':10e-9,'half_step_peak_current_relative_delta_max':.03,'half_step_energy_relative_delta_max':.03},'cases':'VDD12/12.6,MOS25/100C,maxstep2/1ns; same1nA/1uV/.001 tolerances','model_hashes':{'MOS':hashlib.sha256(st.read_bytes()).hexdigest(),'TI':hashlib.sha256(uc.read_bytes()).hexdigest()},'timeout_s':30})
 for temp in [25,100]:
  for vdd in [12,12.6]:
   for ns in [2,1]:
    d=out/f'{temp}C_V{vdd}_{ns}ns';d.mkdir();shutil.copyfile(st,d/'st.lib');shutil.copyfile(uc,d/'uc.lib');(d/'.spiceinit').write_text('set ngbehavior=ps\n')
    s=f'''Alternate exact transistor CS gate cell, not boost workpoint
.include st.lib
.include uc.lib
VDD vdd 0 PWL(0 0 1u {vdd} 60u {vdd})
VBIAS bias 0 195
RLOAD bias drain 200
XQ drain gate src SiHP8N50D
RSHUNT src 0 .82
VPROBE out gr 0
RG gr gate 22
RGS gate src 10k
XU comp fb cs ct 0 out vdd vref UCC28C43_START
VFB fb 0 0
VCS cs 0 PULSE(0 1.2 30u 1n 1n 10u 20u)
RT vref ct 15.4k
CT ct 0 1n
CVREF vref 0 100n
CCOMP comp 0 1n
.temp {temp}
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
set numdgt=15
tran {ns}n 60u 0 {ns}n uic
wrdata waves.txt v(cs) v(out) v(gate) v(src) v(drain) i(vprobe) i(vbias) v(vref)
quit
.endc
.end
'''
    (d/'circuit.cir').write_text(s,encoding='ascii');cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'temperature_C':temp,'VDD_V':vdd,'step_s':ns*1e-9}
    try:
     p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)),model_warnings=[x for x in log.splitlines() if re.search('unrecognized|ignored|unknown parameter',x,re.I)])
     if (d/'waves.txt').exists():
      a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];cs,vo,vg,vs,vd,ig,ib,vr=a[:,1:].T;vgs=vg-vs;r.update(finite=bool(np.isfinite(a).all()),end_s=float(t[-1]),peak_OUT_A=float(abs(ig).max()))
      if t[-1]>=59.999e-6:
       delays=[]
       for te in edges(t,cs,.6,True):
        if np.interp(te-2e-9,t,vgs)<6:continue
        z=edges(t,vgs,3);z=z[z>=te]
        if len(z):delays.append(float(z[0]-te))
       en=[]
       for te in edges(t,vo,6,True):
        k=(t>=te-100e-9)&(t<=te+1e-6)
        if k.sum()>2:en.append(float(np.trapezoid(np.maximum(vo[k]*ig[k],0),t[k])))
       r.update(CS_to_VGS3_s=delays,gate_charge_energy_max_J=max(en) if en else None,VGS_min_V=float(vgs.min()),VGS_max_V=float(vgs.max()))
     r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=59.999e-6 else 'FAIL'
     r['engineering']='PASS_NOMINAL_DEVICE_CELL_ONLY' if r['execution']=='PASS' and not r['model_warnings'] and r.get('CS_to_VGS3_s') and max(r['CS_to_VGS3_s'])<=370e-9 and r.get('peak_OUT_A',99)<=1 and r.get('gate_charge_energy_max_J',1)<=5e-6 else 'NOT_PASSED'
    except Exception as e:r.update(execution='FAIL',engineering='NOT_PASSED',error=str(e));dump(d/'exception.json',r)
    rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
