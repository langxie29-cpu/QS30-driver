"""Pre-publication secret/size/model exclusion audit; never prints credential values."""
from archive import *
import re
def main():
 secrets=[]
 for line in Path('D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml').read_text().splitlines():
  if ':' in line and not line.lstrip().startswith('#'):
   value=line.split(':',1)[1].strip().strip('"\'')
   if len(value)>15:secrets.append(value.encode())
 secrets.append(token().encode())
 files=[];hits=[];large=[];forbidden=[]
 for p in HERE.rglob('*'):
  if not p.is_file() or any(x in p.parts for x in ['.local','appdata','localappdata','__pycache__']):continue
  if p.suffix.lower() in ['.raw','.lib','.sub']:continue
  data=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(data),sha256=sha(p)))
  if any(s and s in data for s in secrets):hits.append(str(p.relative_to(HERE)))
  if len(data)>50*1024*1024:large.append(str(p.relative_to(HERE)))
  if p.suffix.lower() in ['.lib','.sub']:forbidden.append(str(p))
 result=dict(utc=utc(),files=len(files),source_bytes=sum(x['bytes'] for x in files),secret_matches=hits,over50MB_files=large,vendor_model_files_in_candidate_publication=forbidden,scope='R3 publishable small files and native output archives only. Vendor libraries/software, PDF downloads, credentials and raw working bytes excluded via .gitignore. Raw archives hold generated results, not executable vendor models.',status='PASS' if not hits and not large and not forbidden else 'FAIL')
 dump(HERE/'evidence/prepublication_check.json',result);assert result['status']=='PASS';print(json.dumps(result))
 logs=[]
 for p in sorted((HERE/'experiments').glob('*/circuit.log')):
  b=p.read_bytes();enc='utf-16-le' if b.startswith(b'L\x00') else 'utf8';dest=HERE/'evidence/readable_logs'/f'{p.parent.name}.txt';dest.parent.mkdir(exist_ok=True)
  dest.write_text(b.decode(enc,errors='replace'),encoding='utf8');logs.append(dict(original=str(p.relative_to(HERE)),original_sha256=sha(p),readable_copy=str(dest.relative_to(HERE)),encoding=enc))
 dump(HERE/'evidence/readable_logs/index.json',logs)
if __name__=='__main__':main()
