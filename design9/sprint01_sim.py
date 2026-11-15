"""Append-only Sprint01 diagnostic SPICE replay and passive HV discharge.
No converter design changes. Series 0 V source measures switch current only.
"""
from pathlib import Path
import sys,json,re,subprocess,hashlib,argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from safety_sim9 import EXE,execution_ok
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);a=ap.parse_args()
    assert Path(a.run).name==a.run
    dest=ROOT/'sim/a9_2'/a.run;dest.mkdir(exist_ok=False)
    source=ROOT/'sim/a9_2/sprint01_actual/startup_9/circuit.cir'
    deck=source.read_text().replace('S_Q20 SW_HV 0 HV_GATE 0 N_SW','S_Q20 SW_HV Q20_SOURCE HV_GATE 0 N_SW\nVQ20_SENSE Q20_SOURCE 0 0')
    measurements='''meas tran hv_mean AVG v(HV_BUS) FROM=60m TO=80m
meas tran hv_pp PP v(HV_BUS) FROM=60m TO=80m
let vds = v(SW_HV)-v(Q20_SOURCE)
meas tran vds_peak MAX vds
meas tran id_peak MAX i(VQ20_SENSE)
meas tran il_peak MAX i(L20)
let vreverse = v(HV_BUS)-v(SW_HV)
meas tran diode_reverse MAX vreverse
meas tran cap_peak MAX v(HV_BUS)
let pin = -v(input)*i(VIN)
meas tran input_power AVG pin FROM=60m TO=80m
'''
    deck=deck.replace('linearize ',measurements+'linearize ',1)
    (dest/'circuit.cir').write_text(deck,encoding='ascii')
    p=subprocess.run([str(EXE),'-b','-o','ngspice.log','circuit.cir'],cwd=dest,capture_output=True,text=True,timeout=55)
    log=(dest/'ngspice.log').read_text(errors='replace')
    nums={k:float(v) for k,v in re.findall(r'^([a-z][a-z0-9_]*)\s*=\s*([\d.eE+-]+)',log,re.M)}
    results={'instrumented_startup':{'rc':p.returncode,'execution':'PASS' if execution_ok(log,.08,p.returncode,(dest/'waves.txt').exists()) else 'FAIL','metrics':nums,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'model_scope':'A9.2 functional diagnostic; not device stresses qualified by vendor model'}}
    # Existing physical C11/C12 + module caps and four bleeders, independently
    # initialized at HV target. No tube conduction or converter residual input.
    for name,c,r,v0,stop in [('all_connected',20.3e-6,50e3,172.183,12),('main_alone',20e-6,200e3,172.183,12),('main_bleeder_open',20e-6,1e15,172.183,12)]:
        folder=dest/name;folder.mkdir()
        deck=f'''Sprint01 isolated passive discharge {name}
COUT HV_BUS 0 {c} IC={v0}
RBLEED HV_BUS 0 {r}
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran 1m {stop} uic
meas tran end_time MAX time
meas tran v_1s FIND v(HV_BUS) AT=1
meas tran v_5s FIND v(HV_BUS) AT=5
meas tran v_end FIND v(HV_BUS) AT={stop}
wrdata waves.txt v(HV_BUS)
quit
.endc
.end
'''
        (folder/'circuit.cir').write_text(deck,encoding='ascii')
        p=subprocess.run([str(EXE),'-b','-o','ngspice.log','circuit.cir'],cwd=folder,capture_output=True,text=True,timeout=30)
        log=(folder/'ngspice.log').read_text(errors='replace');valid=execution_ok(log,stop,p.returncode,(folder/'waves.txt').exists())
        record={'rc':p.returncode,'execution':'PASS' if valid else 'FAIL','cap_F':c,'bleed_ohm':r,'initial_V':v0,'normal_bleeder_power_W':v0*v0/r}
        if valid:
            data=np.loadtxt(folder/'waves.txt',skiprows=1);t,v=data.T
            cross=np.flatnonzero(v<=50)
            record.update(t50_s=float(t[cross[0]]) if len(cross) else None,values={str(s):float(np.interp(s,t,v)) for s in [0,1,5,12]},analytic_t50_s=float(r*c*np.log(v0/50)))
            fig,ax=plt.subplots(figsize=(8,4));ax.plot(t,v);ax.axhline(50,ls='--',color='r');ax.set(xlabel='Time / s',ylabel='HV / V',title=name+' — isolated passive RC, not turn-off signoff');ax.grid();fig.tight_layout();fig.savefig(folder/'discharge.png');plt.close(fig)
        results[name]=record
    results['provenance']={'ngspice_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (dest/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
