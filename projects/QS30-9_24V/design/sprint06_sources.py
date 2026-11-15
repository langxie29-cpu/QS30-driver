"""Append-only primary source acquisition and S05 input snapshot, not model approval."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
DEST=ROOT/'sources/sprint06'
URLS={
 'UCC28C43_startup':'https://www.ti.com/lit/zip/slum178',
 'UCC28C43_pspice':'https://www.ti.com/lit/zip/slum033',
 'TPS26601_tina':'https://www.ti.com/lit/zip/slvmby4',
 'TPS26601_pspice':'https://www.ti.com/lit/zip/slvmby3',
 'MSS1583':'https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf',
 'TPS3700':'https://www.ti.com/lit/ds/symlink/tps3700.pdf',
 'SN74LVC1G17':'https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf',
 'STP9NK50Z':'https://www.st.com/resource/en/datasheet/stp9nk50z.pdf',
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fetch(item):
 name,url=item;d=DEST/name;d.mkdir()
 r={'id':name,'url':url,'date':'2026-11-14','status':'FAILED','qualification':'NOT_EVALUATED'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=30) as response: data=response.read();r['final_url']=response.url
  ext='.zip' if data.startswith(b'PK') else '.pdf' if data.startswith(b'%PDF') else '.bin'
  p=d/(name+ext);p.write_bytes(data);r.update(bytes=len(data),sha256=sha(p),file=str(p.relative_to(ROOT)))
  if ext=='.zip':
   with zipfile.ZipFile(p) as z:
    for x in z.infolist():
     target=(d/'unpacked'/x.filename).resolve()
     if not target.is_relative_to((d/'unpacked').resolve()):raise ValueError('unsafe ZIP path')
     if not x.is_dir():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(x))
   r['files']=[str(x.relative_to(d)) for x in d.rglob('*') if x.is_file()]
  elif ext=='.pdf':
   exe=REPO/'tools/PortableGit/ucrt64/bin/pdftotext.exe'
   rc=subprocess.run([str(exe),'-layout',str(p),str(p.with_suffix('.txt'))],capture_output=True).returncode;r['text_extract_rc']=rc
  else:raise ValueError('Not a ZIP or PDF response')
  r['status']='DOWNLOADED'
 except Exception as e:r['error']=str(e)
 return r
def main():
 DEST.mkdir(parents=True,exist_ok=False)
 snapshot={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.is_relative_to(DEST)}
 out=ROOT/'docs/sprint06';out.mkdir(exist_ok=False)
 (out/'input_snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n',encoding='utf8')
 (out/'git_status_before.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=REPO))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,URLS.items()))
 (DEST/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
