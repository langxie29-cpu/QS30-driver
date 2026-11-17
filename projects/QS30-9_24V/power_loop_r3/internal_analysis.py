"""Topology-derived internal currents; never called independent silicon probes."""
from analyze import *
def main():
 p=next((HERE/'experiments').glob('cell_internal5ps_*'));c=native(p/'circuit.raw');t=c['time'];a,b=1.02e-6,1.10e-6
 def energy(y):tt,yy=window(t,y,a,b);return dict(signed_J=integ(tt,yy),positive_J=integ(tt,np.maximum(yy,0)),negative_J=integ(tt,np.minimum(yy,0)))
 # Node8 only RJ(8->7) and E3(8->13); node13 only E3 and MOS13->9.
 imos=(c['v(q:7)']-c['v(q:8)'])/.000141
 ird=(c['v(q:7)']-c['v(q:6)'])/.584
 irs=(c['v(q:9)']-c['v(q:12)'])/.0000632
 irg=(c['v(q:4)']-c['v(q:5)'])/4.998
 vds=c['v(q:13)']-c['v(q:9)'];vgs=c['v(q:5)']-c['v(q:9)']
 out=dict(case=p.name,window_s=[a,b],method='Ohm law across unchanged model resistors and internal node8/13 KCL. Requested native internal branch-current expressions were not exported. These are inferred model currents, not separately measured probes.',MOS_intrinsic_drain_current_A=summarize(t,imos),MOS_intrinsic_channel_power_W=summarize(t,vds*imos),MOS_channel_event_energy=energy(vds*imos),RD_event_energy=energy(ird**2*.584),RS_event_energy=energy(irs**2*.0000632),RG_event_energy=energy(irg**2*4.998),RJ_event_energy=energy(imos**2*.000141),MOS_intrinsic_VDS_V=summarize(t,vds),MOS_intrinsic_VGS_V=summarize(t,vgs),scope='Single12V/89.17V/1.4A isolated edge; no repetition rate, no hot silicon, no SOA or total junction loss qualification. MOS body diodes/nonlinear capacitances/E3 model network not all separately integrated. Signed channel power can include model artifacts.')
 # Native source/gate/drain zero-volt probes are independent of algebraic port reconstruction.
 qd=c['i(vqd)'];qg=c['i(vqg)'];qs=-c['i(vqs)'];out['native_terminal_KCL_residual_A']=float(np.max(np.abs(qd+qg+qs)))
 # Finite sample probe extremes within event window only; avoid UIC derivative artifacts.
 event=(t>=a)&(t<=b)
 out['event_derived_channel_current_A']=summarize(t[event],imos[event]);out['event_source_probe_A']=summarize(t[event],qs[event]);out['event_gate_probe_A']=summarize(t[event],qg[event])
 j=int(np.argmin(imos));out['outside_event_derived_extreme']=dict(time_s=float(t[j]),current_A=float(imos[j]),inside_event=bool(event[j]),interpretation='Unvalidated internal dependent-source/very-small-R model excursion outside commutation window. Numerical/model artifact suspected; physical origin not established. Cannot use these internal inferred currents/energies to sign off silicon loss. All raw bytes/extrema retained.')
 out['event_native_KCL_residual_A']=float(np.max(np.abs((qd+qg+qs)[event])))
 out['event_channel_power_W']=summarize(t[event],(vds*imos)[event])
 dump(HERE/'evidence/independent/internal_stress.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
