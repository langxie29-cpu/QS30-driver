"""Independent official LTspice batch comparison, local extraction and ini only."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'toolchain/ltspice26/extracted/LTspice.exe'
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def readtext(p):
 b=p.read_bytes();return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-16le' if len(b)>1 and b[1]==0 else 'utf8',errors='replace')
def raw_ascii(p):
 s=readtext(p);head,body=s.split('Values:',1);n=int(re.search(r'No\. Variables:\s*(\d+)',head).group(1));nv=int(re.search(r'No\. Points:\s*(\d+)',head).group(1));vl=head.split('Variables:',1)[1];names=[x.split()[1] for x in vl.splitlines() if x.strip()];lines=[x.strip() for x in body.splitlines() if x.strip()];a=[]
 for k in range(nv):
  first=lines[k*n].split();assert int(first[0])==k;a.append([float(first[1])]+[float(lines[k*n+j]) for j in range(1,n)])
 return names,np.array(a)
def main():
 out=ROOT/'sim/s06c_lt_compare_v1';out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/'runner_snapshot.py');cases=[]
 for ns in [2,1]:cases.append((f'ST_{ns}ns',ROOT/'sim/s06c_st_compat_v1'/f'original_{ns}ns',['V(g)','V(d)','I(VG)','I(VBIAS)'],40e-6))
 for temp in [25,100]:
  for ns in [5,2.5]:cases.append((f'Vishay_Qg_{temp}C_{ns:g}ns',ROOT/'sim/s06c_gate_charge_v3'/f'{temp}C_{ns:g}ns',['V(gate)','V(drain)','I(VCL)'],40e-6))
 dump(out/'preregister.json',{'scope':'same exact original model and electrical fixture; remove ngspice.control/wrdata/quit, use identical .tran and saved quantities; same .001/1n/1u tolerances. Official signed MSI administratively extracted, not system installed. Per-case local.ini; ASCII raw. No output precharge/boost.','exe':str(EXE),'exe_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'criteria':'rc0, no failure, finite native endpoint;25C Qg fit15nC+/-20percent, half-step1percent. Compare to ngspice before approving translations.','timeout_s':30});rows=[]
 for name,src,vectors,stop in cases:
  d=out/name;d.mkdir()
  for p in src.iterdir():
   if p.suffix.lower()=='.lib':shutil.copyfile(p,d/p.name)
  s=(src/'circuit.cir').read_text();tran=re.search(r'(?m)^tran\s+(.+)$',s).group(1);s=re.sub(r'(?s)\.control.*?\.endc','',s);s=re.sub(r'(?m)^\.end\s*$',f'.tran {tran}\n.save '+ ' '.join(vectors)+'\n.options plotwinsize=0 numdgt=15\n.end',s);(d/'circuit.cir').write_text(s,encoding='ascii');cmd=[str(EXE),'-b','-run','-ascii','-ini',str(d/'local.ini'),str(d/'circuit.cir')];r={'name':name}
  try:
   p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW);dump(d/'command.json',{'argv':cmd,'rc':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')});log=readtext(d/'circuit.log') if (d/'circuit.log').exists() else '';r.update(rc=p.returncode,parsed_error=bool(re.search(r'time step too small|timestep too small|fatal|(?im:^\s*error)',log)))
   if (d/'circuit.raw').exists():
    names,a=raw_ascii(d/'circuit.raw');dump(d/'wave_columns.json',names);np.savetxt(d/'waves.txt',a,header=' '.join(names),comments='');r.update(finite=bool(np.isfinite(a).all()),end_s=float(a[-1,0]),samples=len(a))
    if 'Qg' in name:
     g=a[:,names.index('V(gate)')];t=a[:,0];idx=np.where((g[:-1]<10)&(g[1:]>=10))[0]
     if len(idx):
      j=idx[0];te=t[j]+(10-g[j])*(t[j+1]-t[j])/(g[j+1]-g[j]);k=(t>=1e-6)&(t<=te);tq=np.r_[1e-6,t[k],te];q=(te-1e-6-.5e-9)*.001-np.trapezoid(np.interp(tq,t,g)/1e6,tq);r.update(Qg_C=float(q),time_gate10V_s=float(te))
   r['execution']='PASS' if p.returncode==0 and not r['parsed_error'] and r.get('finite') and r.get('end_s',0)>=stop*.99999 else 'FAIL'
  except Exception as e:r.update(execution='FAIL',error=str(e));dump(d/'exception.json',r)
  rows.append(r);dump(out/'partial_results.json',rows)
 dump(out/'results.json',{'cases':rows,'24V_07':'NOT_PASSED'});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
