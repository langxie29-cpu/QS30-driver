"""Scientific figures from real raw evidence only; metrics use full saved samples."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import lab
OUT=lab.HERE/'evidence/figures';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2})
def envelope(c,stop,binwidth=1e-4):
 t=c['time'];v=c['v(hv)'];bins=np.arange(0,stop+binwidth*.5,binwidth);i=np.searchsorted(t,bins);lo=[];hi=[];av=[]
 for a,b,aa,bb in zip(i[:-1],i[1:],bins[:-1],bins[1:]):
  if b<=a:lo.append(np.nan);hi.append(np.nan);av.append(np.nan)
  else:lo.append(float(v[a:b].min()));hi.append(float(v[a:b].max()));av.append(lab.stats(c,float(aa),float(bb))['mean'])
 return (bins[:-1]+bins[1:])/2,np.array(lo),np.array(hi),np.array(av)
def core():
 old=lab.native(lab.BASE/'circuit.raw');new=lab.native(lab.HERE/'evidence/principal/filter22R_4p7n_threads1_200ms/circuit.raw')
 fig,axs=plt.subplots(3,1,figsize=(11,11),constrained_layout=True)
 for c,stop,color,label in [(old,.06,'#c95c50','R1: 10 ohm / 1 nF'),(new,.2,'#137f95','R2: 22 ohm / 4.7 nF')]:
  x,lo,hi,av=envelope(c,stop);axs[0].fill_between(x*1000,lo,hi,color=color,alpha=.25);axs[0].plot(x*1000,av,color=color,lw=1.4,label=label)
 axs[0].axhspan(164.9,175.1,color='green',alpha=.08,label='Required mean band');axs[0].set(xlabel='Time (ms)',ylabel='Delivered output (V)',title='Real-controller cold start, COUT initially 0 V; ideal 1 ms input/AUX boundary');axs[0].legend(loc='lower right')
 for c,color,label,Rf in [(old,'#c95c50','R1',10),(new,'#137f95','R2',22)]:
  t=c['time'];k=int(np.argmax(c['v(src)']));m=(t>t[k]-100e-9)&(t<t[k]+150e-9)
  axs[1].plot((t[m]-t[k])*1e9,c['v(src)'][m],color=color,lw=.7,alpha=.4,ls='--',label=label+' shunt voltage')
  axs[1].plot((t[m]-t[k])*1e9,c['v(sense)'][m],color=color,lw=1.5,label=label+' SENSE pin')
 axs[1].axhline(.3,color='black',ls=':',label='SENSE +0.3 V absolute maximum');axs[1].set(xlabel='ns relative to each trace\'s own worst shunt peak (phase aligned)',ylabel='Voltage (V)',title='Filter protects the pin; high shunt-branch transient still exists');axs[1].legend(ncol=2,fontsize=9)
 t=new['time'];v=new['v(hv)'];bins=np.arange(.15,.20000001,50e-6);ix=np.searchsorted(t,bins);cent=(bins[:-1]+bins[1:])/2;lo=[float(v[a:b].min())for a,b in zip(ix[:-1],ix[1:])];hi=[float(v[a:b].max())for a,b in zip(ix[:-1],ix[1:])]
 axs[2].fill_between(cent*1000,lo,hi,color='#137f95',alpha=.6);axs[2].set(xlabel='Time (ms)',ylabel='Delivered output (V)',title='Entire predefined 150-200 ms window: 169.985579 V mean, 0.091150 Vpp');axs[2].set_ylim(169.96,170.08)
 axs[2].ticklabel_format(axis='y',style='plain',useOffset=False)
 fig.savefig(OUT/'nominal_and_sense.png',dpi=150);plt.close(fig)
def local():
 c=lab.native(lab.HERE/'evidence/principal/minimum_energy_refine/5ps/circuit.raw');t=c['time'];m=(t>=1.02e-6)&(t<=1.10e-6);x=(t[m]-1.02e-6)*1e9
 fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True,constrained_layout=True)
 for key,label in [('i(lpower)','Inductor'),('i(drec)','Rectifier (negative = recovery)'),('i(rsrc)','Shunt'),('i(vqs)','MOS source package port')]:axs[0].plot(x,c[key][m],label=label,lw=1)
 axs[0].set(ylabel='Current (A)',title='Minimum original power cell, finite 20 ns drive edge; 5 ps maximum step');axs[0].legend(ncol=2)
 axs[1].plot(x,c['v(drain)'][m]-c['v(src)'][m],label='MOS external package VDS',lw=1)
 axs[1].plot(x,c['v(q:13)'][m]-c['v(q:9)'][m],label='MOS intrinsic VDS',lw=1)
 axs[1].plot(x,c['v(q:12)'][m]-c['v(src)'][m],label='Source package inductor voltage',lw=1)
 axs[1].set(xlabel='Time from 1.02 us (ns)',ylabel='Voltage (V)',title='Large package excursion is not the intrinsic MOS voltage');axs[1].legend()
 fig.savefig(OUT/'local_current_paths.png',dpi=150);plt.close(fig)
def startup():
 fig,axs=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
 for kind,label,color in [('uncontrolled','1 us input, uncontrolled','#c95c50'),('precharge','Series 33 ohm -5%','#137f95'),('slew_corrected_7p962ms','7.962 ms assumed source slew','#809b36')]:
  c=lab.native(lab.HERE/'evidence/principal/startup_bounds'/kind/'circuit.raw');t=c['time'];i=c['i(lpower)'];m=t<=.0006
  axs[0].plot(t[m]*1e6,i[m],label=label,color=color,lw=1);axs[1].plot(t[::100]*1000,i[::100],label=label,color=color,lw=1)
 axs[0].axhline(3.1,color='black',ls=':',label='25 C 10% L-drop screen, NOT a hot current rating');axs[0].set(xlabel='Time (us)',ylabel='Inductor current (A)',title='Worst fixed passive corner: 26.4 V / 24.36 uF / 135 uH');axs[0].legend(fontsize=8)
 axs[1].set(xlabel='Time (ms)',ylabel='Inductor current (A)',ylim=(-.03,.9),title='PWM inhibited; bypass and actual eFuse are not modeled');axs[1].axhline(26.4/31.35,color='black',ls=':',label='Vmax / Rmin bound');axs[1].legend(fontsize=8)
 fig.savefig(OUT/'passive_startup_bounds.png',dpi=150);plt.close(fig)
if __name__=='__main__':core();local();startup();print(OUT)
