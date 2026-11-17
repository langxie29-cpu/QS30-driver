from analyze import *
def main():
 p=next((HERE/'experiments').glob('front24_fast_*'));c=native(p/'circuit.raw');a,b=.1,.12;t=c['time'];i,j=np.searchsorted(t,[a,b]);c={k:v[i:j+1] for k,v in c.items()};t=c['time']
 il=c['i(lpower)'];ir=c['i(rsrc)'];vgs=c['v(gate)']-c['v(src)'];vds=c['v(drain)']-c['v(src)'];qd=il-c['i(drec)']-c['i(rsnub)'];qg=c['i(rg)']-vgs/1e4+c['i(rneg)'];pmos=vds*qd+vgs*qg
 quantities={'IL_A':il,'shunt_A':ir,'MOS_drain_A':qd,'MOS_gate_A':qg,'MOS_external_signed_power_W':pmos,'diode_current_A':c['i(drec)'],'diode_signed_terminal_power_W':(c['v(drain)']-c['v(hv)'])*c['i(drec)'],'COUT_current_A':c['i(cout)'],'frontend_current_A':c['i(bpass)'],'frontend_power_W':(c['v(vin)']-c['v(in)'])*c['i(bpass)'],'INTVCC_V':c['v(intvcc)']}
 o=dict(window_s=[float(t[0]),float(t[-1])],requested_window_s=[a,b],boundary_disclosure='Native samples adjacent to exact boundaries, offset below maximum step; formal output acceptance uses exact interpolated boundaries in stats().',quantities={k:summarize(t,v) for k,v in quantities.items()},copper25_W=.16*summarize(t,il)['rms']**2,copper100_W=.16*(1+.00393*75)*summarize(t,il)['rms']**2,shunt_mean_W=.062*summarize(t,ir)['rms']**2,scope='25C parameter frontend/native LDO only; signed terminal power includes stored energy, not guaranteed silicon thermal loss.')
 dump(HERE/'evidence/independent/steady_component_power.json',o);print(json.dumps(o,indent=2))
if __name__=='__main__':main()
