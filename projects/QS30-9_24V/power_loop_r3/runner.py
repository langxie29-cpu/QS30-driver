"""Principal-only deterministic runner. Never executes worker code. Append-only attempts."""
from r3lib import *
import os,re,shutil,subprocess,time,argparse,uuid
EXPECTED=json.loads((R2/'evidence/principal/filter22R_4p7n_threads1_200ms/preregister.json').read_text())['model_hashes']
def run(case,deck,stop,budget,hypothesis,scope):
 ledger=HERE/'evidence/execution_ledger.json'
 records=json.loads(ledger.read_text())['records'] if ledger.exists() else []
 if len(records)>=16:raise RuntimeError('16 invocation ceiling reached, all failed attempts count')
 uid=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+uuid.uuid4().hex[:8]
 temp=HERE/'experiments'/('pending_'+case+'_'+uid);temp.mkdir(parents=True,exist_ok=False)
 for n,h in EXPECTED.items():
  assert sha(MODELS/n)==h;shutil.copy2(MODELS/n,temp/n)
 (temp/'circuit.cir').write_text(deck,encoding='ascii')
 reg=dict(case=case,run_id=uid,utc=utc(),hypothesis=hypothesis,scope=scope,stop_s=stop,max_runtime_s=budget,estimated_cpu_budget_s=budget,estimated_raw_max_bytes=1500000000,estimated_monetary_cost_USD=0,netlist_sha256=sha(temp/'circuit.cir'),model_hashes=EXPECTED,exe_sha256=sha(LT),options=re.findall(r'(?m)^\.options.*$',deck),tran=re.findall(r'(?m)^\.tran.*$',deck),limits=dict(mean_V=[164.9,175.1],ripple_Vpp=1,normal_peak_V=180,startup_s=1,recovery_s=.1,fault_peak_V=195),stop_conditions=['wall timeout','solver failure','endpoint reached'],qualification_rule='rc0 + complete raw + endpoint are execution checks only; device stress and model credibility evaluated separately')
 reg['analysis_windows_s']=[[.10,.12]] if stop>=.12 else ([[.06,.08]] if stop>=.08 else [])
 reg['cell_event_window_s']=[1.02e-6,1.10e-6] if case.startswith('cell') else None
 dump(temp/'preregister.json',reg)
 rec=dict(case=case,run_id=uid,status='STARTED',path=str(temp.relative_to(HERE)),preregister_sha256=sha(temp/'preregister.json'))
 records.append(rec);dump(ledger,dict(R3_invocations=len(records),R2_historical_invocations=36,max_R3=16,records=records))
 env=dict(os.environ)
 for key,folder in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
  (temp/folder).mkdir();env[key]=str(temp/folder)
 argv=[str(LT),'-b',str(temp/'circuit.cir')];start=time.monotonic();rc=None
 try:
  p=subprocess.Popen(argv,cwd=temp,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  dump(temp/'process.json',dict(pid=p.pid,argv=argv))
  try:out,err=p.communicate(timeout=budget);rc=p.returncode;status='COMPLETED_UNREVIEWED' if rc==0 else 'SOLVER_FAIL'
  except subprocess.TimeoutExpired:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
   out,err=p.communicate();status='EXECUTION_FAIL'
 except OSError as ex:out=b'';err=str(ex).encode();status='EXECUTION_FAIL'
 elapsed=time.monotonic()-start
 (temp/'stdout.txt').write_bytes(out);(temp/'stderr.txt').write_bytes(err)
 endpoint=None;error=None
 if (temp/'circuit.raw').exists():
  try:c=native(temp/'circuit.raw');endpoint=float(c['time'][-1]); del c
  except Exception as ex:error=str(ex)
 if status=='COMPLETED_UNREVIEWED' and (endpoint is None or endpoint<stop-1e-10):status='SOLVER_FAIL'
 result=dict(argv=argv,rc=rc,elapsed_s=elapsed,execution_status=status,endpoint_s=endpoint,raw_parse_error=error)
 dump(temp/'command.json',result)
 manifest=[dict(path=str(p.relative_to(temp)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(temp.rglob('*')) if p.is_file() and not any(x in p.parts for x in ['appdata','localappdata'])]
 dump(temp/'SHA256.json',manifest)
 sealed=temp.with_name(case+'_'+uid);temp.rename(sealed)
 protection=subprocess.run(['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE/'protect.ps1'),'-EvidencePath',str(sealed)],capture_output=True,text=True,encoding='utf8',errors='replace')
 dump(HERE/'evidence/seals'/f'{uid}.json',dict(path=str(sealed),acl_rc=protection.returncode,acl=protection.stdout,error=protection.stderr,manifest_sha256=sha(sealed/'SHA256.json')))
 rec.update(path=str(sealed.relative_to(HERE)),status=status,**result)
 dump(ledger,dict(R3_invocations=len(records),R2_historical_invocations=36,max_R3=16,records=records))
 print(json.dumps(dict(case=case,path=str(sealed),**result)),flush=True)
 return sealed,result
