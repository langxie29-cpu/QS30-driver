"""Bounded official-source retrieval; vendor bytes stay local, register only metadata."""
from r4lib import *
import urllib.request,concurrent.futures,fitz
SOURCES={
 'LM5069':'https://www.ti.com/lit/ds/symlink/lm5069.pdf',
 'LM5164':'https://www.ti.com/lit/ds/symlink/lm5164.pdf',
 'UCC27511':'https://www.ti.com/lit/ds/symlink/ucc27511.pdf',
 'TPS7A16':'https://www.ti.com/lit/ds/symlink/tps7a16.pdf',
 'TLV1704':'https://www.ti.com/lit/ds/symlink/tlv1704.pdf',
 'REF3425':'https://www.ti.com/lit/ds/symlink/ref3425.pdf',
 'SN74HC279':'https://www.ti.com/lit/ds/symlink/sn74hc279.pdf',
 'SN74HCS74':'https://www.ti.com/lit/ds/symlink/sn74hcs74.pdf',
 'TPS3808':'https://www.ti.com/lit/ds/symlink/tps3808.pdf',
 'SN74HCS08':'https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf',
 'SN74HCS14':'https://www.ti.com/lit/ds/symlink/sn74hcs14.pdf',
 'STPSC4H065':'https://www.st.com/resource/en/datasheet/stpsc4h065.pdf',
 'MSS1583':'https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf',
 'C3D04065A':'https://assets.wolfspeed.com/uploads/2023/11/Wolfspeed_C3D04065A_data_sheet.pdf',
 'VO617A':'https://www.vishay.com/docs/83430/vo617a.pdf',
 'NTCLE100':'https://www.vishay.com/docs/29049/ntcle100.pdf'}
def get(item):
 name,url=item;p=HERE/'.local/sources'/f'{name}.pdf';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError('Do not overwrite vendor source attempt')
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45)as r:b=r.read()
  p.write_bytes(b);d=fitz.open(p)
  p.with_suffix('.txt').write_text('\n'.join(f'\n--- PAGE {i+1} ---\n'+page.get_text()for i,page in enumerate(d)),encoding='utf8')
  return dict(name=name,url=url,utc=utc(),sha256=sha(p),bytes=len(b),pages=len(d),local_path=str(p),status='DOWNLOADED')
 except Exception as ex:return dict(name=name,url=url,utc=utc(),status='EXECUTION_FAIL',error=str(ex))
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:rows=list(pool.map(get,SOURCES.items()))
 dump(HERE/'evidence/source_register.json',rows)
 for r in rows:print(json.dumps({k:r[k]for k in ['name','status']if k in r}),flush=True)
