"""A9.2 genuine ngspice runs. Append-only run directories, including failures.

Functional UC3843 / LM393 / TL431 equivalents, generic Gummel-Poon BJTs.
Physical nodes/values are read from the captured native XML and matching CSV.
These are diagnostic models, NOT vendor-qualified protection signoff models.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import re

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reconcile9 import xml_nets

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'


def build_deck(native, rows, scenario):
    nodes, _, _ = xml_nets(native)
    parts = {}
    for r in rows:
        parts.setdefault(r['ref'], r)
    def n(ref, pin):
        net = nodes[(ref,str(pin))]
        return '0' if net == 'GND' else net
    def line(ref, value=None):
        r = parts[ref]
        pins = sorted((p for rr,p in nodes if rr==ref),key=lambda s:(len(s),s))
        val = value or r['mpn'].split('/')[0]
        if val.startswith('2x100k'): val = '200k'
        return f'{ref} ' + ' '.join(n(ref,p) for p in pins) + ' ' + val
    vin = scenario.get('vin',12)
    mode = scenario.get('mode','boost')
    tube_count = scenario.get('tubes',9)
    trip = scenario.get('trip',False)
    beta = scenario.get('beta',100)
    stop = scenario.get('stop',.08 if mode=='boost' else .04)
    lines = [f'QS30 A9.2 diagnostic {scenario["id"]}',
             '* Generated from native netlist; see manifest and MODEL_LIMITS.md',
             '.options reltol=0.003 abstol=1n vntol=10u method=gear itl4=200',
             f'.param beta={beta}',
             '.model NGEN NPN(IS=6.7f BF={beta} VAF=75 IKF=.1 ISE=6.7f NE=1.5 BR=4 RB=10 RC=1 RE=.5 CJE=4p CJC=3p TF=.3n TR=100n)',
             '.model PGEN PNP(IS=14f BF={beta} VAF=50 IKF=.1 BR=4 RB=10 RC=1 RE=.5 CJE=5p CJC=4p TF=.5n TR=100n)',
             '.model UFGEN D(IS=10n N=1.5 RS=.5 CJO=15p TT=75n BV=1000 IBV=5u)',
             '.model SCHGEN D(IS=200n N=1.05 RS=2 CJO=10p BV=30 IBV=2u)',
             '.model P_SW SW(RON=.098 ROFF=1g VT=2 VH=.05)',
             '.model N_SW SW(RON=.55 ROFF=1g VT=2.5 VH=.1)',
             f'VIN input 0 PWL(0 0 100u {vin})',
             # Test fixture source impedance, NOT present as a schematic resistor.
             'R_FIXTURE input EXT12 .5',
             'V3V3 3V3 0 PWL(0 0 500u 3.3)',
             'VREQUEST HV_EN_REQ 0 PWL(0 0 1m 0 1.001m 3.3)',
             'RSTAR GND_HV 0 .001']
    if scenario.get('vin_step'):
        lines[lines.index(f'VIN input 0 PWL(0 0 100u {vin})')] = 'VIN input 0 PWL(0 0 100u 11.4 25m 11.4 25.01m 12.6)'
    reset = scenario.get('reset','none')
    lines += ['VRST OVP_RST 0 ' + {'none':'0','pulse':'PULSE(0 3.3 25m 1u 1u 2m 100m)',
                                 'stuck':'PWL(0 0 1m 3.3)'}[reset]]
    # Reproduce actual supply/reference, monitor and latch resistor networks.
    refs = ['R17','R18','R19','C8','R20','R21','R22','R23','R24',
            'R25','R26','R27','R28','R29','R30','R38','R38B',
            'R40','R41','R42','C16','R43','R44','R45','R46','R47','R48',
            'R49','R50','R51','R52','R53','R15','R16',
            'R_Q5_BE','R_Q3_BE','R_HV_REQ_PD','R39']
    for ref in refs:
        if ref not in parts: continue
        value = None
        if ref=='C16': value = scenario.get('c16')
        if ref=='R41': value = scenario.get('rtop')
        if ref=='R42': value = scenario.get('rbot')
        lines.append(line(ref,value))
    for u in ('U6','U24'):
        refvalue = scenario.get('ref',2.495) if u=='U24' else 2.495
        node = n(u,1)
        lines += [f'B{u}_SHUNT {node} 0 I=max((v({node})-{refvalue})/.2,0)',
                  f'C{u}_PAR {node} 0 100p']
    # LM393: open collector, 50-ohm saturated sink approximation; 1 us pole.
    def comparator(label,out,minus,plus):
        supply = 'EXT12' if label=='OVP' else '3V3'
        lines.extend([f'B{label}_DIFF {label}_raw 0 V=v({plus})-v({minus})',
                      f'R{label}_DELAY {label}_raw {label}_ctl 1k',
                      f'C{label}_DELAY {label}_ctl 0 1n',
                      f'B{label}_OUT {out} 0 I=(v({supply})>2 && v({label}_ctl)<0) ? max(v({out}),0)/50 : 0'])
    comparator('OVP',n('U23',1),n('U23',2),n('U23',3))
    comparator('DPG','DRV_PG','VREF_1V0','DRV_SNS')
    comparator('FOK','FAULT_OK','VREF_1V0','HVF_NODE')
    comparator('EPG','EXT12_PG','VREF_1V0','EXT12_SNS')
    comparator('3PG','P3V3_PG','VREF_1V0','P3V3_SNS')
    lines += [f'D4_LOWER {n("D4",1)} {n("D4",3)} SCHGEN',
              f'D4_UPPER {n("D4",3)} {n("D4",2)} SCHGEN']
    for ref, model in [('Q21','PGEN'),('Q22','NGEN'),('Q23','NGEN'),('Q24','NGEN'),('Q25','NGEN'),('Q5','NGEN'),('Q3','NGEN')]:
        lines.append(f'{ref} {n(ref,3)} {n(ref,1)} {n(ref,2)} {model}')
    lines += ['C_Q4_GATE HV_EN_G EXT12 1n','C_Q2_GATE DRV_VDD_G EXT12 1n',
              'S_Q4 HV_IN EXT12 EXT12 HV_EN_G P_SW',
              'S_Q2 DRV_VDD EXT12 EXT12 DRV_VDD_G P_SW',
              'R_HVIN_LOAD HV_IN 0 20k','C_HVIN HV_IN 0 1u',
              'R_DRV_LOAD DRV_VDD 0 5k','C_DRV DRV_VDD 0 1u',
              'B_DRV_EN DRV_VDD_EN 0 V=(v(EXT12_PG)>2 && v(P3V3_PG)>2 && v(HV_EN_REQ)>2) ? v(3V3) : 0',
              'B_HV_EN HV_EN 0 V=(v(DRV_PG)>2 && v(FAULT_OK)>2 && v(HV_EN_REQ)>2 && v(3V3)>3) ? v(3V3) : 0']
    # Exact physical UC reference clash / RT load and COMP compensation.
    for ref in ['R31','R32','C9','R37','C14','C15']:
        lines.append(line(ref)+(' IC=4' if ref=='C15' and scenario.get('precharge_comp') else ''))
    lines += ['.model UV_SW SW(RON=1 ROFF=1g VT=8 VH=.4)',
              'V_ONE ONE 0 1','S_UVLO ONE UC_OK HV_IN 0 UV_SW','R_UVLO UC_OK 0 1k',
              'C_UCREF_INTERNAL VREF_UC 0 10n',
              'B_UCREF 0 VREF_UC I=(v(UC_OK)>.5) ? min(max((5-v(VREF_UC))/.1,0),.05) : 0',
              'R_UCREF_LEAK VREF_UC 0 100k',
              f'B_U21 {n("U21",1)} 0 I=max((v({n("U21",1)})-2.495)/.2,0)',
              'B_COMP 0 COMP_N I=(v(UC_OK)>.5) ? min(max((2.5-v(FB_HV))*.002,-.0005),.0005) : 0',
              'R_COMP_LEAK COMP_N 0 1meg']
    # Switching power stage with 220 uH, feedthrough cap, exact erroneous CS net.
    lines += ['R_L_DCR HV_IN L_IN .3','L20 L_IN SW_HV 220u',
              'S_Q20 SW_HV 0 HV_GATE 0 N_SW','D20 SW_HV HV_BUS UFGEN',
              line('C10'),line('C11'),line('C12'),line('R33'),
              # All three 0.1u/200k module branches connected in the fixture.
              'C_MODULES HV_BUS GND_HV 300n','R_MODULES HV_BUS GND_HV 66.6666667k',
              line('R36'),line('C13')]
    fb = scenario.get('feedback','normal')
    lines += [line('R34','1e15' if fb=='top_open' else None),
              line('R35','1m' if fb=='bottom_short' else None)]
    # Functional current comparator + oscillator. 78 kHz is assumed, not proved
    # by this model. Output disabled below UVLO or bad internal 5 V reference.
    # This macro does not model the exact PWM SR latch / slope compensation.
    lines += ['B_RAMP RAMP 0 V=(time*78000-floor(time*78000))',
              'B_UCOUT HV_GATE 0 V=(v(UC_OK)>.5 && v(VREF_UC)>4.5 && v(COMP_N)>1.4 && v(CS_FILT)<min(max((v(COMP_N)-1.4)/3,0),1) && v(RAMP)<.92) ? 10 : 0']
    # Voltage-dependent 9 independent 20k anode equivalents with 125 V glow.
    # Deliberately no assertion of ignition/hysteresis validation.
    for t in range(1,10):
        count = f'({tube_count})'
        if scenario.get('load_step'): count = '(time<25m ? 6 : 9)'
        lines.append(f'B_TUBE{t} HV_BUS 0 I=({t}<={count}) ? max((v(HV_BUS)-125)/20000,0) : 0')
    if mode=='injection':
        # A specified external fault source replaces converter energy in this
        # subsystem experiment. Its current is saved; it is NOT a boost result.
        if scenario.get('recover'):
            waveform='PWL(0 0 2m 170 8m 170 12m 230 18m 230 22m 170 40m 170)'
        elif scenario.get('initial_hv'):
            waveform='PWL(0 230 40m 230)'
        else: waveform='PWL(0 0 2m 170 8m 170 16m 230 40m 230)'
        lines += [f'VFAULT HV_BUS 0 {waveform}']
    if scenario.get('poweroff'):
        lines = [x if not x.startswith('VIN ') else f'VIN input 0 PWL(0 0 100u {vin} 20m {vin} 20.01m 0)' for x in lines]
    if scenario.get('mcu_off'):
        lines = [x if not x.startswith('V3V3 ') else 'V3V3 3V3 0 PWL(0 0 500u 3.3 20m 3.3 20.01m 0)' for x in lines]
    vectors = 'v(HV_BUS) v(OVP_SNS) v(VREF_OVP) v(OVP_SET) v(LATCH_B) v(OVP_LATCH) v(COMP_N) v(HV_EN) v(HV_EN_G) v(HV_IN) v(DRV_VDD) v(CS_FILT) i(L20) @q21[ic] @q22[ic] @q25[ic] v(VREF_UC) v(HV_GATE) i(VIN)'
    lines += ['.save all @q21[ic] @q22[ic] @q25[ic]', '.control','set noaskquit','set wr_singlescale','set wr_vecnames',
              f'tran 10u {stop} 0 1u uic',
              'meas tran q21_peak MIN @q21[ic]',
              'meas tran q22_peak MAX @q22[ic]',
              'meas tran hv_peak MAX v(HV_BUS)',
              'meas tran end_time MAX time',
              'linearize '+vectors,
              'wrdata waves.txt '+vectors,
              'quit','.endc','.end']
    return '\n'.join(lines)+'\n'


def scenarios():
    return [dict(id='startup_9',mode='boost'), dict(id='startup_no_load',tubes=0),
            dict(id='startup_6',tubes=6), dict(id='input_11_4',vin=11.4),
            dict(id='input_12_6',vin=12.6),dict(id='line_step',vin_step=True),
            dict(id='six_to_nine',load_step=True),dict(id='feedback_top_open',feedback='top_open'),
            dict(id='feedback_bottom_short',feedback='bottom_short'),
            dict(id='ovp_ramp',mode='injection'),
            dict(id='ovp_initial',mode='injection',initial_hv=True),
            dict(id='latch_recovery',mode='injection',recover=True,reset='pulse'),
            dict(id='reset_stuck',mode='injection',reset='stuck'),
            dict(id='corner_late',mode='injection',rtop='1515k',rbot='18.909k',ref=2.55,beta=40,c16='120n'),
            dict(id='corner_early',mode='injection',rtop='1485k',rbot='19.291k',ref=2.44,beta=200,c16='80n'),
            dict(id='mcu_poweroff',mode='injection',mcu_off=True),
            dict(id='input_poweroff',mode='boost',poweroff=True)]


def execution_ok(log, stop, rc, wave_exists):
    endpoint=re.search(r'end_time\s*=\s*([\d.eE+-]+)',log)
    complete=endpoint and abs(float(endpoint[1])-stop)<1e-6
    return wave_exists and bool(complete) and 'No. of Data Rows' in log and not any(x in log.lower() for x in ['error:', 'aborted', 'timestep too small', 'failed!']) and rc==0


def run(run_name, native_run, csv_path, precharged=False, selected_cases=None):
    dest = ROOT/'sim/a9_2'/run_name
    dest.mkdir(exist_ok=False)
    native = ROOT/'kicad/logs'/native_run/'QS30-9_MAIN.xml'
    csvfile = ROOT/csv_path
    rows = list(csv.DictReader(csvfile.open(encoding='utf-8-sig')))
    manifest = dict(native=str(native.relative_to(ROOT)),csv=str(csvfile.relative_to(ROOT)),
                    sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (native,csvfile,EXE,Path(__file__))},results=[])
    cases=scenarios()
    if precharged:
        cases=[dict(c,precharge_comp=True,stop=.06) for c in cases if c.get('mode')=='injection']
    if selected_cases:
        cases=[c for c in cases if c['id'] in selected_cases]
        if len(cases)!=len(selected_cases):raise ValueError('unknown or incompatible selected cases')
    for case in cases:
        folder = dest/case['id'];folder.mkdir()
        (folder/'circuit.cir').write_text(build_deck(native,rows,case),encoding='ascii')
        argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']
        try:
            p=subprocess.run(argv,cwd=folder,capture_output=True,text=True,errors='replace',timeout=55)
            rc,stdout,stderr=p.returncode,p.stdout,p.stderr
        except subprocess.TimeoutExpired as e:
            rc,stdout,stderr='TIMEOUT',str(e.stdout),str(e.stderr)
        record=dict(scenario=case,argv=argv,rc=rc,stdout=stdout,stderr=stderr)
        (folder/'command.json').write_text(json.dumps(record,indent=2)+'\n')
        log=(folder/'ngspice.log').read_text(errors='replace') if (folder/'ngspice.log').exists() else ''
        wave=folder/'waves.txt'
        valid=execution_ok(log,case.get('stop',.08 if case.get('mode','boost')=='boost' else .04),rc,wave.exists())
        record['execution']='PASS' if valid else 'FAIL'
        if valid:
            data=np.loadtxt(wave,skiprows=1)
            headers=wave.read_text().splitlines()[0].split()
            t=data[:,0]
            def v(name): return data[:,[h.lower() for h in headers].index(name.lower())]
            metrics = dict(t_end_s=float(t[-1]),hv_peak_V=float(v('v(HV_BUS)').max()),
                           hv_end_V=float(v('v(HV_BUS)')[-1]),
                           hv_in_peak_V=float(v('v(HV_IN)').max()),
                           q21_ic_abs_peak_A=float(np.abs(v('@Q21[ic]')).max()),
                           q22_ic_abs_peak_A=float(np.abs(v('@Q22[ic]')).max()),
                           q25_ic_abs_peak_A=float(np.abs(v('@Q25[ic]')).max()),
                           comp_min_after_15ms_V=float(v('v(COMP_N)')[t>.015].min()),
                           vref_uc_peak_V=float(v('v(VREF_UC)').max()),
                           cs_peak_V=float(v('v(CS_FILT)').max()),
                           il_peak_A=float(np.abs(v('i(L20)')).max()))
            if case.get('mode')=='injection':
                trip=np.flatnonzero((t>.008)&(v('v(OVP_SNS)')>v('v(VREF_OVP)')))
                low=np.flatnonzero((t>.008)&(v('v(OVP_SET)')<.5))
                metrics['sense_crossing_s']=float(t[trip[0]]) if len(trip) else None
                metrics['out_low_s']=float(t[low[0]]) if len(low) else None
                metrics['latch_end_V']=float(v('v(OVP_LATCH)')[-1])
                metrics['comp_end_V']=float(v('v(COMP_N)')[-1])
            record['metrics']=metrics
            record['protection_signoff']='FAIL' # Known unresolved CS/latch topology; no all-corner qualification.
            fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True)
            for name in ['v(HV_BUS)','v(HV_IN)','v(DRV_VDD)']:axs[0].plot(t*1e3,v(name),label=name)
            for name in ['v(OVP_SNS)','v(VREF_OVP)','v(OVP_SET)','v(OVP_LATCH)','v(COMP_N)']:axs[1].plot(t*1e3,v(name),label=name)
            for name in ['@Q21[ic]','@Q22[ic]','@Q25[ic]','i(L20)']:axs[2].plot(t*1e3,v(name),label=name)
            for ax in axs:ax.legend(fontsize=7);ax.grid();ax.set_ylabel('V' if ax!=axs[2] else 'A')
            axs[2].set_xlabel('time (ms)');fig.suptitle(f'{run_name}: {case["id"]} — diagnostic equivalent, NOT signoff')
            fig.tight_layout();fig.savefig(folder/'waveforms.png',dpi=125);plt.close(fig)
            # CSV is portable; retain full numeric wave data compressed losslessly.
            import gzip
            with gzip.open(folder/'waves.csv.gz','wt',encoding='utf8',newline='') as f:
                np.savetxt(f,data,delimiter=',',header=','.join(headers),comments='')
            # Keep raw ngspice output as well; no failed evidence is removed.
        manifest['results'].append(record)
        (dest/'results.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(run_name,case['id'],rc,record['execution'],record.get('metrics',{}),flush=True)
    return manifest


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--native-run',required=True)
    ap.add_argument('--csv',default='netlist9/QS30-9_REV.A_netlist.csv');ap.add_argument('--precharged',action='store_true')
    ap.add_argument('--cases',help='comma-separated diagnostic case IDs');a=ap.parse_args()
    if Path(a.run).name!=a.run:ap.error('run must be a single new directory name')
    run(a.run,a.native_run,a.csv,a.precharged,a.cases.split(',') if a.cases else None)
