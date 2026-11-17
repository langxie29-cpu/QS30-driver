"""Execute both actual native solvers against a known RC analytical result."""
from pathlib import Path
import os,subprocess,json,hashlib,concurrent.futures,math
from local_probe import HERE,LT,NG
from waveform_review import read_ascii

def case(name,exe):
    d=HERE/'evidence/toolchain_smoke'/name
    d.mkdir(parents=True,exist_ok=False)
    net='Native solver RC check, not HV qualification\nV1 in 0 1\nR1 in out 1k\nC1 out 0 1n IC=0\n'
    if name=='ltspice':net+='.tran .5n 1u 0 .5n uic\n.save V(out)\n.end\n'
    else:net+='.control\ntran .5n 1u uic\nset wr_singlescale\nset wr_vecnames\nwrdata waves.txt v(out)\nquit\n.endc\n.end\n'
    (d/'circuit.cir').write_text(net,encoding='ascii',newline='\n')
    env=dict(os.environ)
    for key,sub in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
        env[key]=str((d/sub).resolve());Path(env[key]).mkdir()
    argv=[str(exe),'-b']+(['-ascii'] if name=='ltspice' else ['-o','run.log'])+[str((d/'circuit.cir').resolve())]
    p=subprocess.run(argv,cwd=d,env=env,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    (d/'stdout.bin').write_bytes(p.stdout);(d/'stderr.bin').write_bytes(p.stderr)
    if name=='ltspice':c=read_ascii(d/'circuit.raw');t,v=c['time'],c['v(out)']
    else:
        lines=(d/'waves.txt').read_text().splitlines()[1:]
        a=[[float(x) for x in l.split()] for l in lines if l.strip()];t,v=[r[0] for r in a],[r[1] for r in a]
    expected=1-math.exp(-1)
    r=dict(solver=name,argv=argv,rc=p.returncode,exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
           endpoint_s=t[-1],endpoint_V=v[-1],analytic_V=expected,error_V=v[-1]-expected,
           status='LIMITED_PASS' if p.returncode==0 and abs(t[-1]-1e-6)<1e-12 and abs(v[-1]-expected)<1e-3 else 'SOLVER_FAIL',
           scope='RC toolchain only; no controller/HV/power-stage qualification')
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    return r

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        print(json.dumps(list(pool.map(lambda a:case(*a),[('ltspice',LT),('ngspice',NG)])),indent=2))
