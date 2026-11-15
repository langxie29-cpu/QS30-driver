"""Isolated exact-device validity cells. No boost or closed-loop workpoint."""
from pathlib import Path
import json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06b_device_cells_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py')
 st=next(p for p in (ROOT/'sources/sprint06b/ST_model_cn/unpacked').rglob('*') if p.is_file())
 cases={
 'ST_gate_ideal_OP':('VBIAS bias 0 195\nRLOAD bias d 200\nVG g 0 PULSE(0 12 20u 100n 100n 5u 10u)\nXQ d g 0 STP9NK50Z','tran 2n 40u 0 2n','v(g) v(d) i(vg) i(vbias)',40e-6),
 'ST_gate_ideal_ramp_UIC':('VBIAS bias 0 PWL(0 0 10u 195 40u 195)\nRLOAD bias d 200\nVG g 0 PULSE(0 12 20u 100n 100n 5u 10u)\nXQ d g 0 STP9NK50Z','tran 2n 40u 0 2n uic','v(g) v(d) i(vg) i(vbias)',40e-6),
 'ST_DC_VGS10_Id3p6':('VG g 0 10\nID 0 d 3.6\nXQ d g 0 STP9NK50Z','op','v(d) v(g)',None),
 'Vishay_US1G_DC1A':('ID 0 a 1\nD1 a 0 US1G','op','v(a)',None),
 'Vishay_US1G_reverse195':('VB a 0 -195\nD1 a 0 US1G','op','i(vb)',None),
 }
 dump(out/'preregister.json',{'scope':'25C exact ST/Vishay isolated cells; .op and transient model validity, not thermal/recovery guarantee','criteria':'finite output, rc0, no abort/error; transient must reach native endpoint; no altered vendor parameters','cases':list(cases),'timeout_s':30})
 rows=[]
 for name,(body,analysis,vectors,end) in cases.items():
  d=out/name;d.mkdir();shutil.copyfile(st,d/'st.lib');shutil.copyfile(ROOT/'sources/sprint06b/Vishay_US1G/us1g.txt',d/'diode.lib');(d/'.spiceinit').write_text('set ngbehavior=ps\n')
  s=f'''Exact device isolated cell 25C
.include st.lib
.include diode.lib
{body}
.temp 25
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
  (d/'circuit.cir').write_text(s,encoding='ascii');r={'name':name}
  cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
  try:
   p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
   if (d/'waves.txt').exists():
    a=np.atleast_2d(np.loadtxt(d/'waves.txt',skiprows=1));r.update(finite=bool(np.isfinite(a).all()),last_row=a[-1].tolist(),rows=len(a))
   r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and (end is None or r['last_row'][0]>=end*.99999) else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e))
  rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'qualification':'MODEL_CELLS_ONLY_NOT_07_PASS'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
