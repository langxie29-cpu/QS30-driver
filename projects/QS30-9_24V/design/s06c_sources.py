"""Bounded primary-source discovery for alternate device candidates."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
ITEMS={'STP7N65M2_model_url1':'https://www.st.com.cn/resource/en/spice_model/stp7n65m2.zip','STP7N65M2_model_url2':'https://www.st.com.cn/resource/en/spice_model/stp7n65m2_spice.zip','STP7N65M2_datasheet':'https://www.st.com.cn/resource/en/datasheet/stp7n65m2.pdf','IPP60R360P7_datasheet':'https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipp60r360p7-datasheet-en.pdf'}
def get(item):
 k,u=item;d=ROOT/'sources/sprint06c'/k;d.mkdir(exist_ok=False);r={'url':u,'url_discovery':'ST ZIP path candidates inferred from known vendor resource naming; only successful recognized files count as source evidence'}
 try:
  res=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20);b=res.read();r.update(final_url=res.url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest());ext='.pdf' if b.startswith(b'%PDF') else '.zip' if b.startswith(b'PK') else '.bin';p=d/('original'+ext);p.write_bytes(b)
  if ext=='.pdf':subprocess.run([str(REPO/'tools/PortableGit/ucrt64/bin/pdftotext.exe'),'-layout',str(p),str(d/'original.txt')],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  elif ext=='.zip':
   with zipfile.ZipFile(p) as z:
    for x in z.infolist():
     target=(d/'unpacked'/x.filename).resolve()
     if not target.is_relative_to((d/'unpacked').resolve()):raise ValueError('unsafe ZIP path')
    z.extractall(d/'unpacked')
  else:r['error']='unrecognized file content'
 except Exception as e:r['error']=str(e)
 (d/'source.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return k,r
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rr=dict(pool.map(get,ITEMS.items()))
 (ROOT/'sources/sprint06c/manifest.json').write_text(json.dumps(rr,indent=2)+'\n');print(json.dumps(rr,indent=2))
if __name__=='__main__':main()
