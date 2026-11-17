"""Independent two-case counterexample: PWM-off passive Boost charging path."""
from pathlib import Path
import json, math, sys
from candidate_diagnostic import build,run,HERE,dump
from waveform_review import read_ascii

if __name__=='__main__':
    results=[]
    half='--halfstep' in sys.argv
    for name,rise in [('fast_1us',1e-6),('slow_1ms',1e-3)]:
        original_name=name
        if half:name+='_25ns'
        d=HERE/'evidence/passive_path'/name
        build(d,24,2.5e-8 if half else 5e-8,.002)
        p=d/'circuit.cir';s=p.read_text(encoding='ascii')
        s=s.replace('PWL(0 0 1m 24)','PWL(0 0 '+str(rise)+' 24)')
        s=s.replace('REN1 in en 200k\nREN2 en 0 12.8k','VEN en 0 0')
        p.write_text(s,encoding='ascii',newline='\n')
        pr=json.loads((d/'preregister.json').read_text())
        pr.update(scope='Passive path diagnostic ONLY, native controller SHDN held0; no autonomous switching or 170V claim',
                  source_ramp_s=rise,hypothesis='MOSFET peak-current comparator cannot interrupt passive input-L-diode-COUT current while gate is off',
                  analytic_lossless_step_peak_A=24*math.sqrt(20.3e-6/150e-6),
                  comparison='3.1A at25C/10% L drop is historical MSS1583 screening value, not a validated hot current limit. Crossing it invalidates linear L qualification.')
        dump(d/'preregister.json',pr)
        r=run(d,HERE/'evidence/toolchain_smoke/ltspice/result.json')
        if r['rc']==0 and (d/'circuit.raw').exists():
            c=read_ascii(d/'circuit.raw');il=c['i(lpower)'];v=c['v(hv)'];vg=[a-b for a,b in zip(c['v(gate)'],c['v(src)'])]
            r.update(name=name,endpoint_s=c['time'][-1],IL_peak_A=max(il),VOUT_initial_V=v[0],VOUT_peak_V=max(v),VGS_max_V=max(vg),
                     linear_3p1A_screen_exceeded=max(il)>3.1,
                     classification='ELECTRICAL_FAIL' if max(il)>3.1 else 'LIMITED_PASS',
                     limitation='Only specified passive-path fixture; no eFuse, nonlinear hot L, active startup, 170V loop or hardware approval')
        else:r.update(name=name,classification=r.get('classification','SOLVER_FAIL'))
        if half and 'IL_peak_A' in r:
            old=json.loads((HERE/'evidence/passive_path'/original_name/'metrics.json').read_text())
            r['halfstep_comparison']=dict(IL_peak_delta_A=abs(r['IL_peak_A']-old['IL_peak_A']),VOUT_peak_delta_V=abs(r['VOUT_peak_V']-old['VOUT_peak_V']),
                criterion='Passive path peak reproducibility: IL difference<=0.01A and VOUT difference<=0.1V; separate from HV acceptance',
                passed=abs(r['IL_peak_A']-old['IL_peak_A'])<=.01 and abs(r['VOUT_peak_V']-old['VOUT_peak_V'])<=.1)
        dump(d/'metrics.json',r);results.append(r)
    dump(HERE/'evidence/passive_path'/('results_halfstep.json' if half else 'results.json'),results)
    print(json.dumps(results,indent=2))
