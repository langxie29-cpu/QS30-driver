"""startup_followup -- CORRECTED startup calculator (Round4, CODE ONLY; NOT executed by worker).
Fixes the Round3-review defect: the old calculator used P=6 W as if it were the 26.4 V input.
Symbols below are the exact prompt inputs. All numerics are emitted as executable numpy
arithmetic; this worker computes nothing by hand and makes NO simulator/model/shell call.
Writes ONE json next to this file (own folder only). No signoff, no threshold, no HOLD change.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

OUTDIR = Path(__file__).resolve().parent
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
OLD_TI = Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V/sources/TPS2660.txt')
STL = R2 / 'models/st.lib'
EV = R2 / 'evidence/principal/startup_bounds'

V = np.float64(26.4)         # worst fixed input voltage (prompt)
P = np.float64(6.0)          # required HV output power (prompt)
R = np.float64(33.0)         # series precharge resistor, nominal (prompt)
Iprog = np.float64(5.5e-6)   # dVdT programming current (prompt)
G = np.float64(25.5)         # dVdT-to-OUT gain, datasheet MAX (TPS2660.txt L453)
Cmin = np.float64(42.3e-9)   # dVdT capacitor, min (prompt)
V_BIAS = np.float64(1.0)     # V(ILIM) bias (TPS2660.txt L457)
FACT_V = np.float64(23.9)    # factory dVdT ramp (TPS2660.txt L1365)
FACT_T = np.float64(1.6e-3)  # factory ramp time, s (same line)

dvdt = Iprog * G / Cmin                  # V/s  (prompt fastest gain-limited rate)
rise = V / dvdt                          # s    0 -> V at that linear rate
PmaxVs = np.array([21.6, 24.0, 26.4]) ** 2 / (4.0 * R)   # W, max power transfer per VIN
load_A = P / V                           # A needed for 6 W at worst VIN
R_loss = load_A ** 2 * R                 # W lost in the series precharge element
R_for_6W = V ** 2 / (2.0 * P)            # ohm that would pass 6 W only if V/2 were available
factory_rate = FACT_V / FACT_T           # V/s
C_for_factory_rate = Iprog * G / factory_rate   # F, ramp cap that would reproduce factory rate


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def lit(x):
    return [float(v) for v in np.ravel(np.asarray(x, dtype=np.float64))]


def metrics(case):
    p = EV / case / 'metrics.json'
    m = json.loads(p.read_text(encoding='utf8')) if p.is_file() else {}
    m['src'] = f'evidence/principal/startup_bounds/{case}/metrics.json'
    return m


def num(x):
    """None-safe float for a copied literal (never invents a value)."""
    return None if x is None else float(x)


meas = {c: metrics(c) for c in ('uncontrolled', 'precharge', 'slew_corrected_7p962ms')}
raw_peak = meas['uncontrolled'].get('IL_peak_A')
budget_ceiling = (PmaxVs / np.float64(raw_peak)) if raw_peak else None   # V-equivalent per VIN
pre = meas['precharge']

res = {
    'task': 'startup_followup', 'role': 'startup_regression', 'executed_by_worker': False,
    'inputs': dict(V=lit(V), P=lit(P), R=lit(R), Iprog=lit(Iprog), G=lit(G), Cmin=lit(Cmin),
                   G_src='OLD/sources/TPS2660.txt L453 GAIN(dVdT) 23.75/24.6/25.5 V/V (MAX used)',
                   Iprog_src='prompt constant; not a TPS2660.txt current spec (see factory check)'),
    'dvdt_V_per_s': lit(dvdt), 'rise_0_to_V_s': lit(rise),
    'rise_note': 'rise = V/dvdt is the prompt LINEAR SOURCE-RAMP assumption, not native TPS26601 behaviour.',
    'Pmax_per_VIN_W': {f'{v:g}': float(p) for v, p in zip(lit(np.array([21.6, 24.0, 26.4])), lit(PmaxVs))},
    'load_current_for_6W_A': lit(load_A), 'series_R_loss_at_6W_W': lit(R_loss),
    'R_for_6W_if_half_Y_V_ohm': lit(R_for_6W),
    'factory_correspondence': dict(
        factory_rate_V_per_s=lit(factory_rate), factory_gain_vs_ILIM_bias_V=lit(G * V_BIAS),
        C_for_factory_rate_F=lit(C_for_factory_rate),
        ratio_Cmin_over_C_for_factory=lit(Cmin / C_for_factory_rate),
        note='Factory 23.9 V/1.6 ms with Iprog 5.5u and Gmax 25.5 needs C~9.386n, i.e. Cmin 42.3n is 4.5x '
             'larger, so the two datasheet/prompt-derived ramp numbers are inconsistent unless Cmin is '
             'not the ramp capacitor. UNRESOLVED: no native slew claim is made.'),
    'measured_copied_literals': meas,
    'uncontrolled_budget_ceiling_V': ({f'{v:g}': float(c) for v, c in
                                       zip(lit(np.array([21.6, 24.0, 26.4])), lit(budget_ceiling))}
                                      if budget_ceiling is not None else None),
    'budget_ceiling_note': 'PmaxVs/IL_peak(uncontrolled): the 6 W budget expressed as the equivalent '
                           'source voltage it can pay for at the copied passive peak. A ratio, not a converter result.',
    'precharge_copied': dict(bound_A=num(pre.get('bound_A')), energy_J=num(pre.get('precharge_energy_J')),
                             peak_W=num(pre.get('precharge_peak_W')),
                             caveat='copied literals only; part pulse rating, duration and bypass design remain HOLD.'),
    'permanent_R': dict(
        cannot_deliver_6W=True,
        reason='a permanent series R in the load path caps deliverable power at V^2/(4R); that ceiling is '
               'below the 6 W requirement at every VIN in the list (assertion max_Pmax_lt_6W) and the '
               'series element itself burns I^2*R of the budget.');
}
res['permanent_R']['assertions'] = dict(
    max_Pmax_lt_6W=bool(np.max(PmaxVs) < P), all_Pmax_lt_6W=bool(np.all(PmaxVs < P)),
    series_loss_positive=bool(np.all(R_loss > 0)), dvdt_positive=bool(np.all(dvdt > 0)),
    rise_finite_positive=bool(np.all(np.isfinite(rise) & (rise > 0))),
    load_finite_positive=bool(np.all(np.isfinite(load_A) & (load_A > 0))))
res['precharge_bypass'] = dict(
    hardware_missing=True, actual_device_MPN=None, bypass_model=None, max_delay=None,
    reason='no bypass device, MPN, bypass model or vendor MAXIMUM delay exists in the repository. '
           'MODE=open TPS26601 is circuit-breaker+latch (TPS2660.txt L170, L1717-L1719), not a continuous '
           'limiter, and every protection delay is TYP-only (L615, L635, L642, L644).')
res['source_hashes'] = {k: sha(v) for k, v in dict(
    tps2660_txt=OLD_TI, st_lib=STL,
    uncontrolled_metrics=EV / 'uncontrolled/metrics.json',
    precharge_metrics=EV / 'precharge/metrics.json',
    slew_corrected_metrics=EV / 'slew_corrected_7p962ms/metrics.json').items()}
res['numpy_version'] = np.__version__
res['solver'] = 'none (arithmetic only; principal executes)'

(OUTDIR / 'startup_calc_v2.json').write_text(json.dumps(res, indent=2) + '\n', encoding='utf8')
print(json.dumps(res['Pmax_per_VIN_W'], indent=1))
