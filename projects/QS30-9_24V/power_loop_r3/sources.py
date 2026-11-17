from r3lib import *
import urllib.request,fitz
urls={
 'TPS2660':'https://www.ti.com/lit/ds/symlink/tps2660.pdf',
 'STP9NK50Z':'https://www.st.com/resource/en/datasheet/stp9nk50z.pdf',
 'US1':'https://www.vishay.com/docs/88747/us1a.pdf',
 'LT3757A':'https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf',
 'HV5622':'https://www.microchip.com/content/dam/mchp/documents/OTH/ProductDocuments/DataSheets/20005854A.pdf',
 'WSL':'https://www.vishay.com/docs/30100/wsl.pdf',
 'MSS1583':'https://www.coilcraft.com/getmedia/fbfe8ea7-f5d8-4484-859e-2285f427326d/mss1583.pdf'}
records=[]
for name,url in urls.items():
 p=HERE/'.local/sources'/f'{name}.pdf';p.parent.mkdir(parents=True,exist_ok=True)
 try:
  data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read();p.write_bytes(data)
  d=fitz.open(p); text='\n'.join(f'\n--- PAGE {i+1} ---\n'+page.get_text() for i,page in enumerate(d))
  # Text extracts remain local to avoid republishing entire copyright documents.
  p.with_suffix('.txt').write_text(text,encoding='utf8')
  pages={'TPS2660':[5,6,7,8,20,21,22,23,24,25,26,29,30,31],'STP9NK50Z':[1,4],'US1':[0],'LT3757A':[5,8,9,10],'WSL':[0],'MSS1583':[0],'HV5622':[2]}.get(name,[])
  for i in pages:
   if i<len(d):d[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(str(p.parent/f'{name}_p{i+1}.png'))
  records.append(dict(name=name,url=url,sha256=sha(p),bytes=len(data),pages=len(d),status='DOWNLOADED',local_path=str(p)))
 except Exception as ex:records.append(dict(name=name,url=url,status='EXECUTION_FAIL',error=str(ex)))
dump(HERE/'evidence/source_register.json',records)
print(json.dumps(records,ensure_ascii=False))
