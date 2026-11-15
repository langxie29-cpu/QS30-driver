"""Additional primary sources, append-only, bounded per-request timeouts."""
from pathlib import Path
import concurrent.futures,hashlib,json,urllib.request,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1];DEST=ROOT/'sources/sprint06b'
URLS={
 'ST_model_cn':'https://www.st.com.cn/resource/en/spice_model/stp9nk50z_spice.zip',
 'ST_pdf_cn':'https://www.st.com.cn/resource/en/datasheet/stp9nk50z.pdf',
 'Diodes_US1G':'https://www.diodes.com/spice/download/722/US1G.spice.txt',
 'Coilcraft_product':'https://www.coilcraft.com/en-us/products/power/high-voltage-inductors/mss-mos-(1)/mss1583/mss1583-154/',
 'ESP32_S3_WROOM':'https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf',
}
def fetch(item):
 n,url=item;r={'name':n,'url':url,'date':'2026-11-15','status':'FAILED'};d=DEST/n;d.mkdir()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=15) as response:data=response.read();r['final_url']=response.url
  ext='.pdf' if data.startswith(b'%PDF') else '.zip' if data.startswith(b'PK') else '.txt' if '.txt' in url else '.html'
  p=d/(n+ext);p.write_bytes(data);r.update(file=str(p.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),status='DOWNLOADED_UNREVIEWED')
  if ext=='.pdf':
   pr=subprocess.run([str(REPO/'tools/PortableGit/ucrt64/bin/pdftotext.exe'),'-layout',str(p),str(p.with_suffix('.txt'))],capture_output=True);r['text_extract_rc']=pr.returncode
  if ext=='.zip':
   with zipfile.ZipFile(p) as z:
    for x in z.infolist():
     target=(d/'unpacked'/x.filename).resolve()
     if not target.is_relative_to((d/'unpacked').resolve()):raise ValueError('unsafe zip path')
     if not x.is_dir():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(x))
 except Exception as e:r['error']=str(e)
 return r
if __name__=='__main__':
 DEST.mkdir(exist_ok=False)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(fetch,URLS.items()))
 (DEST/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(rows,ensure_ascii=False,indent=2))
