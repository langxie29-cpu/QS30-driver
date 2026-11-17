"""Plots ONLY actual native raw data, including clearly labelled partial runs."""
from pathlib import Path
import sys,re,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from waveform_review import read_ascii
HERE=Path(__file__).resolve().parent

def partial(d):
 p=d/'circuit.raw'
 with p.open('rb') as f:b=f.read(10000)
 enc='utf-16-le' if b.startswith(b'T\0') else 'utf8'
 m='Binary:\n'.encode(enc);pos=b.find(m)
 if pos<0:m='Binary:\r\n'.encode(enc);pos=b.find(m)
 s=b[:pos].decode(enc);off=pos+len(m)
 n=int(re.search(r'No\. Variables:\s*(\d+)',s)[1]);count=int(re.search(r'No\. Points:\s*(\d+)',s)[1]);count=min(count,(p.stat().st_size-off)//(8*n))
 names=[l.split()[1].lower() for l in s.rsplit('Variables:',1)[1].splitlines() if l.strip()]
 a=np.memmap(p,dtype='<f8',mode='r',offset=off,shape=(count,n))
 return {name:a[:,i] for i,name in enumerate(names)}

if __name__=='__main__':
 plt.rcParams.update({'font.size':11,'axes.grid':True,'grid.alpha':.2})
 out=HERE/'evidence/figures';out.mkdir(parents=True,exist_ok=True)
 fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for name,label in [('fast_1us','1 us input rise'),('slow_1ms','1 ms input rise')]:
  c=read_ascii(HERE/'evidence/passive_path'/name/'circuit.raw');t=np.array(c['time'])*1e3
  ax[0].plot(t,c['v(hv)'],label=label);ax[1].plot(t,c['i(lpower)'],label=label)
 ax[1].axhline(3.1,color='#bb3333',ls='--',label='25 C linear-L screening: 3.1 A')
 ax[0].set(ylabel='COUT voltage (V)',title='PWM disabled: passive 24 V Boost charging path')
 ax[1].set(ylabel='Inductor current (A)',xlabel='Actual simulation time (ms)')
 for a in ax:a.legend(loc='upper right');a.set_xlim(0,2)
 fig.suptitle('Actual LTspice raw | COUT starts at 0 V | no 170 V result claimed',fontsize=13)
 fig.tight_layout();fig.savefig(out/'passive_path.png',dpi=160);plt.close(fig)

 c=read_ascii(HERE/'evidence/native_reference_encoding_fix/circuit.raw')
 fig,ax=plt.subplots(figsize=(11,4));ax.plot(np.array(c['time'])*1e3,c['v(out)'],color='#146c94')
 ax.axhline(24,color='#555555',ls='--');ax.set(xlabel='Actual simulation time (ms)',ylabel='VOUT (V)',title='ADI 12 V to 24 V reference: encoding-corrected generated netlist')
 ax.text(.98,.08,'Original controller model bytes unchanged\nFour micro-unit suffix bytes normalized to ASCII u\nThis is not the QS30 170 V design',transform=ax.transAxes,ha='right',bbox=dict(facecolor='white',alpha=.9))
 fig.tight_layout();fig.savefig(out/'native_reference_24V.png',dpi=160);plt.close(fig)

 fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for name,label in [('nominal_24V_200ns','Gear'),('nominal_24V_trap_200ns','Trap')]:
  d=HERE/'evidence/candidate_diagnostic'/name
  if not (d/'command.json').exists():continue
  c=partial(d);step=max(1,len(c['time'])//15000);ix=np.arange(0,len(c['time']),step)
  t=c['time'][ix]*1e3
  ax[0].plot(t,c['v(hv)'][ix],label=label+' partial data')
  ax[1].plot(t,c['i(lpower)'][ix],lw=.5,label=label+' sampled trace')
 ax[0].axhline(170,color='#bb3333',ls='--',label='170 V target')
 ax[0].set(ylabel='COUT voltage (V)',title='Real LT3757A + original ST/US1G models: incomplete cold-start attempts')
 ax[1].set(xlabel='Actual simulation time (ms)',ylabel='Inductor current (A)')
 for a in ax:a.legend(loc='best')
 fig.suptitle('TIMEOUT: no steady-state or M2/M3 PASS | plots decimated; metrics use full reviewed data',fontsize=12)
 fig.tight_layout();fig.savefig(out/'cold_start_PARTIAL_TIMEOUT.png',dpi=160);plt.close(fig)
 print(out)
