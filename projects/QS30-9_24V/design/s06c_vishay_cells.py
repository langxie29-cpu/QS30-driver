"""Alternative exact vendor MOS model cells before any controller coupling."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06c_vishay_cells_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');vendor=ROOT/'sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB';rows=[]
 dump(out/'preregister.json',{'candidate_mpn':'SiHP8N50D-GE3','model':'SiHP8N50D D G S, original vendor RevB electrical model','vendor_sha256':hashlib.sha256(vendor.read_bytes()).hexdigest(),'scope':'25/100C external-temperature electrical cells, no self-heating or boost startup. Vendor guideline characterizes25-150C,0-15V gate; not guaranteed part corners.','criteria':'rc0,finite native40us,no abort/error; list unsupported model warnings as qualification blockers;2/1ns convergence required','cases':'ideal gate same195V resistor bias as ST; static10V4A at25/100C','timeout_s':30})
 for temp in [25,100]:
  for kind,ns in [('gate',2),('gate',1),('static',0)]:
   d=out/f'{kind}_{temp}C_{ns}ns';d.mkdir();shutil.copyfile(vendor,d/'vendor.lib');(d/'.spiceinit').write_text('set ngbehavior=ps\n')
   body='VBIAS bias 0 195\nRLOAD bias d 200\nVG g 0 PULSE(0 12 20u 100n 100n 5u 10u)' if kind=='gate' else 'VG g 0 10\nID 0 d 4'
   analysis=f'tran {ns}n 40u 0 {ns}n' if kind=='gate' else 'op';vectors='v(g) v(d) i(vg) i(vbias)' if kind=='gate' else 'v(d) v(g)'
   s=f'''Exact Vishay alternate MOS cell, not boost workpoint
.include vendor.lib
{body}
XQ d g 0 SiHP8N50D
.temp {temp}
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
set numdgt=15
{analysis}
wrdata waves.txt {vectors}
quit
.endc
.end
'''
   (d/'circuit.cir').write_text(s,encoding='ascii');r={'kind':kind,'temperature_C':temp,'step_s':ns*1e-9};cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)),model_warnings=[x for x in log.splitlines() if re.search('unrecognized|ignored|unknown parameter',x,re.I)])
    if (d/'waves.txt').exists():
     a=np.atleast_2d(np.loadtxt(d/'waves.txt',skiprows=1));r.update(finite=bool(np.isfinite(a).all()),last_row=a[-1].tolist(),samples=len(a))
     if kind=='gate':r.update(end_s=float(a[-1,0]),drain_min_V=float(a[:,2].min()),drain_max_V=float(a[:,2].max()),gate_current_peak_A=float(abs(a[:,3]).max()))
     else:r['Rds_model_ohm']=float(a[-1,1]/4)
    r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and (kind=='static' or r.get('end_s',0)>=39.999e-6) else 'FAIL'
    r['qualification']='PENDING_STEP_COMPARISON' if r['execution']=='PASS' and not r['model_warnings'] else 'NOT_PASSED'
   except Exception as e:r.update(execution='FAIL',qualification='NOT_PASSED',error=str(e));dump(d/'exception.json',r)
   rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
