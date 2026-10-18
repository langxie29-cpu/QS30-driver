"""Native ngspice passive discharge experiment; excludes residual converter power.

Only bleeders retained (conservative: feedback/OVP dividers omitted). No safety
touch-voltage certification. Does not replace converter turn-off validation.
"""
from pathlib import Path
import subprocess
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'


def main():
    dest=ROOT/'sim/a9_2/discharge';dest.mkdir(exist_ok=False)
    cases=[('all_connected',20.3e-6,50e3,172.18),
           ('all_high_rc',24.36e-6,50.5e3,220),
           ('one_bleeder_open',20.3e-6,200e3/3,172.18),
           ('main_alone',20e-6,200e3,172.18),
           ('main_bleeder_open',20e-6,1e15,172.18),
           ('detached_module',.1e-6,200e3,172.18)]
    results=[]
    for name,c,r,voltage in cases:
        folder=dest/name;folder.mkdir()
        step=1e-5 if name=='detached_module' else .001
        stop=.15 if name=='detached_module' else 12
        deck=f'''QS30 A9.2 isolated passive discharge {name}
* No converter energy input. Sense dividers omitted, bleeders only.
COUT HV_BUS 0 {c} IC={voltage}
RBLEED HV_BUS 0 {r}
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step} {stop} uic
meas tran end_time MAX time
meas tran final_voltage FIND v(HV_BUS) AT={stop}
wrdata voltage.txt v(HV_BUS)
quit
.endc
.end
'''
        (folder/'circuit.cir').write_text(deck,encoding='ascii')
        argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']
        p=subprocess.run(argv,cwd=folder,capture_output=True,text=True,errors='replace',timeout=30)
        record=dict(case=name,cap_F=c,bleed_ohms=r,initial_V=voltage,argv=argv,rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
        log=(folder/'ngspice.log').read_text(errors='replace');wave=folder/'voltage.txt'
        valid=p.returncode==0 and wave.exists() and 'aborted' not in log.lower() and 'error:' not in log.lower()
        if valid:
            data=np.loadtxt(wave,skiprows=1);t,v=data[:,0],data[:,1]
            valid=t[-1]>=stop-1e-6
            threshold=np.flatnonzero(v<=50)
            record.update(t_end_s=float(t[-1]),final_V=float(v[-1]),
                          measured_t50_s=float(t[threshold[0]]) if len(threshold) else None)
            fig,ax=plt.subplots(figsize=(8,4));ax.plot(t,v);ax.axhline(50,color='r',linestyle='--',label='50 V test reference')
            ax.set(xlabel='time (s)',ylabel='HV_BUS (V)',title=f'Passive bleeder only: {name}');ax.legend();ax.grid();fig.tight_layout();fig.savefig(folder/'discharge.png',dpi=120);plt.close(fig)
        record['execution']='PASS' if valid else 'FAIL'
        record['t50_test']='PASS' if record.get('measured_t50_s') is not None else 'FAIL'
        (folder/'command.json').write_text(json.dumps(record,indent=2)+'\n')
        results.append(record)
        print(json.dumps(record),flush=True)
    (dest/'results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
