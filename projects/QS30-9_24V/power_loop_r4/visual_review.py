"""Render actual native SVGs for visual inspection; output PNGs are review artifacts."""
from r4lib import *
import fitz
from PIL import Image,ImageDraw
def main():
 r=json.loads((HERE/'EVT01/latest_review.json').read_text());src=HERE/r['run']/'svg';out=HERE/'evidence/visual_review';out.mkdir(exist_ok=True);shots=[]
 for p in sorted(src.glob('*.svg')):
  d=fitz.open(stream=p.read_bytes(),filetype='svg');pix=d[0].get_pixmap(matrix=fitz.Matrix(2,2));dest=out/(p.stem+'.png');pix.save(dest);shots.append(dict(source=str(p.relative_to(HERE)),source_sha256=sha(p),PNG=str(dest.relative_to(HERE)),PNG_sha256=sha(dest),width=pix.width,height=pix.height))
 canvas=Image.new('RGB',(1600,((len(shots)+1)//2)*620),'#dddddd');draw=ImageDraw.Draw(canvas)
 for i,s in enumerate(shots):
  im=Image.open(HERE/s['PNG']).convert('RGB');im.thumbnail((780,580));x=10+(i%2)*800;y=30+(i//2)*620;canvas.paste(im,(x,y));draw.text((x,y-20),Path(s['PNG']).stem,fill='black')
 canvas.save(out/'contact_sheet.png');dump(out/'render_receipt.json',dict(utc=utc(),actual_native_run=r['run'],pages=shots,manual_visual_review='PENDING until principal sees rendered pages; rendering success is not signoff'))
 print(json.dumps(dict(pages=len(shots),contact_sheet=str(out/'contact_sheet.png'))))
if __name__=='__main__':main()
