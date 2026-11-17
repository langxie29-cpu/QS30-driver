from analyze import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
F=HERE/'evidence/figures';F.mkdir(exist_ok=True)
def envelope(ax,t,y,label,color=None,bins=1600):
 edges=np.linspace(t[0],t[-1],bins+1);idx=np.searchsorted(t,edges);tt=[];lo=[];hi=[]
 for a,b in zip(idx[:-1],idx[1:]):
  if b>a:tt.append((t[a]+t[b-1])/2);lo.append(float(np.min(y[a:b])));hi.append(float(np.max(y[a:b])))
 ax.fill_between(tt,lo,hi,alpha=.3,color=color);ax.plot(tt,(np.array(lo)+np.array(hi))/2,label=label,color=color,lw=.8)
def raw(case):return native(next((HERE/'experiments').glob(case+'_*'))/'circuit.raw')
def main():
 c=raw('front24_fast');t=c['time']*1e3;fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
 for k,l,col in [('v(hv)','HV output','C0'),('v(in)','Switched branch','C1')]:envelope(axes[0],t,c[k],l,col)
 axes[0].axhspan(164.9,175.1,color='green',alpha=.1);axes[0].set_ylabel('Voltage / V');axes[0].legend();axes[0].set_title('R3 parameter frontend + native LT3757A LDO; COUT=0; not TPS26601 qualification')
 for k,l,col in [('i(lpower)','Inductor','C0'),('i(bpass)','Input pass device','C1')]:envelope(axes[1],t,c[k],l,col)
 axes[1].set_ylabel('Current / A');axes[1].legend()
 envelope(axes[2],t,(c['v(vin)']-c['v(in)'])*c['i(bpass)'],'Pass terminal power','C3');axes[2].set_ylabel('Power / W');axes[2].set_xlabel('Time from input establishment / ms');axes[2].legend()
 for ax in axes:ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(F/'startup_energy_path.png',dpi=150);plt.close(fig);del c
 c=raw('cell5ps');sel=(c['time']>=1.02e-6)&(c['time']<=1.1e-6);t=(c['time'][sel]-1e-6)*1e9;fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
 def y(k):return c[k][sel]
 for yy,l,col in [(y('v(qd)')-y('v(qs)'),'MOS external VDS','C0'),(y('v(q:13)')-y('v(q:9)'),'MOS intrinsic VDS','C2'),(y('v(drain)')-y('v(hv)'),'Diode A-K voltage','C3')]:envelope(axes[0],t,yy,l,col)
 axes[0].set_ylabel('Voltage / V');axes[0].legend();axes[0].set_title('Localized 89.17V / 1.4A / 12V drive cell; original vendor models; NOT cold startup')
 for k,l,col in [('i(lpower)','Inductor','C0'),('i(drec)','Rectifier','C3'),('i(rsrc)','Shunt','C1')]:envelope(axes[1],t,y(k),l,col)
 axes[1].set_ylabel('Current / A');axes[1].legend()
 for yy,l,col in [(y('i(vqd)'),'Drain into MOS','C0'),(-y('i(vqs)'),'Source into MOS','C1'),(y('i(vqg)'),'Gate into MOS','C2')]:envelope(axes[2],t,yy,l,col)
 axes[2].set_ylabel('Terminal current / A');axes[2].set_xlabel('Time after 1us / ns');axes[2].legend()
 for ax in axes:ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(F/'commutation_stress.png',dpi=150);plt.close(fig);del c
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for case,col,label in [('front26p4_short1u','C0','Downstream CIN=1uF'),('front26p4_short47u','C3','Downstream CIN=47uF')]:
  c=raw(case);sel=(c['time']>=.01195)&(c['time']<=.0125);t=(c['time'][sel]-.012)*1e6
  envelope(axes[0],t,c['i(lpower)'][sel],label+' IL',col);envelope(axes[1],t,c['i(bpass)'][sel],label+' pass current',col)
 axes[0].axhline(3.1,color='k',ls='--',label='25C 10% L-drop point');axes[0].legend();axes[0].set_ylabel('Inductor current / A');axes[0].set_title('PWM disabled short: downstream energy bypasses favorable instantaneous input limit')
 axes[1].set_ylabel('Pass current / A');axes[1].set_xlabel('Time relative to short command / us');axes[1].legend()
 for ax in axes:ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(F/'downstream_fault_energy.png',dpi=150);plt.close(fig)
 print('3 plots: raw sample min/max envelopes, no filtered acceptance data')
if __name__=='__main__':main()
