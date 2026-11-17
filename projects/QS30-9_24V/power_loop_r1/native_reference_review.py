"""Independent exact ADI bundled reference replay, not a 170V validation."""
from pathlib import Path
import zipfile,os,subprocess,time,json,hashlib
from local_probe import HERE,LT
from waveform_review import read_ascii,stats

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    d=HERE/'evidence/native_reference_independent'
    d.mkdir(parents=True,exist_ok=False)
    local=HERE/'.local/native_reference_profile/LTspice'
    local.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(LT.parent/'lib.zip') as z:z.extractall(local)
    with zipfile.ZipFile(LT.parent/'examples.zip') as z:
        (d/'LT3757A.asc').write_bytes(z.read('examples/Applications/LT3757A.asc'))
    env=dict(os.environ,APPDATA=str(local.parent),LOCALAPPDATA=str(local.parent))
    cmd=[str(LT),'-b','-ascii',str((d/'LT3757A.asc').resolve())]
    r=dict(argv=cmd,original_asc_sha256=sha(d/'LT3757A.asc'),simulator_sha256=sha(LT),
           model_sha256=sha(local/'lib/sub/LT3757A.sub'),scope='Exact unmodified 12V->24V ADI reference, NOT QS30 170V')
    (d/'preregister.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=d,env=env,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(rc=p.returncode,elapsed_s=time.monotonic()-start)
        (d/'stdout.bin').write_bytes(p.stdout);(d/'stderr.bin').write_bytes(p.stderr)
        if (d/'LT3757A.raw').exists():
            c=read_ascii(d/'LT3757A.raw'); t=c['time'];v=c['v(out)']
            r.update(endpoint_s=t[-1],initial_V=v[0],peak_V=max(v),steady_V=stats(t,v,.0012,.0015))
            r['classification']='LIMITED_PASS' if p.returncode==0 and t[-1]>=.0015 and 23<=r['steady_V']['mean']<=25 else 'ELECTRICAL_FAIL'
        else:r.update(classification='EXECUTION_FAIL',reason='No native raw')
    except subprocess.TimeoutExpired as e:
        r.update(rc=None,classification='EXECUTION_FAIL',reason='60s timeout',elapsed_s=time.monotonic()-start)
        (d/'stdout.bin').write_bytes(e.stdout or b'');(d/'stderr.bin').write_bytes(e.stderr or b'')
    except Exception as e:r.update(classification='INCONCLUSIVE',reason=repr(e))
    (d/'metrics.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r,indent=2))
