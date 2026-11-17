import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_probe import HERE
from render_evidence import partial
if __name__=='__main__':
 c=partial(HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600');t=c['time']
 ix=np.arange(0,len(t),max(1,len(t)//20000))
 fig,ax=plt.subplots(3,1,figsize=(11,9),sharex=True)
 ax[0].axhspan(164.9,175.1,color='#56b48c',alpha=.15,label='164.9-175.1 V target band')
 ax[0].plot(t[ix]*1e3,c['v(hv)'][ix],color='#146c94',label='Actual native LTspice VOUT')
 ax[0].axhline(180,color='#bb3333',ls='--',label='Normal peak limit')
 ax[0].set(ylabel='VOUT (V)',title='Completed 0 V cold-start fixture: 24 V input, 25 C, linear magnetics')
 ax[1].plot(t[ix]*1e3,c['i(lpower)'][ix],lw=.5,color='#e59500',label='Inductor current (display decimated)')
 ax[1].set(ylabel='Inductor current (A)')
 # Max/min bins preserve excursions in the plot instead of losing narrow spikes.
 n=15000;bins=np.linspace(0,len(t),n+1,dtype=int);tm=[];mx=[];mn=[]
 for a,b in zip(bins[:-1],bins[1:]):
  if a==b:continue
  tm.append(t[a]*1e3);mx.append(c['v(sense)'][a:b].max());mn.append(c['v(sense)'][a:b].min())
 ax[2].fill_between(tm,mn,mx,color='#bb3333',alpha=.7,label='Full-data SENSE min/max envelope')
 ax[2].axhline(.3,color='black',ls='--',label='LT3757A absolute max +0.3 V')
 ax[2].axhline(-.3,color='black',ls='--')
 ax[2].set(ylabel='SENSE (V)',xlabel='Actual simulation time (ms)')
 for a in ax:a.legend(loc='best');a.grid(alpha=.2);a.set_xlim(0,60)
 fig.suptitle('ELECTRICAL_FAIL: SENSE over-rating | no M2/M3 approval | all raw evidence preserved',fontsize=12)
 fig.tight_layout();p=HERE/'evidence/figures/cold_start_COMPLETED_SENSE_FAIL.png';fig.savefig(p,dpi=160);print(p)
