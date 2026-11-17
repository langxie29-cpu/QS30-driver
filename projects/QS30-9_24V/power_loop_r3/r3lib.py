from pathlib import Path
import sys,json,hashlib,datetime
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R2=Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
OLD=Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V')
LT=OLD/'toolchain/ltspice26/extracted/LTspice.exe'
MODELS=OLD/'sim/s06c_current_cell_v3/ST_AUX12_1ns'
sys.path.insert(0,str(R2))
from lab import native,stats
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
