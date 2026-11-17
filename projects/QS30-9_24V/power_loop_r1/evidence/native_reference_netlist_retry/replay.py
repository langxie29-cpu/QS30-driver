from pathlib import Path
import os,sys,subprocess,json,time,hashlib
HERE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
from local_probe import LT
from waveform_review import read_ascii,stats
d=Path(__file__).resolve().parent
lib=HERE/'.local/native_reference_profile/LTspice/lib/sub'
cmd=[str(LT),'-b','-ascii',str(d/'LT3757A.net'),'-I'+str(lib)]
r={'argv':cmd,'scope':'Unmodified vendor ASC, native-generated NET, native solver;12V->24V reference only','timeout_s':60}
start=time.monotonic()
try:
 p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 (d/'run_stdout.bin').write_bytes(p.stdout);(d/'run_stderr.bin').write_bytes(p.stderr)
 r.update(rc=p.returncode,elapsed_s=time.monotonic()-start)
 if (d/'LT3757A.raw').exists():
  c=read_ascii(d/'LT3757A.raw');t=c['time'];v=c['v(out)']
  r.update(endpoint_s=t[-1],initial_V=v[0],peak_V=max(v),steady_V=stats(t,v,.0012,.0015))
  r['classification']='LIMITED_PASS' if p.returncode==0 and t[-1]>=.0015 and 23<=r['steady_V']['mean']<=25 else 'ELECTRICAL_FAIL'
 else:r.update(classification='EXECUTION_FAIL',reason='No raw')
except subprocess.TimeoutExpired:r.update(rc=None,classification='EXECUTION_FAIL',reason='60s timeout',elapsed_s=time.monotonic()-start)
except Exception as e:r.update(classification='INCONCLUSIVE',reason=repr(e))
(d/'metrics.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps(r,indent=2))
