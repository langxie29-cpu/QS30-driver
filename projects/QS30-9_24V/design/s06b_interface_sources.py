"""Archive additional primary interface evidence; never overwrite an old source."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
ITEMS={'VOS618A': 'https://www.vishay.com/docs/83465/vos618a.pdf','TPS2660_fault_handling':'https://www.ti.com/lit/an/slva934a/slva934a.pdf','FT231X':'https://www.ftdichip.com/wp-content/uploads/2025/06/DS_FT231X.pdf','MSS1583_current':'https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf'}
def get(k,u):
 d=ROOT/'sources/sprint06b'/k;d.mkdir(exist_ok=False);r={'source':u}
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'});res=urllib.request.urlopen(req,timeout=25);b=res.read();r.update(final_url=res.url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest());(d/'original.pdf').write_bytes(b)
  if b.startswith(b'%PDF'):
   p=subprocess.run([str(REPO/'tools/PortableGit/ucrt64/bin/pdftotext.exe'),'-layout',str(d/'original.pdf'),str(d/'original.txt')],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);r['text_extract_rc']=p.returncode
  else:r['error']='not PDF'
 except Exception as e:r['error']=str(e)
 (d/'source.json').write_text(json.dumps(r,indent=2)+'\n');return k,r
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:r=dict(pool.map(lambda x:get(*x),ITEMS.items()))
 (ROOT/'sources/sprint06b/interface_sources.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
