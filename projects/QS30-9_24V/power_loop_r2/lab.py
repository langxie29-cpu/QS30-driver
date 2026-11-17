"""R2 native simulation helpers. No acceptance inferred from process completion."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,time
import numpy as np
HERE=Path(__file__).resolve().parent
R1_LOCAL=Path('D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1')
BASE=R1_LOCAL/'evidence/candidate_diagnostic/nominal_24V_gear_resource600'
OLD=Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V')
LT=OLD/'toolchain/ltspice26/extracted/LTspice.exe'
MODEL_SOURCE=OLD/'sim/s06c_current_cell_v3/ST_AUX12_1ns'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def native(path):
 path=Path(path)
 with path.open('rb') as f:b=f.read(131072)
 enc='utf-16-le' if b.startswith(b'T\0') else 'utf-8'
 for suffix in ['Binary:\r\n','Binary:\n']:
  marker=suffix.encode(enc);pos=b.find(marker)
  if pos>=0:break
 if pos<0:raise ValueError('Expected uncompressed native binary raw')
 header=b[:pos].decode(enc);offset=pos+len(marker)
 flags=re.search(r'Flags:\s*([^\r\n]+)',header)[1].lower().split()
 if 'fastaccess' in flags or 'complex' in flags:raise ValueError('Unsupported flags')
 names=[s.split()[1].lower() for s in header.rsplit('Variables:',1)[1].splitlines() if s.strip()]
 n=int(re.search(r'No\. Variables:\s*(\d+)',header)[1]);count=int(re.search(r'No\. Points:\s*(\d+)',header)[1])
 size=path.stat().st_size-offset
 if size==count*n*8:dt=np.dtype([(name,'<f8') for name in names])
 elif size==count*(8+4*(n-1)) and 'double' not in flags:dt=np.dtype([(names[0],'<f8')]+[(name,'<f4') for name in names[1:]])
 else:raise ValueError('Incomplete or unsupported raw size')
 if n!=len(names):raise ValueError('Variable count mismatch')
 arr=np.memmap(path,dtype=dt,mode='r',offset=offset,shape=(count,))
 t=arr[names[0]]
 if not np.isfinite(t).all() or not np.all(np.diff(t)>0):raise ValueError('Nonmonotonic/nonfinite time')
 for name in names[1:]:
  if not np.isfinite(arr[name]).all():raise ValueError('Nonfinite signal: '+name)
 return {name:arr[name] for name in names}
def stats(c,a,b,name='v(hv)'):
 t=c['time'];y=c[name]
 if b<=a:raise ValueError('Empty/reversed analysis window')
 if a<t[0] or b>t[-1]+1e-12:raise ValueError('Window outside complete trace')
 i,j=np.searchsorted(t,[a,b])
 def endpoint(k,x):
  if k==len(t):return y[-1]
  if t[k]==x:return y[k]
  return y[k-1]+(y[k]-y[k-1])*(x-t[k-1])/(t[k]-t[k-1])
 tt=np.r_[a,t[i:j],b];yy=np.r_[endpoint(i,a),y[i:j],endpoint(j,b)]
 return dict(mean=float(np.trapezoid(yy,tt)/(b-a)),minimum=float(yy.min()),maximum=float(yy.max()),pp=float(np.ptp(yy)))
def full(path,stop=.01008,step=2e-7,method='gear'):
 path=Path(path);path.mkdir(parents=True,exist_ok=False)
 for name in ['controller.sub','st.lib','diode.lib','ss14.lib']:shutil.copy2(MODEL_SOURCE/name,path/name)
 s=(BASE/'circuit.cir').read_text(encoding='ascii')
 s=s.replace('method=gear','method='+method)
 s=re.sub(r'(?m)^\.tran .*$',f'.tran {step} {stop} 0 {step} uic',s)
 # Pure observation: no zero-volt probes or modifications inside vendor subcircuits.
 s=s.replace('.save V(hv)', '.save V(out) I(XQ:LD) I(XQ:LS) I(XQ:LG) I(XNEG:ddio) I(XNEG:dgr) I(RSRC) I(RF) I(RGS) I(RNEG) I(RSNUB) I(CSNUB) V(hv)')
 (path/'circuit.cir').write_text(s,encoding='ascii')
 return path
def execute(path,hypothesis,variable,timeout=180):
 path=Path(path).resolve()
 if (path/'preregister.json').exists():raise FileExistsError('Never overwrite a previous experiment')
 # Initial worker deleted two completed NEW attempts; they still consume budget.
 registered=0
 for base,dirs,files in os.walk(HERE):
  dirs[:]=[d for d in dirs if d not in ['.local','appdata','localappdata','sim_profile','__pycache__']]
  registered+=int('preregister.json' in files)
 if registered+2>=36:raise RuntimeError('Combined36 native-attempt cap exhausted (deleted attempts count)')
 s=(path/'circuit.cir').read_text(encoding='ascii')
 models={p.name:sha(p) for p in path.iterdir() if p.suffix.lower() in ['.sub','.lib']}
 base_models=json.loads((BASE/'preregister.json').read_text())['model_hashes']
 if models!=base_models:raise ValueError('Vendor model bytes differ from R1')
 settings=re.search(r'(?m)^\.options .*$',s)[0]
 if 'reltol=.001 abstol=1n vntol=1u' not in settings:raise ValueError('Original tolerances required')
 limits=dict(mean_V=[164.9,175.1],ripple_Vpp=1,normal_peak_V=180,startup_s=1,recovery_s=.1,fault_peak_V=195,sense_abs_V=.3)
 dump(path/'preregister.json',dict(hypothesis=hypothesis,unique_main_variable=variable,netlist_sha256=sha(path/'circuit.cir'),model_hashes=models,solver='LTspice 24.0.12.0 Windows Normal',solver_exe_sha256=sha(LT),tran=re.search(r'(?m)^\.tran .*$',s)[0],options=settings,acceptance=limits,diagnostic_reproducibility='For a matched local cell: peak change <=5%, KCL residual <=1mA. Full startup phase may shift; no claim from same wall time alone.',max_runtime_s=timeout,raw=str(path/'circuit.raw'),log=str(path/'circuit.log'),scope='Research only, 25C linear L; all HOLD remain',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
 env=dict(os.environ)
 for key,rel in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
  (path/rel).mkdir();env[key]=str(path/rel)
 argv=[str(LT),'-b',str(path/'circuit.cir')];start=time.monotonic()
 p=subprocess.Popen(argv,cwd=path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 dump(path/'process.json',dict(pid=p.pid,argv=argv))
 try:
  out,err=p.communicate(timeout=timeout);rc=p.returncode;status='COMPLETED_UNREVIEWED' if rc==0 else 'SOLVER_FAIL'
 except subprocess.TimeoutExpired:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  out,err=p.communicate();rc=None;status='EXECUTION_FAIL'
 (path/'stdout.bin').write_bytes(out);(path/'stderr.bin').write_bytes(err)
 result=dict(argv=argv,rc=rc,elapsed_s=time.monotonic()-start,status=status)
 dump(path/'command.json',result)
 return result
