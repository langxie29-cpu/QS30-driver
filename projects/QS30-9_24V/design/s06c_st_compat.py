"""Controlled ST-model compatibility experiments; no device parameter edits."""
from pathlib import Path
import difflib,hashlib,json,re,shutil,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'sim/s06c_st_compat_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');src=ROOT/'sim/s06b_device_cells_v1/ST_gate_ideal_OP';rows=[]
 pre={'scope':'ST exact25C isolated transistor195V resistor bias, no boost workpoint','criteria':'rc0, finite40us native endpoint, no abort/error; maxstep2/1ns; no tolerance relaxation','equivalence':'E3 POLY(2) x,y coefficients0,0,0,0,0.0527 =0.0527*x*y. E1/E2 unity VCVS can be nativeB voltage followers. Same nodes and all original numerical device parameters. Translations require validation; not automatically qualified.','variants':['original','native_POLY','native_E123','trap_original','shared46_original'],'timeout_s':30};dump(out/'preregister.json',pre)
 for variant in pre['variants']:
  for ns in [2,1]:
   d=out/f'{variant}_{ns}ns';d.mkdir();original=(src/'st.lib').read_bytes();shutil.copyfile(src/'st.lib',d/'original_vendor.lib');shutil.copyfile(src/'diode.lib',d/'diode.lib');shutil.copyfile(src/'.spiceinit',d/'.spiceinit');st=original.decode('latin1')
   if variant in ['native_POLY','native_E123']:
    st,n=re.subn(r'^E3\s+8\s+13\s+POLY\(2\).*$', 'BE3 8 13 V={0.0527*V(6,8)*V(6,12)}',st,flags=re.M);assert n==1
   if variant=='native_E123':
    st,n=re.subn(r'^E1\s+10\s+5\s+101\s+0\s+1\s*$', 'BE1 10 5 V={V(101)}',st,flags=re.M);assert n==1
    st,n=re.subn(r'^E2\s+11\s+5\s+102\s+0\s+1\s*$', 'BE2 11 5 V={V(102)}',st,flags=re.M);assert n==1
   (d/'st.lib').write_bytes(st.encode('latin1'));(d/'adaptation.diff').write_text(''.join(difflib.unified_diff(original.decode('latin1').splitlines(True),st.splitlines(True),fromfile='original_vendor.lib',tofile='st.lib')),encoding='utf8')
   s=(src/'circuit.cir').read_text();s=s.replace('tran 2n 40u 0 2n',f'tran {ns}n 40u 0 {ns}n')
   if variant=='trap_original':s=s.replace('method=gear','method=trap')
   if variant=='shared46_original':s=s.replace('\nquit\n','\necho unit_finished\n')
   (d/'circuit.cir').write_text(s,encoding='ascii');cmd=([sys.executable,str(ROOT/'design/s06b_shared_worker.py'),str(d)] if variant=='shared46_original' else [str(REPO/'tools/ngspice47/Spice64/bin/ngspice_con.exe'),'-b','-o','ngspice.log','circuit.cir']);r={'variant':variant,'step_s':ns*1e-9,'original_model_sha256':hashlib.sha256(original).hexdigest(),'run_model_sha256':hashlib.sha256((d/'st.lib').read_bytes()).hexdigest()}
   try:
    p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')});log=(d/('shared_engine.log' if variant=='shared46_original' else 'ngspice.log')).read_text(errors='replace');r.update(rc=p.returncode,parsed_error=bool(re.search(r'timestep too small|aborted|(?im:^.*\berror\b)',log)))
    if (d/'waves.txt').exists():
     a=np.loadtxt(d/'waves.txt',skiprows=1);r.update(end_s=float(a[-1,0]),samples=len(a),finite=bool(np.isfinite(a).all()))
     if a[-1,0]>=39.999e-6:r.update(drain_min_V=float(a[:,2].min()),drain_max_V=float(a[:,2].max()),gate_current_peak_A=float(abs(a[:,3]).max()))
    r['execution']='PASS' if r['rc']==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=39.999e-6 else 'FAIL'
   except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
   rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
