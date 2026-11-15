"""Check vendor gate-charge characterization before trusting a running model."""
from pathlib import Path
import json,re,shutil,subprocess
import numpy as np
from s06b_real_gate import edges
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06c_gate_charge_v2';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');rows=[];vendor=ROOT/'sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB'
 dump(out/'preregister.json',{'scope':'Vishay exact original model, gate-charge test400V/4A,1mA gate current to10V. Ideal diode clamp holds initial drain near400V and caps gate near12V; device test only, not boost workpoint.','criteria':'finite40us/no abort/error;25C nominal15nC +/-20percent fit screen, compare30nC datasheet max only at its stated25C conditions;100C exploratory only. Halfstep charge delta<=1percent. No model parameter fitting.','fixture_revision':'v1 had an ambiguous initial gate OP and a mathematical low-N diode with default thermal EG causing overflow at100C. v2 forces gate0 before pulse and uses temperature-neutral clamp EG0/XTI0. Vendor model unchanged.','timeout_s':30})
 for temp in [25,100]:
  for ns in [5,2.5]:
   d=out/f'{temp}C_{ns:g}ns';d.mkdir();shutil.copyfile(vendor,d/'vendor.lib');(d/'.spiceinit').write_text('set ngbehavior=ps\n');s=f'''Gate charge isolated device characterization, no boost workpoint
.include vendor.lib
XQ drain gate 0 SiHP8N50D
ID 0 drain 4
VCL cl 0 400
DCL drain cl CLAMP
VGL gl 0 12
DGL gate gl CLAMP
.model CLAMP D(IS=1p N=.01 RS=.001 EG=0 XTI=0)
VRESET reset 0 PULSE(1 0 1u 1n 1n 100u 200u)
SHOLD gate 0 reset 0 HOLD
.model HOLD SW(RON=.1 ROFF=1G VT=.5 VH=.1)
IG 0 gate PULSE(0 1m 2u 1n 1n 100u 200u)
RGDC gate 0 1G
.temp {temp}
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
set numdgt=15
tran {ns}n 40u 0 {ns}n
wrdata waves.txt v(gate) v(drain) i(vcl)
quit
.endc
.end
''';(d/'circuit.cir').write_text(s,encoding='ascii');r={'temperature_C':temp,'step_s':ns*1e-9};cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
    if (d/'waves.txt').exists():
     a=np.loadtxt(d/'waves.txt',skiprows=1);t=a[:,0];e=edges(t,a[:,1],10,True);r.update(end_s=float(t[-1]),finite=bool(np.isfinite(a).all()))
     if len(e):r.update(time_gate10V_s=float(e[0]),Qg_C=float((e[0]-2e-6-.5e-9)*.001),drain_initial_V=float(np.interp(.9e-6,t,a[:,2])))
    r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=39.999e-6 else 'FAIL'
    r['fit_screen']='PASS_25C_NOMINAL_FIT_ONLY' if temp==25 and r['execution']=='PASS' and 12e-9<=r.get('Qg_C',0)<=18e-9 else 'NOT_PASSED' if temp==25 else 'EXPLORATORY_NOT_DATASHEET_CORNER'
   except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
   rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
