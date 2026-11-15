"""Isolate controller-only load sensitivity without the external driver model."""
from pathlib import Path
import json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 dest=ROOT/'sim/s06b_port_load_v1';dest.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),dest/'runner_snapshot.py');src=ROOT/'sim/s06_buffered_gate_v1/cs_gate_buffered_5ns'
 dump(dest/'preregister.json',{'date':'2026-11-15','scope':'UCC model alone, exact230k resistive load representing driver model IN+. Capacitive load1p/100p/1n characterize numerical validity; no component approval or closed loop.','stop_s':500e-6,'criteria':'finite native endpoint, no error/abort, unchanged .001/1n/1u tolerances','timeout_s':40})
 rows=[]
 for cap in ['1p','100p','1n']:
  d=dest/cap;d.mkdir();shutil.copyfile(src/'vendor.lib',d/'vendor.lib');shutil.copyfile(src/'.spiceinit',d/'.spiceinit')
  s=(src/'circuit.cir').read_text();s=re.sub(r'(?m)^\.include driver_compat.lib\n|^VINHIBIT.*\n|^XD .*\n|^RGON.*\n|^RGOFF.*\n|^CG .*\n|^RGS.*\n','',s);s=s.replace('COUT out 0 1p',f'COUT out 0 {cap}\nRPORT out 0 230k\nBMON gate 0 V=V(out)');(d/'circuit.cir').write_text(s,encoding='ascii')
  cmd=[str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir'];r={'load_cap':cap}
  try:
   pr=subprocess.run(cmd,cwd=d,capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':pr.returncode,'stdout':pr.stdout.decode(errors='replace'),'stderr':pr.stderr.decode(errors='replace')});log=(d/'ngspice.log').read_text(errors='replace');r.update(rc=pr.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^\s*error)',log)))
   if (d/'waves.txt').exists():
    a=np.loadtxt(d/'waves.txt',skiprows=1);r.update(end_s=float(a[-1,0]),finite=bool(np.isfinite(a).all()))
   r['execution']='PASS' if pr.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=499.99e-6 else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
  rows.append(r);dump(dest/'partial_results.json',rows)
 dump(dest/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
