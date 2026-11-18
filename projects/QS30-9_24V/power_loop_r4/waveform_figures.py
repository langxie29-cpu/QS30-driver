"""Deterministic SVG plots of sealed diagnostic samples. Never modifies or resamples raw."""
from r4lib import *
import numpy as np,html
def panel(title,x,y,series,xlabel,ylabel):
 w,h=1080,270;left,top=100,60;pw,ph=900,160;out=[f'<g transform="translate({x},{y})"><text x="20" y="28" font-size="21">{html.escape(title)}</text>'];all_y=np.concatenate([v for _,t,v,col in series]);ymin,ymax=float(all_y.min()),float(all_y.max());pad=max((ymax-ymin)*.07,.01);ymin-=pad;ymax+=pad;xmin=min(float(t.min())for _,t,v,col in series);xmax=max(float(t.max())for _,t,v,col in series)
 for k in range(5):
  py=top+ph*k/4;val=ymax-(ymax-ymin)*k/4;out+=[f'<path d="M {left} {py} h {pw}" stroke="#ddd"/><text x="10" y="{py+5}" font-size="14">{val:.4g}</text>']
 for label,t,v,col in series:
  pts=' '.join(f'{left+(float(a)-xmin)/(xmax-xmin)*pw:.2f},{top+(ymax-float(b))/(ymax-ymin)*ph:.2f}'for a,b in zip(t,v));out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.5"/>')
 out.append(f'<text x="{left}" y="245" font-size="15">{html.escape(xlabel)} [{xmin:.4g}, {xmax:.4g}] / {html.escape(ylabel)}</text>')
 for i,(label,t,v,col)in enumerate(series):out.append(f'<text x="{600+i*210}" y="42" fill="{col}" font-size="14">{html.escape(label)}</text>')
 out.append('</g>');return ''.join(out)
def main():
 s=[]
 for name,col in [('sic_1ns','#1263a0'),('sic_0p5ns','#b23e24')]:
  p=next((HERE/'experiments').glob(name+'_*'));c=native(p/'circuit.raw');w=(c['time']>=.99e-6)&(c['time']<=1.1e-6);s.append((name,c['time'][w]*1e6,c['i(drec)'][w],col))
 body=panel('SiC rectifier terminal current: matched precharged cell, NOT cold start',0,60,s,'time (us)','I(DREC) (A)');s=[]
 for name,col in [('energy47_after_R','#b23e24'),('energy47_before_R','#1263a0')]:
  p=next((HERE/'experiments').glob(name+'_*'));c=native(p/'circuit.raw');s.append((name,c['time']*1e6,c['i(lpower)'],col))
 body+=panel('47uF capacitor location: source stays on; 135uH linear L, no HV COUT',0,350,s,'time (us)','I(LPOWER) (A)')
 dest=HERE/'evidence/figures';dest.mkdir(exist_ok=True);(dest/'diagnostic_waveforms.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="660" viewBox="0 0 1100 660"><rect width="1100" height="660" fill="white"/><g font-family="Arial" fill="#152e43"><text x="20" y="33" font-size="24">QS30-9 R4: sealed native waveform evidence / overall HOLD</text>'+body+'</g></svg>',encoding='utf8')
 dump(dest/'receipt.json',dict(utc=utc(),source='Sealed original native.raw samples, every saved diagnostic point plotted',smoothing=False,scope='Figures for local comparison only; measurements/SHA/preregister remain authority'))
if __name__=='__main__':main()
