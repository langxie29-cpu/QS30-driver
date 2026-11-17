"""passive_bounds runner v2. Exactly six preregistered single-variable diagnostic runs.
Uses shared lab.py (lab.full + lab.execute). Only writes inside OUTPUT_DIR/runs/.
Policy B (approved): every run removes the REN1/REN2 divider and holds controller SHDN at 0 V as
the prerequisite context demands; then the ONE preregistered variable per case is applied.
"""
import sys, json
from pathlib import Path
import numpy as np

R2 = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
sys.path.insert(0, str(R2))
import lab

OUT = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_01/passive_bounds')
RUNS = OUT / 'runs'
STOP, STEP, METHOD, TIMEOUT = 0.003, 5e-8, 'gear', 30
SHDN = ('REN1 in en 200k\nREN2 en 0 12.8k', 'VEN en 0 0')

RUNS_DEF = [
    dict(name='p1_fast_24V',
         hypothesis='Prerequisite cell with SHDN held 0, 24V and a source ramp fast enough (50ns) to keep the linear-divider limit the binding constraint: reference for the passive clamp',
         variable='SHDN hold only: REN1/REN2 divider -> VEN en 0 0 (no other change)',
         edits=[SHDN]),
    dict(name='p2_slow_1ms',
         hypothesis='A 1ms linear source ramp keeps the cell in the divider-limited regime instead of the ringing regime and lowers peak passive charging current',
         variable='VINPUT ramp 50ns -> 1ms (source slew only); SHDN hold is the task prerequisite',
         edits=[SHDN, ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1m 24)')]),
    dict(name='p3_fast_vin_26p4',
         hypothesis='Source tolerance corner: +10% plateau (26.4V) scales the passive charging stress of the same fast cell proportionally to VIN',
         variable='VINPUT plateau 24V -> 26.4V (source voltage only); SHDN hold is the task prerequisite',
         edits=[SHDN, ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1m 26.4)')]),
    dict(name='p4_fast_rinput_1ohm',
         hypothesis='Larger input series resistance reduces the passive inrush peak by increasing the divider share, at the cost of source drop',
         variable='RINPUT .1ohm -> 1ohm (input series resistance only); SHDN hold is the task prerequisite',
         edits=[SHDN, ('RINPUT vin in .1', 'RINPUT vin in 1')]),
    dict(name='p5_fast_cout_24p36',
         hypothesis='+20% HV output capacitance raises the passive clamp voltage and the charge stored per amp of peak current',
         variable='COUT 20.3uF -> 24.36uF (output capacitance only); SHDN hold is the task prerequisite',
         edits=[SHDN, ('COUT hv 0 20.3u', 'COUT hv 0 24.36u')]),
    dict(name='p6_fast_lpower_135u',
         hypothesis='-10% inductance raises di/dt and therefore the current reachable by the same passive stimulus',
         variable='LPOWER 150uH -> 135uH (inductance only, Rser .16 unchanged); SHDN hold is the task prerequisite',
         edits=[SHDN, ('LPOWER in drain 150u', 'LPOWER in drain 135u')]),
]

RDS_ON = {24: 0.45, 26.4: 0.45}  # STP9NK50Z linear-model Rds at 25C, informational only


def measure(path, vin_plateau):
    c = lab.native(path / 'circuit.raw')
    t = c['time']; v = c['v(hv)']; il = c['i(lpower)']; vin = c['v(in)']
    vpk = int(np.argmax(v)); ipk = int(np.argmax(il))
    seg_end = vpk
    thr10, thr90 = .1 * v[vpk], .9 * v[vpk]
    def cross(thr):
        idx = np.nonzero(v[:seg_end + 1] >= thr)[0]
        return float(t[idx[0]]) if idx.size else float('nan')
    t10, t90 = cross(thr10), cross(thr90)
    dtv = np.gradient(v, t)
    # divider share at the source-plateau level using nominal 25C linear-model resistances
    rsrc = 0.1 if 'p4' not in path.name else 1.0
    if rsrc == 1.0:
        pass
    z = rsrc + 0.16 + RDS_ON[24] + 0.062
    share = rsrc / z
    return dict(t_end=float(t[-1]), n_points=len(t),
                vin_final=float(vin[-1]),
                t_peak_vout=float(t[vpk]), vout_peak=float(v[vpk]),
                t_peak_il=float(t[ipk]), il_peak=float(il[ipk]),
                il_rms=float(np.sqrt(np.mean(il ** 2))),
                il_energy_J=float(0.5 * 150e-6 * il[ipk] ** 2),
                vout_at_1ms=float(np.interp(1e-3, t, v)),
                vout_at_2ms=float(np.interp(2e-3, t, v)),
                vout_final=float(v[-1]), il_final=float(il[-1]),
                il_at_vout_peak=float(il[vpk]),
                dvdt_1090_V_per_s=float(0.8 * v[vpk] / (t90 - t10)) if t90 > t10 else None,
                dvdt_max_V_per_s=float(dtv.max()),
                divider_share_nominal=share,
                ideal_peak_A=float(vin_plateau * np.sqrt(20.3e-6 / 150e-6)),
                raw_sha256=lab.sha(path / 'circuit.raw'))


RES = []
LABEL = 'FINAL'
SUF = '_' + LABEL
EDITS = {  # the single approved per-run variable edit, applied on top of the SHDN hold
    'ramp1ms': ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1m 24)'),
    'rise50n': ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 50n 24)'),
    'plateau': ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1m 26.4)'),
    'rinput': ('RINPUT vin in .1', 'RINPUT vin in 1'),
    'cout': ('COUT hv 0 20.3u', 'COUT hv 0 24.36u'),
    'lpower': ('LPOWER in drain 150u', 'LPOWER in drain 135u'),
}
RUNS_DEF = [
    dict(name='p1_fast_24V', key='rise50n',
         hypothesis='Prerequisite cell, SHDN held 0, 24V, source rise 50ns (fast relative to the L/C ringing mode so the linear divider limit is the binding constraint)',
         variable='SHDN hold: REN1/REN2 divider -> VEN en 0 0, plus source rise 1ms -> 50ns (source slew only)',
         edits=[SHDN, EDITS['rise50n']]),
    dict(name='p2_slow_1ms', key='ramp1ms',
         hypothesis='A 1ms linear source ramp keeps the cell in the divider-limited regime instead of the ringing regime and lowers the peak passive charging current',
         variable='SHDN hold only: VEN en 0 0 with the 1ms source ramp unchanged (no other change)',
         edits=[SHDN, EDITS['ramp1ms']]),
    dict(name='p3_fast_vin_26p4', key='plateau',
         hypothesis='Source tolerance corner: +10% plateau (26.4V) scales the passive charging stress of the same fast cell',
         variable='SHDN hold: VEN en 0 0, plus source plateau 24V -> 26.4V (source voltage only)',
         edits=[SHDN, EDITS['plateau']]),
    dict(name='p4_fast_rinput_1ohm', key='rinput',
         hypothesis='Larger input series resistance reduces the passive inrush peak by increasing the divider share, at the cost of source drop',
         variable='SHDN hold: VEN en 0 0, plus RINPUT .1ohm -> 1ohm (input series resistance only)',
         edits=[SHDN, EDITS['rinput']]),
    dict(name='p5_fast_cout_24p36', key='cout',
         hypothesis='+20% HV output capacitance raises the passive clamp voltage and the charge stored per amp of peak current',
         variable='SHDN hold: VEN en 0 0, plus COUT 20.3uF -> 24.36uF (output capacitance only)',
         edits=[SHDN, EDITS['cout']]),
    dict(name='p6_fast_lpower_135u', key='lpower',
         hypothesis='-10% inductance raises di/dt and therefore the current reachable by the same passive stimulus',
         variable='SHDN hold: VEN en 0 0, plus LPOWER 150uH -> 135uH (inductance only, Rser .16 unchanged)',
         edits=[SHDN, EDITS['lpower']]),
]
only = sys.argv[1:] or None
RES = []
for d in RUNS_DEF:
    if only and d['name'] not in only:
        continue
    p = RUNS / (d['name'] + SUF)
    if (p / 'preregister.json').exists() or (p / 'circuit.raw').exists():
        raise SystemExit('refuse to overwrite existing experiment: ' + str(p))
    lab.full(p, stop=STOP, step=STEP, method=METHOD)
    cir = (p / 'circuit.cir').read_text(encoding='ascii')
    for old, new in d['edits']:
        if cir.count(old) != 1:
            raise SystemExit(f'anchor not unique/missing in {p.name}: {old!r}')
        cir = cir.replace(old, new)
    (p / 'circuit.cir').write_text(cir, encoding='ascii')
    cmd = lab.execute(p, d['hypothesis'], d['variable'], timeout=TIMEOUT)
    pr = json.loads((p / 'preregister.json').read_text())
    assert pr['unique_main_variable'] == d['variable'] and '.tran 5e-08 0.003 0 5e-08 uic' in cir
    assert 'VEN en 0 0' in cir and 'REN1' not in cir, 'SHDN not held'
    m = dict(name=d['name'], artifact_dir=p.name, variable=d['variable'], hypothesis=d['hypothesis'], edits=[[a, b] for a, b in d['edits']],
             rc=cmd['rc'], status=cmd['status'], elapsed_s=cmd['elapsed_s'], timeout_s=TIMEOUT,
             netlist_sha256=pr['netlist_sha256'], tran=pr['tran'], options=pr['options'],
             model_hashes=pr['model_hashes'], solver=pr['solver'])
    log = (p / 'circuit.log')
    txt = log.read_text(errors='replace') if log.exists() else ''
    m['log_tail'] = txt.strip().splitlines()[-4:]
    m['solver_steps_raised_defcon'] = txt.count('Heightened Def Con')
    if (p / 'circuit.raw').exists() and cmd['rc'] == 0:
        m.update(measure(p, 26.4 if 'p3' in d['name'] else 24.0))
    (p / 'derived.json').write_text(json.dumps(m, indent=2) + '\n', encoding='utf8')
    RES.append(m)
    print(json.dumps({k: m.get(k) for k in ['name', 'rc', 'status', 'elapsed_s', 'il_peak', 't_peak_il', 'vout_peak',
                                            't_peak_vout', 'vout_final', 'il_final', 'il_energy_J', 'dvdt_1090_V_per_s',
                                            'dvdt_max_V_per_s', 'divider_share_nominal', 'ideal_peak_A',
                                            'solver_steps_raised_defcon', 'log_tail']}, indent=1))

idx = RUNS / ('raw_index' + SUF + '.json')
prev = json.loads(idx.read_text()) if idx.exists() else []
keep = {m['name']: m for m in prev}
keep.update({m['name']: m for m in RES})
idx.write_text(json.dumps([keep[d['name']] for d in RUNS_DEF if d['name'] in keep], indent=2) + '\n', encoding='utf8')
print('DONE', len(RES))
