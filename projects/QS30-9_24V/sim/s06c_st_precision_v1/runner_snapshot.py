"""Test whether absolute current resolution masks small internal branch currents."""
from pathlib import Path
import json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06c_st_precision_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');rows=[]
 dump(out/'preregister.json',{'hypothesis':'OP E2 branch current is about195pA, smaller than old1nA absolute current tolerance. Tighten ONLY abstol1n to1p, never loosen; compare original and algebraic translation at2/1/0.5ns. One2ns pass in prior native_E123 failed at1ns, so not qualified.','criteria':'finite40us, rc0,no error; both half steps required before waveform convergence comparison','timeout_s':30})
 for variant in ['original','native_E123']:
  for ns in [2,1,.5]:
   d=out/f'{variant}_{ns:g}ns';d.mkdir();src=ROOT/'sim/s06c_st_compat_v1'/f'{variant}_2ns'
   for f in ['st.lib','diode.lib','.spiceinit','original_vendor.lib','adaptation.diff']:shutil.copyfile(src/f,d/f)
   s=(src/'circuit.cir').read_text().replace('abstol=1n','abstol=1p').replace('tran 2n 40u 0 2n',f'tran {ns:g}n 40u 0 {ns:g}n');(d/'circuit.cir').write_text(s,encoding='ascii');r={'variant':variant,'step_s':ns*1e-9,'abstol_A':1e-12};cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
    if (d/'waves.txt').exists():
     a=np.loadtxt(d/'waves.txt',skiprows=1);r.update(end_s=float(a[-1,0]),finite=bool(np.isfinite(a).all()),samples=len(a))
    r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=39.999e-6 else 'FAIL'
   except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
   rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
