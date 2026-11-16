"""Snapshot/check historical source evidence without changing it. Stdlib only."""
import hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def paths():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    for base in ['projects/QS30-9_24V/docs','projects/QS30-9_24V/config','projects/QS30-9_24V/design','projects/QS30-9_24V/sources']:
        names += [p.relative_to(ROOT).as_posix() for p in (ROOT/base).rglob('*') if p.is_file()]
    return sorted(set(n for n in names if n and '/safety_r1/' not in n and not n.startswith('.github/workflows/qs30-safety')))
if __name__=='__main__':
    target=HERE/'history_snapshot.json'
    if sys.argv[1]=='snapshot':
        if target.exists(): raise SystemExit('snapshot already exists')
        data={n:digest(ROOT/n) for n in paths() if (ROOT/n).is_file()}
        target.write_text(json.dumps({'scope':'All tracked baseline files plus existing 24V docs/config/design/sources; untracked historical simulation raw excluded','files':data},indent=2),encoding='utf8')
        print('snapshot',len(data))
    else:
        data=json.loads(target.read_text(encoding='utf8'))['files']
        bad=[n for n,h in data.items() if not (ROOT/n).is_file() or digest(ROOT/n)!=h]
        result={'checked':len(data),'changed_or_missing':bad,'status':'FAIL' if bad else 'PASS'}
        (HERE/'history_check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result));sys.exit(bool(bad))
