"""Freeze inherited inputs, without importing historical generators."""
from pathlib import Path
import hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'sim/sprint04'
BASE.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8', errors='replace')

def included(p):
    return not (p.startswith(('sim/sprint04/', 'docs9/electrical_sprint04/', 'design9/sprint04_', 'design9/topology24')))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__ == '__main__':
    dest = BASE / 'baseline.json'
    assert not dest.exists(), 'Refusing to overwrite baseline'
    paths = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')
    hashes = {p: sha(ROOT / p) for p in paths if p and included(p) and (ROOT / p).is_file()}
    data = dict(date='2026-11-14', timezone='Asia/Shanghai', head=git('rev-parse', 'HEAD').strip(),
                branch=git('branch', '--show-current').strip(), status=git('status', '--short'),
                protected_sha256=hashes, authorization='Sprint04 research plus 24V alternative; two delegated agents; no formal circuit edits')
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'inherited-worktree.patch').write_text(git('diff', '--binary'), encoding='utf-8')
    print(f'Frozen {len(hashes)} inherited Git-visible files')
