"""Independent installed ngspice build comparison; no solver tolerance loosening."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(run,shared_only=False):
 if not re.fullmatch(r'[a-zA-Z0-9_-]+',run):raise ValueError('invalid run name')
 dest=ROOT/'sim'/run;dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py');shutil.copyfile(ROOT/'design/s06b_shared_worker.py',dest/'shared_worker_snapshot.py')
 pre={'date':'2026-11-15','scope':'same electrical netlist on CLI SPARSE/KLU and installed KiCad shared build; only control quit removal in DLL case','criteria':'finite native endpoint and no aborted/error/timestep-too-small; same .001/1n/1u tolerances. Alternative build success is not electrical qualification.','timeout_s':40};dump(dest/'preregister.json',pre)
 cases=[('shared_driver',ROOT/'sim/s06_driver_unit_v1/11.4_switch_1ns','shared',100e-6),('shared_integrated',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns','shared',500e-6),('klu_integrated',ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns','klu',500e-6)]
 if shared_only:cases=[x for x in cases if x[2]=='shared']
 rows=[]
 for name,src,engine,stop in cases:
  d=dest/name;d.mkdir()
  for p in src.iterdir():
   if p.is_file() and (p.suffix.lower()=='.lib' or p.name in ['circuit.cir','.spiceinit']):shutil.copyfile(p,d/p.name)
  p=d/'circuit.cir';s=p.read_text(encoding='ascii')
  if engine=='shared':
   s=s.replace('\nquit\n','\necho unit_finished\n');cmd=[sys.executable,str(ROOT/'design/s06b_shared_worker.py'),str(d)]
  else:
   s=s.replace('set noaskquit','set noaskquit\nset klu');cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']
  p.write_text(s,encoding='ascii')
  try:
   r=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')})
   logfile=d/('shared_engine.log' if engine=='shared' else 'ngspice.log');log=logfile.read_text(errors='replace') if logfile.exists() else ''
   row={'case':name,'engine':engine,'rc':r.returncode,'parsed_error':bool(re.search(r'timestep too small|aborted|(?im:^.*\berror\b)',log))}
   if (d/'waves.txt').exists():
    a=np.loadtxt(d/'waves.txt',skiprows=1);row.update(end_s=float(a[-1,0]),samples=len(a),finite=bool(np.isfinite(a).all()))
   row['execution']='PASS' if r.returncode==0 and not row['parsed_error'] and row.get('finite') and row.get('end_s',0)>=stop*(1-1e-6) else 'FAIL'
  except Exception as e:row={'case':name,'execution':'FAIL','error':str(e)};dump(d/'exception.json',row)
  rows.append(row);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--shared-only',action='store_true');a=p.parse_args();main(a.run,a.shared_only)
