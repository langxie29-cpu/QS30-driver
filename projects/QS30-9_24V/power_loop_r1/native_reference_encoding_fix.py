"""Correct generated-netlist ACP unit bytes; preserve all original vendor bytes."""
from pathlib import Path
import sys,subprocess,time,json,hashlib
from local_probe import HERE,LT
from waveform_review import read_ascii,stats
if __name__=='__main__':
    d=HERE/'evidence/native_reference_encoding_fix';d.mkdir(parents=True,exist_ok=False)
    src=HERE/'evidence/native_reference_netlist_retry/LT3757A.net'
    b=src.read_bytes();(d/'native_original.net').write_bytes(b)
    # ACP936 native netlister emits Greek mu A6CC; native batch parser here reads
    # it as no recognized suffix (10H,47F instead of micro units).
    n=b.count(b'\xa6\xcc');assert n==4,n
    fixed=b.replace(b'\xa6\xcc',b'u')
    (d/'circuit.cir').write_bytes(fixed)
    r=dict(scope='Vendor original ASC values, native-generated netlist with four micro-unit encoding substitutions; model bytes unchanged. NOT byte-unmodified reference netlist.',
           changes={'byte_A6CC_to_ASCII_u':n},original_net_sha256=hashlib.sha256(b).hexdigest(),fixed_net_sha256=hashlib.sha256(fixed).hexdigest())
    cmd=[str(LT),'-b','-ascii',str((d/'circuit.cir').resolve()),'-I'+str((HERE/'.local/native_reference_profile/LTspice/lib/sub').resolve())]
    r['argv']=cmd;r['timeout_s']=60;start=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(rc=p.returncode,elapsed_s=time.monotonic()-start)
        (d/'stdout.bin').write_bytes(p.stdout);(d/'stderr.bin').write_bytes(p.stderr)
        if (d/'circuit.raw').exists():
            c=read_ascii(d/'circuit.raw');t=c['time'];v=c['v(out)']
            r.update(endpoint_s=t[-1],initial_V=v[0],peak_V=max(v),steady_V=stats(t,v,.0012,.0015))
            r['classification']='LIMITED_PASS' if p.returncode==0 and t[-1]>=.0015 and 23<=r['steady_V']['mean']<=25 else 'ELECTRICAL_FAIL'
        else:r.update(classification='EXECUTION_FAIL',reason='No raw')
    except subprocess.TimeoutExpired:r.update(rc=None,classification='EXECUTION_FAIL',reason='60s timeout',elapsed_s=time.monotonic()-start)
    except Exception as e:r.update(classification='INCONCLUSIVE',reason=repr(e))
    (d/'metrics.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r,indent=2))
