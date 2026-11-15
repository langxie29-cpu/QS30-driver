"""Download primary documents into this isolated project; retain hashes/failures."""
from pathlib import Path
import concurrent.futures, hashlib, json, subprocess, urllib.request
ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
 'TPS2660':'https://www.ti.com/lit/ds/symlink/tps2660.pdf',
 'LMR51610':'https://www.ti.com/lit/ds/symlink/lmr51610.pdf',
 'TPS2116':'https://www.ti.com/lit/ds/symlink/tps2116.pdf',
 'TPS62162':'https://www.ti.com/lit/ds/symlink/tps62162.pdf',
 'UCC28C43':'https://www.ti.com/lit/ds/symlink/ucc28c43.pdf',
 'STP9NK50Z':'https://www.st.com/resource/en/datasheet/stp9nk50z.pdf',
 'US1':'https://www.vishay.com/docs/88768/us1_test_dcicons.pdf',
 'MSS1260':'https://www.coilcraft.com/getmedia/febefb9b-60f9-4a2c-8525-9c396f34e363/mss1260.pdf',
 'GST40A':'https://www.meanwell.com/Upload/PDF/GST40A/GST40A-SPEC.PDF',
 'HV5622':'https://ww1.microchip.com/downloads/en/DeviceDoc/20005854A.pdf',
 'SMBJ':'https://www.vishay.com/docs/88392/smbj.pdf',
 'FR':'https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1215.pdf',
 'TPS22810':'https://www.ti.com/lit/ds/symlink/tps22810.pdf',
 'TNPW':'https://www.vishay.com/docs/28758/tnpw_e3.pdf',
 'ECQE_primary_note':'https://api.pim.na.industrial.panasonic.com/file_stream/main/fileversion/4042',
}
def fetch(item):
 name,url=item; p=ROOT/'sources'/f'{name}.pdf'
 r=dict(id=name,url=url,retrieved_date='2026-11-14',status='FAILED')
 try:
  if not p.exists():
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   data=urllib.request.urlopen(req,timeout=35).read()
   if not data.startswith(b'%PDF'): raise ValueError('Response is not PDF')
   p.write_bytes(data)
  r.update(status='DOWNLOADED',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
  exe=ROOT.parents[1]/'tools/PortableGit/ucrt64/bin/pdftotext.exe'
  result=subprocess.run([str(exe),'-layout',str(p),str(p.with_suffix('.txt'))],capture_output=True)
  r['text_extract_rc']=result.returncode
 except Exception as e: r['error']=str(e)
 return r
if __name__=='__main__':
 (ROOT/'sources').mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(fetch,SOURCES.items()))
 (ROOT/'sources/manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps([{k:v for k,v in r.items() if k in ('id','status','error')} for r in rows],indent=2))
