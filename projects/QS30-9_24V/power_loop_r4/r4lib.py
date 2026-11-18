from pathlib import Path
import json,hashlib,datetime,sys
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R3=Path('D:/PROJECTS/dsharness/QS30-power-loop-r3/projects/QS30-9_24V/power_loop_r3')
R2=Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
ORIGINAL=Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V')
PY=Path('D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe')
KC=Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
LT=ORIGINAL/'toolchain/ltspice26/extracted/LTspice.exe'
MODELS=ORIGINAL/'sim/s06c_current_cell_v3/ST_AUX12_1ns'
BASELINE='98b6f81927592f0576e7eb4148e97fe2b14eab1c'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
sys.path.insert(0,str(R2))
from lab import native,stats
