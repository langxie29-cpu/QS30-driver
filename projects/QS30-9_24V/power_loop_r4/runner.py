"""Principal-only deterministic native executor, twelve total attempts including failures."""
from r4lib import *
import os,re,subprocess,shutil,time,uuid
def run(case,deck,models,stop,wall,hypothesis,variable,windows,scope):
 ledger=HERE/'evidence/execution_ledger.json'
 records=json.loads(ledger.read_text(encoding='utf8'))['records']if ledger.exists()else[]
 if len(records)>=12:raise RuntimeError('R4 twelve-attempt ceiling reached')
 uid=utc().replace(':','').replace('-','')[:15]+'_'+uuid.uuid4().hex[:8]
 p=HERE/'experiments'/(case+'_'+uid);p.mkdir(parents=True,exist_ok=False)
 hashes={}
 for name,source in models.items():shutil.copy2(source,p/name);hashes[name]=sha(p/name)
 (p/'circuit.cir').write_text(deck,encoding='ascii')
 reg=dict(utc=utc(),case=case,hypothesis=hypothesis,unique_main_variable=variable,netlist_sha256=sha(p/'circuit.cir'),model_hashes=hashes,solver='LTspice 24.0.12.0 Windows Normal',solver_exe_sha256=sha(LT),stop_s=stop,max_runtime_s=wall,options=re.findall(r'(?m)^\.options.*',deck),tran=re.findall(r'(?m)^\.tran.*',deck),analysis_windows_s=windows,raw=str(p/'circuit.raw'),log=str(p/'circuit.log'),scope=scope,limits=dict(mean_V=[164.9,175.1],raw_ripple_Vpp=1,normal_peak_V=180,startup_s=1,recovery_s=.1,fault_peak_V=195,SENSE_abs_V=.3),diagnostic_acceptance='<=5% peak change in matched half-step cell; <=1mA local KCL for directly observed ports. Does not grant device/SOA/system qualification',stop_conditions=['wall budget','solver failure','registered endpoint'],estimated_raw_bytes='UNKNOWN; all bytes retained',CPU_and_peak_RAM='Not instrumented; UNKNOWN')
 dump(p/'preregister.json',reg)
 row=dict(case=case,path=str(p.relative_to(HERE)),preregister_sha256=sha(p/'preregister.json'),status='STARTED');records.append(row);dump(ledger,dict(max_native=12,calls=len(records),records=records))
 env=dict(os.environ)
 for var,folder in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
  (p/folder).mkdir();env[var]=str(p/folder)
 argv=[str(LT),'-b',str(p/'circuit.cir')];start=time.monotonic();rc=None
 try:
  proc=subprocess.Popen(argv,cwd=p,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  dump(p/'process.json',dict(pid=proc.pid,argv=argv))
  try:out,err=proc.communicate(timeout=wall);rc=proc.returncode;status='COMPLETED_UNREVIEWED'if rc==0 else'SOLVER_FAIL'
  except subprocess.TimeoutExpired:
   subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);out,err=proc.communicate();status='EXECUTION_FAIL'
 except OSError as e:out=b'';err=str(e).encode();status='EXECUTION_FAIL'
 (p/'stdout.bin').write_bytes(out);(p/'stderr.bin').write_bytes(err)
 endpoint=None;error=None
 if (p/'circuit.raw').exists():
  try:c=native(p/'circuit.raw');endpoint=float(c['time'][-1]);del c
  except Exception as e:error=str(e)
 if rc==0 and(endpoint is None or endpoint<stop-1e-10):status='SOLVER_FAIL'
 result=dict(argv=argv,rc=rc,elapsed_s=time.monotonic()-start,execution_status=status,endpoint_s=endpoint,raw_parse_error=error)
 dump(p/'command.json',result)
 for name,h in hashes.items():assert sha(p/name)==h
 files=[dict(path=str(f.relative_to(p)),bytes=f.stat().st_size,sha256=sha(f))for f in sorted(p.rglob('*'))if f.is_file()and not any(x in f.parts for x in ['appdata','localappdata'])]
 dump(p/'SHA256.json',files)
 row.update(status=status,**result);dump(ledger,dict(max_native=12,calls=len(records),records=records))
 seal=subprocess.run(['pwsh','-NoProfile','-File',str(HERE/'protect.ps1'),'-EvidencePath',str(p)],capture_output=True,text=True,encoding='utf8',errors='replace')
 dump(HERE/'evidence/seals'/(uid+'.json'),dict(path=str(p),rc=seal.returncode,stdout=seal.stdout,stderr=seal.stderr))
 print(json.dumps(dict(case=case,**result)),flush=True);return p,result
