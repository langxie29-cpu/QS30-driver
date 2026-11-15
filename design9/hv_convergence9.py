"""A9.3 append-only SPICE evidence. Functional candidates never edit KiCad.
Run stages separately, e.g. python design9/hv_convergence9.py controller --run ctrl01
Each deck is self-contained (model copied locally); no overwriting prior runs.
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, json, math, re, subprocess, sys, time
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'sim/a9_3'
EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
MODEL=BASE/'models/uc3843_functional.lib'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')

def audit():
    """Use fresh native XML; explicitly verify CSV per pin, not narrative reports."""
    path=ROOT/'kicad/logs/a9_3_baseline/QS30-9_MAIN.xml'
    tree=ET.parse(path); mapping={}
    for c in tree.findall('./components/comp'):
        mapping[c.attrib['ref']]=next(f.text for f in c.findall('./fields/field') if f.attrib.get('name')=='DesignRef')
    nodes={}
    for n in tree.findall('./nets/net'):
        for p in n.findall('node'): nodes[(mapping[p.attrib['ref']],p.attrib['pin'])]=n.attrib['name']
    rows=list(csv.DictReader((ROOT/'netlist9/QS30-9_REV.A_netlist.csv').open(encoding='utf-8-sig')))
    refs=['U20','Q20','L20','D20','C10','C11','C12','R32','C9','R34','R35','R36','C13','R37','C14','C15','U23','U24','R40','R41','R42','C16','Q21','Q22','Q23','Q24','Q25','Q4']
    evidence=[]
    for r in rows:
        if r['ref'] not in refs: continue
        a=nodes[(r['ref'],r['pin'])]
        assert a==r['net'], (r,a)
        evidence.append(dict(r,native_net=a))
    dump(BASE/'native_audit.json',{'input':str(path.relative_to(ROOT)),'sha256':sha(path),'pins':evidence})
    return evidence

def control(stop,step,vectors,measures='',method='gear',maxstep=None,uic=True):
    return f'''\n.options reltol=.001 abstol=1n vntol=1u method={method} itl4=200
.save all @q21[ic] @q22[ic] @q25[ic]
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran {step:g} {stop:g} 0 {maxstep or step:g} {'uic' if uic else ''}
meas tran end_time MAX time
{measures}
wrdata waves.txt {vectors}
quit
.endc
.end
'''

def simulate(folder,deck,stop,meta,analyze=None):
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'circuit.cir').write_text(deck,encoding='ascii')
    if '.include uc3843_functional.lib' in deck: (folder/'uc3843_functional.lib').write_bytes(MODEL.read_bytes())
    argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']; started=time.time()
    try:
        p=subprocess.run(argv,cwd=folder,capture_output=True,text=True,errors='replace',timeout=120)
        rc,out,err=p.returncode,p.stdout,p.stderr
    except subprocess.TimeoutExpired as e: rc,out,err='TIMEOUT',str(e.stdout),str(e.stderr)
    log=(folder/'ngspice.log').read_text(errors='replace') if (folder/'ngspice.log').exists() else ''
    m=re.search(r'end_time\s*=\s*([\deE.+-]+)',log)
    bad=[s for s in ['error:','aborted','timestep too small','failed!','no such vector'] if s in log.lower()]
    wave=folder/'waves.txt'
    valid=rc==0 and m is not None and abs(float(m[1])-stop)<max(1e-9,stop*1e-6) and not bad and wave.exists()
    result=dict(meta,argv=argv,rc=rc,stdout=out,stderr=err,duration_s=time.time()-started,execution='PASS' if valid else 'FAIL',log_errors=bad,requested_stop_s=stop,deck_sha256=sha(folder/'circuit.cir'),simulator_sha256=sha(EXE))
    if wave.exists():
        with gzip.open(folder/'waves.txt.gz','wb') as f: f.write(wave.read_bytes())
    if valid:
        headers=wave.read_text().splitlines()[0].lower().split()
        data=np.loadtxt(wave,skiprows=1); t=data[:,0]
        assert abs(t[-1]-stop)<max(1e-9,stop*1e-6)
        def v(s): return data[:,headers.index(s.lower())]
        result['metrics']=analyze(t,v) if analyze else {}
        result['native_measurements']={k:float(val) for k,val in re.findall(r'^([a-z][a-z_0-9]*)\s*=\s*([\deE.+-]+)',log,re.M)}
        result['engineering']=result['metrics'].pop('status','OBSERVATION')
        fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True)
        cols=headers[1:]; groups=[cols[i::3] for i in range(3)]
        for ax,group in zip(axs,groups):
            idx=np.unique(np.r_[np.arange(0,len(t),max(1,len(t)//16000)),len(t)-1])
            for col in group[:5]: ax.plot(t[idx]*1000,v(col)[idx],label=col,linewidth=.7)
            ax.legend(fontsize=7,loc='upper right'); ax.grid(alpha=.3)
        axs[-1].set_xlabel('Time (ms)'); fig.suptitle(folder.name+' | diagnostic model, not hardware qualification')
        fig.tight_layout(); fig.savefig(folder/'waveforms.png',dpi=120); plt.close(fig)
    dump(folder/'command.json',result)
    print(folder.name,result['execution'],result.get('engineering'),result.get('metrics',{}),flush=True)
    return result

def controller_deck(c):
    stop=c.get('stop',.01)
    vin=c.get('supply','PWL(0 0 1m 12)')
    fb=c.get('fb','0')
    lines=['UC3843 isolated physical-pin functional test', '.include uc3843_functional.lib',
           f'VCC vcc 0 {vin}',f'VFB fb 0 {fb}',
           'C_VCC vcc 0 1u','C_REF ref 0 100n','R_REF_LOAD ref 0 5k',
           f'RT ref ct {c.get("rt",10000)}',f'CT ct 0 {c.get("ct",2.2e-9)}',
           f'C15 comp 0 {c.get("comp_cap",22e-6)}', 'R37 comp comp_r 10k','C14 comp_r 0 100n',
           f'XUC comp fb cs ct 0 out vcc ref UC3843_FUNC IDIS={c.get("idis",.006)}',
           'C_GATE out 0 1n','R_GATE out 0 100k']
    if c.get('comp_force') is not None: lines.append('VCOMP comp 0 '+str(c['comp_force']))
    lines.append(c.get('cs','VCS cs 0 0'))
    vec='v(vcc) v(ref) v(ct) v(comp) v(fb) v(cs) v(out) v(xuc.dis) v(xuc.mem)'
    meas='meas tran ref_final FIND v(ref) AT='+str(stop)+'\nmeas tran ct_max MAX v(ct) FROM='+str(stop*.8)+'\nmeas tran ct_min MIN v(ct) FROM='+str(stop*.8)
    return '\n'.join(lines)+control(stop,c.get('step',100e-9),vec,meas,c.get('method','gear'),uic=c.get('uic',True))

def ctrl_metrics(c,t,v):
    mask=t>c.get('stop',.01)*.8; gate=v('v(out)')>5
    rising=np.flatnonzero(np.diff(gate.astype(int))==1)+1
    falling=np.flatnonzero(np.diff(gate.astype(int))==-1)+1
    late=rising[t[rising]>c.get('stop',.01)*.8]
    freq=float(1/np.median(np.diff(t[late]))) if len(late)>2 else None
    d={'ref_end_V':float(v('v(ref)')[-1]),'comp_end_V':float(v('v(comp)')[-1]),'out_max_V':float(v('v(out)').max()),'late_frequency_Hz':freq,'late_duty':float(np.trapezoid(gate[mask].astype(float),t[mask])/(t[mask][-1]-t[mask][0])),'ct_min_V':float(v('v(ct)')[mask].min()),'ct_max_V':float(v('v(ct)')[mask].max()),'first_pulse_s':float(t[rising[0]]) if len(rising) else None,'status':'SIMULATED PASS'}
    if c['id']=='fb_high': good=d['out_max_V']<.5
    elif c['id']=='uvlo':
        up=np.flatnonzero((v('v(ref)')>4.5)&(t<.004)); down=np.flatnonzero((v('v(out)')<.5)&(v('v(vcc)')<7.6)&(t>.004))
        d['ref_valid_vcc_V']=float(v('v(vcc)')[up[0]]) if len(up) else None
        d['off_after_uvlo']=bool(len(down) and np.max(v('v(out)')[t>.007])<.5)
        good=d['off_after_uvlo'] and len(up)>0
    else: good=freq is not None and 65000<freq<90000 and 4.82<d['ref_end_V']<5.18
    if c['id']=='cs_latch':
        trip=(v('v(cs)')>1)&(v('v(xuc.dis)')<.1)
        d['cs_trip_off_fraction']=float(np.mean(v('v(out)')[trip]<.5))
        # Explicitly find re-triggering within a charge interval after first trip.
        dis=v('v(xuc.dis)')>.5; count=0; held=False
        for i in range(len(t)):
            if dis[i]: held=False
            elif held and gate[i]: count+=1
            if v('v(xuc.mem)')[i]>.9 and not gate[i]: held=True
        d['retrigger_samples_same_cycle']=count
        edges=np.flatnonzero(np.diff((v('v(cs)')>1).astype(int))==1)+1
        delays=[]
        for edge in edges:
            if t[edge]<.001 or v('v(out)')[edge]<5: continue
            off=np.flatnonzero((t>t[edge])&(t<t[edge]+1e-6)&(v('v(out)')<.5))
            if len(off): delays.append(float(t[off[0]]-t[edge]))
        d['cs_to_output_low_max_s']=max(delays) if delays else None
        d['cs_tested_edges']=len(delays)
        good=good and count==0 and len(delays)>10 and max(delays)<=300e-9
    d['status']='SIMULATED PASS' if good else 'FAIL'
    return d

def controller(dest,selected=None):
    cases=[dict(id='nominal_start',stop=.12,step=200e-9),dict(id='uvlo',supply='PWL(0 0 3m 12 4m 12 7m 0 10m 0)',comp_force=5),
           dict(id='fb_low',comp_cap=100e-9),dict(id='fb_high',fb='2.7',comp_cap=100e-9),
           dict(id='cs_latch',stop=.003,step=20e-9,comp_force=5,cs='BCS cs 0 V=(v(ct)>1.8 && v(ct)<2.2) ? 1.2 : 0'),
           dict(id='max_duty',comp_force=5),dict(id='solver_trap',comp_force=5,method='trap'),
           dict(id='solver_op',comp_force=5,uic=False),dict(id='idis_low',comp_force=5,idis=.0028),
           dict(id='idis_high',comp_force=5,idis=.0083)]
    results=[]
    for c in cases:
        if selected and c['id'] not in selected: continue
        results.append(simulate(dest/c['id'],controller_deck(c),c.get('stop',.01),dict(stage='controller',case=c),lambda t,v:ctrl_metrics(c,t,v)))
    return results

def power_deck(c):
    stop=c.get('stop',.15); closed=c.get('closed',False)
    c10=c.get('c10',10e-9); rs=c.get('rs',.15 if closed else .001)
    lines=['QS30 A9.3 ISOLATED power fixture - no system protection claim',
           '* Open-loop PWM / closed-loop candidate only, not current KiCad baseline.',
           '.model NSW SW(RON=.55 ROFF=1e10 VT=3 VH=.1)',
           '.model UF D(IS=10n N=1.5 RS=.5 CJO=15p TT=75n BV=1000 IBV=5u)',
           '.model BODY D(IS=1n N=1.5 RS=.1 CJO=1p TT=100n BV=400)',
           f'VIN vin 0 {c.get("vinwave", "PWL(0 0 100u "+str(c.get("vin",12))+")")}',
           'R_FIX vin vcc .05','C_VCC vcc 0 10u',
           f'RL vcc lin {c.get("dcr",.3)}',f'L20 lin sw {c.get("ind",220e-6)}',
           'VSWI sw mos 0','S20 mos src gate 0 NSW',f'RSENSE src 0 {rs}',
           'DBODY src mos BODY','COSS mos src 150p','D20 sw hv UF',
           f'RESR hv cap {c.get("esr",.5)}',f'COUT cap 0 {c.get("cout",20.3e-6)}',
           'RBLEED hv 0 50k',f'RFBTOP hv fb {c.get("rtop",1.5e6)}','RFBBOT fb 0 22.1k']
    if c10: lines.append(f'C10 sw hv {c10}')
    if c.get('mos_model')=='level1':
        lines=[x if not x.startswith('S20 ') else 'M20 mos gate src src NMOS' for x in lines]
        lines.append('.model NMOS NMOS(LEVEL=1 VTO=3 KP=2 LAMBDA=.002 RD=.25 RS=.15 IS=1e-25)')
    if c.get('resistive'):
        lines.append('RLOAD hv 0 8.5k')
    else:
        count=c.get('count','9')
        lines.append(f'BTUBES hv 0 I=({count})*max((v(hv)-125)/20000,0)')
    if c.get('short'):
        lines+=['VSHORT ctl 0 PWL(0 0 100m 0 100.001m 5)', '.model SHORT SW(RON=1 ROFF=1e12 VT=2 VH=.1)','SSHORT hv 0 ctl 0 SHORT']
    if closed:
        lines+=['.include uc3843_functional.lib','C_REF ref 0 100n',
                f'RT ref ct {c.get("rt",10000)}',f'CT ct 0 {c.get("ct",2.2e-9)}',
                'XUC comp fb cs ct 0 driver vcc ref UC3843_FUNC',
                f'C15 comp 0 {c.get("comp_cap",22e-6)}','R37 comp comp_r 10k','C14 comp_r 0 100n',
                'RG driver gate 10','RGPD gate 0 100k','CG gate src 1n']
        if c.get('compensation')=='type2':
            lines=[x for x in lines if not x.startswith(('C15 ','C14 '))]
            lines+=['C14 comp_r fb 4.7u','C15 comp fb 1n']
        if c.get('wrong_cs'):
            lines+=['R36 sw cs 100k','C13 cs 0 470p']
        else:
            # Physical summation resistors: low-side 1k, ramp 2.8k => .737*Vs + .263*CT.
            # Baseline offset of CT is retained, not silently subtracted by a source.
            lines+=['R36 src cs 1k',f'RRAMP {"rampbuf" if c.get("buffer") else "ct"} cs 2.8k','C13 cs 0 100p']
            if c.get('buffer'):
                lines+=['.model NBUF NPN(IS=6.7f BF=100 VAF=75 IKF=.1 CJE=4p CJC=3p TF=.3n)',
                        'RBCT ct rbbase 1k','QBUF vcc rbbase rampbuf NBUF','REBUF rampbuf 0 100k']
        if c.get('fb_fault'):
            if c['fb_fault']=='top_open': lines=[x if not x.startswith('RFBTOP ') else 'RFBTOP hv fb 1e15' for x in lines]
            if c['fb_fault']=='bottom_short': lines=[x if not x.startswith('RFBBOT ') else 'RFBBOT fb 0 .001' for x in lines]
    else:
        duty=c.get('duty',.94); freq=78000
        lines+=[f'VPWM driver 0 PULSE(0 10 1m 30n 30n {duty/freq} {1/freq})',
                'RG driver gate 10','CG gate src 1n','RCP comp 0 1meg','RFCT ct 0 1meg','RREF ref 0 1meg','RCS cs 0 1meg']
    vec='v(hv) v(sw) v(src) v(gate) v(comp) v(fb) v(cs) v(ct) v(ref) i(l20) i(vin) i(vswi)'
    measures=f'''meas tran hv_peak MAX v(hv)
meas tran il_peak MAX i(l20)
meas tran sw_peak MAX v(sw)
meas tran mos_i_peak MAX i(vswi)
meas tran il_rms RMS i(l20) FROM={stop-.01}
meas tran mos_i_rms RMS i(vswi) FROM={stop-.01}
meas tran hv_avg AVG v(hv) FROM={stop-.01}
meas tran hv_min MIN v(hv) FROM={stop-.01}
meas tran hv_max MAX v(hv) FROM={stop-.01}
let pin=v(vin)*(-i(vin))
let pmos=v(mos,src)*i(vswi)
meas tran input_power AVG pin FROM={stop-.01}
meas tran mos_loss AVG pmos FROM={stop-.01}'''
    return '\n'.join(lines)+control(stop,c.get('step',200e-9),vec,measures,method=c.get('method','gear'))

def power_metrics(c,t,v):
    late=t>c.get('stop',.15)-.01
    hv=v('v(hv)');il=v('i(l20)')
    mean=float(np.trapezoid(hv[late],t[late])/(t[late][-1]-t[late][0]))
    metric=dict(hv_end_V=float(hv[-1]),hv_peak_V=float(hv.max()),hv_late_average_V=mean,hv_late_pp_V=float(np.ptp(hv[late])),inductor_peak_A=float(il.max()),switch_peak_V=float(v('v(sw)').max()),cs_peak_V=float(v('v(cs)').max()),status='OBSERVATION')
    if c.get('closed'):
        regulated=169<=mean<=175 and metric['hv_late_pp_V']<2 and metric['hv_peak_V']<220
        metric['status']='SIMULATED PASS' if regulated else 'FAIL'
    return metric

def power(dest,selected=None):
    cases=[dict(id='open_original_c10',stop=.03,c10=10e-9,resistive=True),
           dict(id='open_without_c10',stop=.03,c10=0,resistive=True),
           dict(id='open_duty_93',stop=.08,c10=0,duty=.93,resistive=True),
           dict(id='closed_actual_cs',closed=True,wrong_cs=True,c10=10e-9),
           dict(id='closed_cs_repair_only',closed=True,c10=10e-9),
           dict(id='closed_no_c10',closed=True,c10=0),
           dict(id='closed_rt22k_ct1n',closed=True,c10=0,rt=22000,ct=1e-9)]
    cases += [dict(id='closed_buffer',closed=True,c10=0,buffer=True,mos_model='level1'),
              dict(id='closed_buffer_rt22k',closed=True,c10=0,buffer=True,mos_model='level1',rt=22000,ct=1e-9),
              dict(id='open_smooth_crosscheck',stop=.08,c10=0,duty=.93,resistive=True,mos_model='level1')]
    cases += [dict(id='closed_type2',closed=True,c10=0,buffer=True,mos_model='level1',rt=22000,ct=1e-9,compensation='type2',stop=.1)]
    result=[]
    for c in cases:
        if selected and c['id'] not in selected:continue
        result.append(simulate(dest/c['id'],power_deck(c),c.get('stop',.15),dict(stage='power',case=c),lambda t,v:power_metrics(c,t,v)))
    return result

def protection_deck(c):
    # Exact original component nodes copied from fresh native audit; generic BJT
    # values identical to A9.2. Candidate modifications are explicitly enumerated.
    old=(ROOT/'sim/a9_2/final_actual_model/startup_9/circuit.cir').read_text()
    want={'R40','R41','R42','C16','R43','R44','R45','R46','R47','R48','R49','R50','R51','R52','R53','Q21','Q22','Q23','Q24','Q25','R37','C14','C15'}
    lines=['QS30 A9.3 independent OVP latch and COMP sink fixture',
           '* Forced HV source is stimulus, never a protected converter peak.']
    for line in old.splitlines():
        if line.startswith('.model NGEN ') or line.startswith('.model PGEN '):lines.append(line.replace('{beta}',str(c.get('beta',100))))
        elif line.split(' ')[0] in want:
            if line.startswith('C15 '):line='C15 COMP_N 0 '+str(c.get('comp_cap',22e-6))+' IC=4'
            if line.startswith('C16 '):line='C16 OVP_SNS 0 '+str(c.get('c16',100e-9))
            if line.startswith('R42 '):line='R42 OVP_SNS 0 '+str(c.get('rbot',19100))
            if line.startswith('R41 '):line='R41 HV_BUS OVP_SNS '+str(c.get('rtop',1.5e6))
            if c.get('limited'):
                if line.startswith('Q21 '):line='Q21 OVP_LATCH LATCH_B P_EMITTER PGEN'
                if line.startswith('Q22 '):line='Q22 N_COL N_BASE 0 NGEN'
            lines.append(line)
    if c.get('limited'):lines+=['RPE EXT12 P_EMITTER 330','RNB OVP_LATCH N_BASE 22k','RNC N_COL LATCH_B 10k']
    lines += ['VIN EXT12 0 '+c.get('supply','PWL(0 0 100u 12)'),
              'VHV HV_BUS 0 '+c.get('hv','PWL(0 0 2m 170 8m 170 14m 230 40m 230)'),
              'VRST OVP_RST 0 '+c.get('reset','0'),
              'BREF VREF_OVP 0 I=max((v(VREF_OVP)-'+str(c.get('ref',2.495))+')/.2,0)',
              'CREF VREF_OVP 0 100p',
              'BDIFF diff 0 V=v(VREF_OVP)-v(OVP_SNS)',
              'RDELAY diff ctl 1k','CDELAY ctl 0 1n',
              'BCOMP OVP_SET 0 I=(v(EXT12)>2 && v(ctl)<0) ? max(v(OVP_SET),0)/50 : 0',
              'B_EA 0 COMP_N I=v(EXT12)>8.4 ? min(max((6-v(COMP_N))/.1,0),.0008) : 0',
              'R_COMP COMP_N 0 1meg']
    vec='v(HV_BUS) v(OVP_SNS) v(VREF_OVP) v(OVP_SET) v(OVP_LATCH) v(COMP_N) v(HV_FAULT_OD) v(OVP_RST) @q21[ic] @q22[ic] @q25[ic]'
    meas='''meas tran q21_min MIN @q21[ic]
meas tran q22_max MAX @q22[ic]
meas tran q25_max MAX @q25[ic]
meas tran comp_end FIND v(COMP_N) AT=.04
meas tran latch_end FIND v(OVP_LATCH) AT=.04'''
    return '\n'.join(lines)+control(c.get('stop',.04),1e-6,vec,meas)

def protection_metrics(c,t,v):
    hv=v('v(hv_bus)');diff=v('v(ovp_sns)')-v('v(vref_ovp)')
    cross=np.flatnonzero((t>.005)&(diff>0));low=np.flatnonzero((t>.005)&(v('v(ovp_set)')<.5));comp=np.flatnonzero((t>.005)&(v('v(comp_n)')<1.4))
    d=dict(forced_hv_peak_V=float(hv.max()),q21_peak_A=float(abs(v('@q21[ic]')).max()),q22_peak_A=float(abs(v('@q22[ic]')).max()),q25_peak_A=float(abs(v('@q25[ic]')).max()),latch_end_V=float(v('v(ovp_latch)')[-1]),comp_end_V=float(v('v(comp_n)')[-1]),status='FAIL')
    if len(cross):
        i=cross[0]; d.update(sense_cross_s=float(t[i]),forced_hv_at_cross_V=float(hv[i]))
        lo=low[low>=i];co=comp[comp>=i]
        d['comparator_delay_s']=float(t[lo[0]]-t[i]) if len(lo) else None
        d['comp_off_delay_s']=float(t[co[0]]-t[i]) if len(co) else None
    # Device current under absolute maximum is necessary, not sufficient for PASS.
    d['within_200mA_absolute_limit']=max(d['q21_peak_A'],d['q22_peak_A'],d['q25_peak_A'])<.2
    if c.get('limited'):d['status']='PROVISIONAL' if d['within_200mA_absolute_limit'] else 'FAIL'
    if c['id']=='limited_reset_stuck_recovery':
        d['unauthorized_restart_request']=bool(d['latch_end_V']<.5 and d['comp_end_V']>1.4)
        d['status']='FAIL' if d['unauthorized_restart_request'] else 'PROVISIONAL'
    if c['id']=='limited_power_cycle':
        d['power_cycle_clear_failed']=bool(d['latch_end_V']>2)
        d['status']='FAIL' if d['power_cycle_clear_failed'] else 'PROVISIONAL'
    return d

def protection(dest,selected=None):
    recovery='PWL(0 0 2m 170 8m 170 12m 230 18m 230 22m 170 40m 170)'
    cases=[dict(id='original_ramp'),dict(id='original_reset',hv=recovery,reset='PULSE(0 3.3 25m 1u 1u 2m 100m)'),
           dict(id='original_reset_stuck',reset='PWL(0 0 1m 3.3)'),
           dict(id='limited_ramp',limited=True),dict(id='limited_reset',limited=True,hv=recovery,reset='PULSE(0 3.3 25m 1u 1u 2m 100m)'),
           dict(id='limited_reset_stuck',limited=True,reset='PWL(0 0 1m 3.3)'),
           dict(id='limited_fast_sense',limited=True,c16=1e-9,rbot=19600),
           dict(id='limited_fast_late',limited=True,c16=1.2e-9,rbot=19404,rtop=1515000,ref=2.55,beta=40),
           dict(id='limited_fast_early',limited=True,c16=.8e-9,rbot=19796,rtop=1485000,ref=2.44,beta=200)]
    cases += [dict(id='limited_fast_small_comp',limited=True,c16=1e-9,rbot=19600,comp_cap=100e-9),
              dict(id='limited_reset_stuck_recovery',limited=True,hv=recovery,reset='PWL(0 0 1m 3.3)'),
              dict(id='limited_power_cycle',limited=True,hv=recovery,supply='PWL(0 0 100u 12 28m 12 28.01m 0 32m 0 32.01m 12 40m 12)'),
              dict(id='limited_initial_hv',limited=True,hv='170')]
    results=[]
    for c in cases:
        if selected and c['id'] not in selected:continue
        results.append(simulate(dest/c['id'],protection_deck(c),c.get('stop',.04),dict(stage='protection',case=c),lambda t,v:protection_metrics(c,t,v)))
    return results

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['controller','power','protection']);ap.add_argument('--run',required=True);ap.add_argument('--cases');args=ap.parse_args()
    if Path(args.run).name!=args.run: ap.error('single directory name required')
    dest=BASE/args.run;dest.mkdir(exist_ok=False)
    audit()
    selected=args.cases.split(',') if args.cases else None
    results={'controller':controller,'power':power,'protection':protection}[args.stage](dest,selected)
    if not results: raise ValueError('no matching cases')
    dump(dest/'results.json',{'stage':args.stage,'script_sha256':sha(Path(__file__)),'model_sha256':sha(MODEL),'results':results})
    return 0 if all(r['execution']=='PASS' for r in results) else 1

if __name__=='__main__': sys.exit(main())
