"""Append-only Sprint03 qualification experiments; never changes engineering sources.
Usage: python design9/sprint03_hv.py --run RUN_NAME
All electrical values in isolated decks are hypotheses, not hardware signoff.
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, json, re, shutil, subprocess, time
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'sim/sprint03'
EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
KICAD=Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf8',errors='replace')
def loadwave(p):
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt') as f:
        names=f.readline().lower().split(); a=np.loadtxt(f)
    return a[:,0],lambda n:a[:,names.index(n.lower())]
def stats(t,y,lo,hi):
    k=(t>=lo)&(t<=hi); x=t[k]; z=y[k]
    return dict(mean=float(np.trapezoid(z,x)/(x[-1]-x[0])),min=float(z.min()),max=float(z.max()),pp=float(np.ptp(z)),slope_V_per_s=float(np.polyfit(x-x[0],z,1)[0]))
def control(stop,step,vectors,extra=''):
    return f'''\n.options reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step} {stop} 0 {step} uic
meas tran end_time MAX time
{extra}
wrdata waves.txt {vectors}
quit
.endc
.end
'''
def run(dest,name,purpose,deck,stop,kind,params):
    d=dest/name; d.mkdir()
    (d/'circuit.cir').write_text(deck,encoding='ascii')
    if '.include' in deck: shutil.copyfile(BASE/'source/uc3843_functional.lib',d/'uc3843_functional.lib')
    argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']; start=time.monotonic()
    try:
        p=subprocess.run(argv,cwd=d,capture_output=True,timeout=45)
        rc=p.returncode; stdout=p.stdout.decode(errors='replace'); stderr=p.stderr.decode(errors='replace')
    except subprocess.TimeoutExpired as e:
        rc='TIMEOUT'; stdout=str(e.stdout); stderr=str(e.stderr)
    log=(d/'ngspice.log').read_text(errors='replace') if (d/'ngspice.log').exists() else ''
    end=re.search(r'end_time\s*=\s*([\deE.+-]+)',log)
    bad=[x for x in ('error:','aborted','timestep too small','failed!','no such vector') if x in log.lower()]
    valid=rc==0 and end is not None and abs(float(end[1])-stop)<1e-9 and not bad and (d/'waves.txt').exists()
    r=dict(id=name,purpose=purpose,kind=kind,parameters=params,argv=argv,timeout_s=45,duration_s=time.monotonic()-start,exit_code=rc,stdout=stdout,stderr=stderr,log_errors=bad,execution='PASS' if valid else 'FAIL',engineering='INCONCLUSIVE',deck_sha256=sha(d/'circuit.cir'),requested_stop_s=stop)
    if valid:
        t,v=loadwave(d/'waves.txt'); metrics={}
        if kind=='oscillator':
            late=t>stop*.75; g=v('v(out)')>5; edges=np.flatnonzero(np.diff(g.astype(int))==1)+1; edges=edges[t[edges]>stop*.75]
            periods=np.diff(t[edges]); metrics=dict(ct_min_V=float(v('v(ct)')[late].min()),ct_max_V=float(v('v(ct)')[late].max()),frequency_Hz=float(1/np.median(periods)) if len(periods) else None,period_pp_s=float(np.ptp(periods)) if len(periods) else None,duty=float(np.trapezoid(g[late].astype(float),t[late])/(t[late][-1]-t[late][0])))
            cols=['v(ct)','v(out)','v(cs)']
        elif kind=='cs':
            late=t>stop*.8; metrics=dict(actual_current_A=float(v('i(vprobe)')[late].mean()),cs_final_V=float(v('v(cs)')[-1]),shunt_final_V=float(v('v(src)')[-1]),conversion_V_per_A=float(v('v(cs)')[-1]/v('i(vprobe)')[-1]))
            cols=['i(vprobe)','v(cs)','v(src)']
        else:
            metrics['output']=stats(t,v('v(hv)'),stop-.0005,stop)
            metrics['capacitor']=stats(t,v('v(cap)'),stop-.0005,stop)
            for n in ['i(l20)','v(gate)','v(sw)','i(vdprobe)']:
                z=v(n); metrics[n]=dict(min=float(z.min()),max=float(z.max()),late_rms=float(np.sqrt(np.trapezoid(z[t>stop-.0005]**2,t[t>stop-.0005])/(t[-1]-t[t>stop-.0005][0]))))
            cols=['v(hv)','i(l20)','v(sw)','i(vdprobe)']
        r['metrics']=metrics
        fig,axs=plt.subplots(len(cols),1,figsize=(10,8),sharex=True)
        idx=np.arange(max(0,len(t)-25000),len(t))
        for ax,col in zip(axs,cols): ax.plot(t[idx]*1e3,v(col)[idx],lw=.6); ax.set_ylabel(col); ax.grid(alpha=.3)
        axs[-1].set_xlabel('Time (ms)'); fig.suptitle(name+' | simplified diagnostic; no hardware qualification'); fig.tight_layout(); fig.savefig(d/'waveforms.png',dpi=120); plt.close(fig)
        with gzip.open(d/'waves.txt.gz','wb') as f: f.write((d/'waves.txt').read_bytes())
    dump(d/'command.json',r); print(name,rc,r.get('metrics'),flush=True)
    return r

def osc(mode='baseline',idis=.0083,cs=0):
    s='''UC3843A hypothesis using inherited functional model
.include uc3843_functional.lib
VCC vcc 0 12
VCOMP comp 0 5
VFB fb 0 0
RT ref ct 10k
CT ct 0 2.2n
CREF ref 0 100n
XUC comp fb cs ct 0 out vcc ref UC3843_FUNC IDIS=IDIS_VALUE
CG out 0 1n
'''.replace('IDIS_VALUE',str(idis))
    if mode=='baseline': s+=f'VCS cs 0 {cs}\n'
    else:
        s+='VSRC src 0 0\nR36 src cs 1k\nC13 cs 0 100p\n'
        if mode=='direct': s+='RRAMP ct cs 2.8k\n'
        else: s+='RRAMP rampbuf cs 2.8k\nRBCT ct rbbase 1k\nQBUF vcc rbbase rampbuf NBUF\nREBUF rampbuf 0 100k\n.model NBUF NPN(IS=6.7f BF=100 VAF=75 IKF=.1 CJE=4p CJC=3p TF=.3n)\n'
    return s+control(.001,20e-9,'v(ct) v(out) v(cs) v(ref)')

def csdeck(amps,repair):
    # Independent known drain current and fixed switch voltage: distinguishes
    # actual voltage pickoff from hypothetical Kelvin shunt conversion.
    return f'''Known-current excitation, disconnected controller
VSW sw 0 12
ILOAD sw drain {amps}
VPROBE drain src 0
{'RS src 0 .15' if repair else 'VSOURCE src 0 0'}
R36 {'src' if repair else 'sw'} cs {'1k' if repair else '100k'}
C13 cs 0 {'100p' if repair else '470p'}
'''+control(.0005,100e-9,'i(vprobe) v(cs) v(src)')

def power(vin,duty,c10):
    # Warm-start diagnostic, not autonomous startup or a UC3843 implementation.
    s=f'''Warm-start open-loop boost hypothesis, fixed physical assumptions
.model NSW SW(RON=.55 ROFF=1e10 VT=3 VH=.1)
.model UF D(IS=10n N=1.5 RS=.5 CJO=15p TT=75n BV=1000 IBV=5u)
.model BODY D(IS=1n N=1.5 RS=.1 CJO=1p TT=100n BV=400)
VIN vin 0 {vin}
RL vin lin .3
L20 lin sw 220u IC=.5
S20 sw src gate 0 NSW
RSENSE src 0 .15
DBODY src sw BODY
COSS sw src 150p
D20 sw da UF
VDPROBE da hv 0
RESR hv cap .5
COUT cap 0 20.3u IC=172.1832579
RBLEED hv 0 50k
RFB hv 0 1.5221meg
ROVP hv 0 1.5191meg
BTUBE hv 0 I=27m*min(max(v(hv)/150,0),1)
VPWM gate 0 PULSE(0 10 0 30n 30n {duty/78000-30e-9} {1/78000})
'''
    if c10:s+='C10 sw hv 10n\n'
    return s+control(.003,50e-9,'v(hv) v(cap) v(sw) v(src) v(gate) i(l20) i(vdprobe)')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);a=ap.parse_args();assert Path(a.run).name==a.run
    dest=BASE/a.run;dest.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,dest/'driver.py')
    results=[]
    for mode in ['baseline','direct','buffered']:
        results.append(run(dest,'osc_'+mode,'Compare CT loading using identical timing and 8.3mA A-series hypothesis',osc(mode),.001,'oscillator',dict(idis_A=.0083,mode=mode)))
    for idis in [.0076,.0088]:
        results.append(run(dest,'osc_idis_'+str(idis),'Sensitivity at documented A-series discharge-current endpoints; not complete corner model',osc(idis=idis),.001,'oscillator',dict(idis_A=idis)))
    for val in [.3,.6,.9]:
        results.append(run(dest,'pwm_cs_'+str(val),'Known CS threshold changes pulse width at fixed COMP',osc(cs=val),.001,'oscillator',dict(cs_V=val)))
    for repair in [False,True]:
        for amps in [.2,.8]:
            results.append(run(dest,('kelvin_' if repair else 'actual_cs_')+str(amps),'Known current at fixed SW voltage; verify A-to-V conversion',csdeck(amps,repair),.0005,'cs',dict(current_A=amps,repair_hypothesis=repair)))
    # Small bounded screen only. No long closed-loop run when G0 is blocked.
    for duty,c10 in [(.92,False),(.935,False),(.95,False),(.935,True)]:
        results.append(run(dest,'power_'+str(duty)+('_c10' if c10 else ''),'Warm-start 11.4V/27mA plus bleeders; sign of energy drift vs duty and C10 burden',power(11.4,duty,c10),.003,'power',dict(vin_V=11.4,duty=duty,c10_F=10e-9 if c10 else 0)))
    dump(dest/'results.json',dict(results=results,system='FAIL/HOLD',HV_G0='BLOCKED',HV_G1='BLOCKED',HV_G2='FAIL'))
    with (dest/'SIMULATION_MATRIX.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=['id','purpose','kind','execution','engineering','exit_code','duration_s','requested_stop_s']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in results)
    return 0 if all(r['execution']=='PASS' for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
