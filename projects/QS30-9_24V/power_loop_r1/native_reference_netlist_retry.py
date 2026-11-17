"""Minimal CLI correction, keep failed direct-ASC replay untouched."""
from pathlib import Path
import os,subprocess,time,json,shutil
from local_probe import HERE,LT

if __name__=='__main__':
    d=HERE/'evidence/native_reference_netlist_retry'
    d.mkdir(parents=True,exist_ok=False)
    shutil.copy2(HERE/'evidence/native_reference_independent/LT3757A.asc',d/'LT3757A.asc')
    local=HERE/'.local/native_reference_profile/LTspice'
    env=dict(os.environ,APPDATA=str(local.parent),LOCALAPPDATA=str(local.parent))
    cmd=[str(LT),'-netlist',str((d/'LT3757A.asc').resolve()),'-I'+str((local/'lib/sym').resolve())]
    r=dict(argv=cmd,timeout_s=15,scope='Only native schematic-to-netlist, original ASC unchanged')
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=d,env=env,capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(rc=p.returncode,elapsed_s=time.monotonic()-start)
        (d/'stdout.bin').write_bytes(p.stdout);(d/'stderr.bin').write_bytes(p.stderr)
    except subprocess.TimeoutExpired:r.update(rc=None,classification='EXECUTION_FAIL',reason='15s native netlist timeout',elapsed_s=time.monotonic()-start)
    r['netlist_created']=(d/'LT3757A.net').is_file()
    (d/'command.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r,indent=2))
