"""Focused follow-ups and historical waveform analysis, without long retries."""
import argparse, json, shutil
from pathlib import Path
import numpy as np
import sprint03_hv as h

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);a=ap.parse_args()
    dest=h.BASE/a.run;dest.mkdir(exist_ok=False);shutil.copyfile(__file__,dest/'driver.py')
    results=[]
    for threshold in [.3,.6,.9]:
        deck=h.osc(cs=0).replace('VCOMP comp 0 5',f'VCOMP comp 0 {1.4+3*threshold}').replace('VCS cs 0 0','BCS cs 0 V=max((v(ct)-1)/1.7,0)')
        results.append(h.run(dest,'ramp_pwm_'+str(threshold),'Unloaded CT reference ramp via ideal measurement, thresholds .3/.6/.9V; tests latch and pulse consistency',deck,.001,'oscillator',dict(threshold_V=threshold,cs='ideal observer; no ramp loading')))
    deck=h.power(11.4,.935,False).replace('tran 5e-08 0.003 0 5e-08','tran 2.5e-08 0.003 0 2.5e-08')
    results.append(h.run(dest,'power_step25ns','Halved timestep commutation sensitivity, unchanged tolerances or electrical parameters',deck,.003,'power',dict(step_s=25e-9)))
    raw=(h.ROOT/'sim/sprint02/source/diotec_uf4007_spice.lib').read_text(encoding='ascii')
    raw=raw.replace(' mfg=Diotec type=Rectifier','')
    (dest/'diotec_compat.lib').write_text(raw,encoding='ascii')
    deck=h.power(11.4,.935,False).replace('D20 sw da UF','X20 sw da UF4007').replace('.control',raw+'\n.control')
    results.append(h.run(dest,'power_vendor_diode','Official Diotec electrical parameters, metadata compatibility only; supplier remains unconfirmed',deck,.003,'power',dict(supplier_hypothesis='Diotec UF4007')))
    # Original physical wiring short screen, inherited diagnostic controller is
    # explicitly NOT A-series qualified and retains its historical fixed .92 cap.
    source=h.ROOT/'sim/a9_2/sprint02_actual_baseline/startup_9/circuit.cir'
    deck=source.read_text().split('.control')[0]
    deck+=h.control(.005,100e-9,'v(HV_BUS) v(CS_FILT) v(HV_GATE) v(COMP_N) i(L20)')
    # raw kind gives generic columns; analyze this case independently below.
    d=dest/'actual_short';d.mkdir();(d/'circuit.cir').write_text(deck,encoding='ascii')
    import subprocess,time,re,gzip
    start=time.monotonic();argv=[str(h.EXE),'-b','-o','ngspice.log','circuit.cir']
    try:
        p=subprocess.run(argv,cwd=d,capture_output=True,timeout=45);rc=p.returncode
    except subprocess.TimeoutExpired:rc='TIMEOUT'
    log=(d/'ngspice.log').read_text(errors='replace');valid=rc==0 and re.search(r'end_time\s*=\s*5.00000e-03',log) is not None
    r=dict(id='actual_short',purpose='5ms original-wiring screen; not autonomous startup acceptance',exit_code=rc,duration_s=time.monotonic()-start,execution='PASS' if valid else 'FAIL',engineering='FAIL',source_sha256=h.sha(source),controller='Inherited diagnostic, not A-series qualification',argv=argv)
    if valid:
        t,v=h.loadwave(d/'waves.txt');r['metrics']={n:dict(end=float(v(n)[-1]),peak=float(v(n).max())) for n in ['v(hv_bus)','v(cs_filt)','v(hv_gate)','i(l20)']}
        with gzip.open(d/'waves.txt.gz','wb') as f:f.write((d/'waves.txt').read_bytes())
    h.dump(d/'command.json',r);results.append(r);h.dump(dest/'results.json',results)
    # Recompute historical measurements from raw nonuniform data, not summary.
    source=h.ROOT/'sim/sprint02/power_v1/buffered_type2/waves.txt.gz'
    t,v=h.loadwave(source); y=v('v(hv)'); gate=v('v(gate)')>5
    bins=[]
    for lo in [.12,.13,.14,.145]:bins.append(dict(start_s=lo,end_s=lo+.005,**h.stats(t,y,lo,lo+.005)))
    edges=np.flatnonzero(np.diff((v('v(ct)')>1.85).astype(int))==-1)+1
    cyc=[]
    for i,j in zip(edges[:-1],edges[1:]):
        if t[i]<.12:continue
        cyc.append([float(t[i]),float(np.trapezoid(y[i:j+1],t[i:j+1])/(t[j]-t[i])),float(np.median(y[i:j+1])),float(np.min(y[i:j+1])),float(np.max(y[i:j+1]))])
    a=np.array(cyc);np.savetxt(dest/'historical_cycle_statistics.csv',a,delimiter=',',header='time_s,time_weighted_mean_V,sample_median_V,min_V,max_V',comments='')
    late=t>.14;k=np.flatnonzero(late)[np.argmin(y[late])]
    data=dict(source=str(source.relative_to(h.ROOT)),source_sha256=h.sha(source),windows=bins,late_cycle_mean_slope_V_per_s=float(np.polyfit(a[a[:,0]>.14,0]-.14,a[a[:,0]>.14,1],1)[0]),late_cycle_mean_range_V=[float(a[a[:,0]>.14,1].min()),float(a[a[:,0]>.14,1].max())],worst_dip={n:float(v(n)[k]) for n in ['v(hv)','v(sw)','v(gate)','v(fb)','i(l20)','i(vswi)']},worst_dip_time_s=float(t[k]),interpretation='Cycle means still drifting; narrow HV dips coincide with commutation currents. Capacitor voltage absent from historical save; cannot infer precise internal-cap ripple or phase margin.')
    h.dump(dest/'historical_type2_analysis.json',data)
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,1,figsize=(10,7));axs[0].plot(a[:,0]*1000,a[:,1]);axs[0].set_ylabel('Cycle mean HV (V)')
    m=(t>t[k]-2e-6)&(t<t[k]+2e-6);axs[1].plot((t[m]-t[k])*1e6,y[m],label='HV terminal (V)');axs[1].plot((t[m]-t[k])*1e6,v('i(vswi)')[m],label='Switch current (A)');axs[1].legend();axs[1].set_xlabel('Time relative to dip (us)')
    for ax in axs:ax.grid(alpha=.3)
    fig.suptitle('Sprint02 raw evidence reanalysis; not new 150ms simulation');fig.tight_layout();fig.savefig(dest/'historical_type2_analysis.png',dpi=130);plt.close(fig)
    print(json.dumps(data,indent=2),flush=True)
if __name__=='__main__':main()
