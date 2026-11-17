"""startup_candidate — post-hoc measurement of the three approved case raws (DRAFT ONLY).

EXECUTION IS FORBIDDEN IN THIS SESSION. It exists separately from `build_startup.py` on purpose:
the approved quantities are fixed HERE, before any raw is produced, so that reading the data can
never influence what was run. The principal runs `build_startup.py` first, then this file.

Properties that are mandatory for this file:
  * It NEVER simulates. Only `lab.native` (uncompressed memmap reader, read-only) is imported.
  * It NEVER invents a value. Every quantity is either measured from a complete raw, or written
    as `null` with a `status` explaining why it could not be measured.
  * It NEVER changes an acceptance threshold. The limits are read verbatim from the run's own
    `preregister.json` (`acceptance`), which `lab.execute` filled from `lab.py`.
  * "Evaluable" is decided before looking at the numbers: with the gate inhibited in all three
    approved cases, the converter cannot switch, so `fault_peak_V` and `ripple_Vpp` have no valid
    domain here and are NOT EVALUABLE by construction, not by convenience.
"""
import json, sys
from pathlib import Path

R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
OUT = Path(__file__).resolve().parent
RUNS = OUT / 'runs'
sys.path.insert(0, str(R2))

if __name__ != '__main__':
    raise SystemExit('measure_startup.py is a draft; do not import it.')
import numpy as np          # noqa: E402
import lab                  # noqa: E402  (lab.native only; lab.execute is never called)

CASES = ['startup_A_uncontrolled_ref', 'startup_B_precharge_33ohm', 'startup_C_slow_slew_8p49ms']
VIN_SET = 26.4
COUT, LPOW = 24.36e-6, 135e-6
# Analytic lossless bound, FROZEN before execution (see inventory.md section 4):
BOUND_V_PK = VIN_SET * (COUT / LPOW) ** 0.5


def measure(path):
    c = lab.native(path / 'circuit.raw')
    t = c['time']
    v = c['v(hv)']
    if t[-1] < 0.98 * 0.01008:
        return dict(status='TRACE_INCOMPLETE', t_end=float(t[-1]))
    vin = c['v(in)'] if 'v(in)' in c else None
    il = c['i(lpower)'] if 'i(lpower)' in c else None
    i_src = c['i(rsrc)'] if 'i(rsrc)' in c else None

    def at(te, y):
        return float(np.interp(te, t, y)) if y is not None else None

    # Cumulative charge delivered into the power path, from the source-side entry point only.
    q = (float(np.trapezoid(i_src, t)) if i_src is not None else None)
    out = dict(
        status='MEASURED',
        t_end=float(t[-1]),
        n_points=int(len(t)),
        vin_final_V=at(1e-3, vin),
        vin_plateau_reached=bool(vin is not None and abs(float(vin[-1]) - VIN_SET) < 0.05 * VIN_SET),
        v_hv_peak_V=float(v.max()),
        t_v_hv_peak_s=float(t[int(np.argmax(v))]),
        v_hv_final_V=float(v[-1]),
        i_lpower_peak_A=float(il.max()) if il is not None else None,
        t_i_lpower_peak_s=float(t[int(np.argmax(il))]) if il is not None else None,
        i_lpower_final_A=at(t[-1], il),
        i_rsrc_peak_A=float(i_src.max()) if i_src is not None else None,
        charge_in_C=q,
        v_hv_10pct_bound_s=None, v_hv_90pct_bound_s=None,
        bound_v_peak_V=BOUND_V_PK,
        bound_exceeded=(float(v.max()) > BOUND_V_PK * 1.15),
    )
    # Time to reach 10 % / 90 % of the FROZEN analytic bound: a fixed ruler, so cases are
    # comparable even though their peaks differ. Not a settling claim.
    for frac, key in ((0.1, 'v_hv_10pct_bound_s'), (0.9, 'v_hv_90pct_bound_s')):
        thr = frac * BOUND_V_PK
        idx = np.nonzero(v >= thr)[0]
        out[key] = float(t[idx[0]]) if idx.size else None
    # Residual against the frozen bound: >1.15 would mean the frozen arithmetic inputs disagree
    # with the executed netlist (e.g. wrong corner) and the run must be re-read, not reinterpreted.
    out['bound_ratio'] = float(v.max()) / BOUND_V_PK
    return out


def assertions(m, lim):
    """Explicit test assertions. `EVALUABLE` is decided structurally, before the numbers."""
    # Re-asserted in main() before this function is reached; reaching here implies it held.
    gate_inhibited = True
    a = {
        'trace_complete_to_10ms': dict(test='t_end >= 0.98 * 0.01008',
                                       value=m.get('t_end'), passed=m.get('status') == 'MEASURED'),
        'gate_inhibit_held': dict(test='circuit.cir contains VEN en 0 0 and no REN1',
                                  passed=gate_inhibited),
        'v_hv_peak_vs_analytic_bound': dict(
            test='v_hv_peak <= 1.15 * VIN*sqrt(COUT/L) (frozen bound, lossless upper bound)',
            value=m.get('v_hv_peak_V'), bound_v=BOUND_V_PK,
            passed=(m.get('bound_exceeded') is False) if m.get('status') == 'MEASURED' else None),
        'fault_peak_V_le_195': dict(
            test=f'v_hv peak <= {lim["fault_peak_V"]} V',
            evaluable=False,
            reason='gate inhibited in all three approved cases: the converter cannot switch, so '
                   'the 195 V ceiling has no domain. Not evaluable is NOT a pass.'),
        'ripple_Vpp_le_1V': dict(
            test=f'ripple <= {lim["ripple_Vpp"]} Vpp',
            evaluable=False, reason='no switching in the approved cases; ripple undefined.'),
        'normal_mean_165_175V': dict(
            test='time-weighted V(hv) mean in 164.9..175.1',
            evaluable=False, reason='regulated steady state is not reachable with the gate inhibited.'),
        'startup_within_1s': dict(
            test=f'startup <= {lim["startup_s"]} s',
            evaluable=False, reason='passive arrival only; the regulated converter never starts here.'),
        'sense_abs_le_0p3V': dict(
            test=f'|V(sense)| <= {lim["sense_abs_V"]} V',
            evaluable=False,
            reason='out of scope for startup_candidate; the SENSE filter candidate is a separate '
                   'Round2 task.'),
    }
    return a


def main():
    idx_path = RUNS / 'startup_raw_index.json'
    index = json.loads(idx_path.read_text(encoding='utf8')) if idx_path.exists() else {}
    metrics = dict(task='startup_candidate', scope='research only; no acceptance', cases={})
    for name in CASES:
        p = RUNS / name
        prereg = p / 'preregister.json'
        if not prereg.exists():
            metrics['cases'][name] = dict(status='RUN_ABSENT', note='build_startup.py not executed')
            continue
        pr = json.loads(prereg.read_text(encoding='utf8'))
        cmd = json.loads((p / 'command.json').read_text(encoding='utf8')) if (p / 'command.json').exists() else None
        cir = (p / 'circuit.cir').read_text(encoding='ascii')
        if cmd is None or cmd.get('rc') != 0 or not (p / 'circuit.raw').exists():
            metrics['cases'][name] = dict(status='SOLVER_UNREVIEWED', command=cmd,
                                          note='rc != 0 or raw absent; preserved, never retried')
            continue
        if not ('VEN en 0 0' in cir and 'REN1' not in cir):
            metrics['cases'][name] = dict(status='INHIBIT_NOT_HELD')
            continue
        m = measure(p)
        m['assertions'] = assertions(m, pr['acceptance'])
        m['variable'] = pr['unique_main_variable']
        m['tran'] = pr['tran']
        m['options'] = pr['options']
        m['model_hashes'] = pr['model_hashes']
        m['netlist_sha256'] = pr['netlist_sha256']
        m['solver'] = pr['solver']
        m['raw_sha256'] = lab.sha(p / 'circuit.raw')
        metrics['cases'][name] = m
    metrics['bound_derivation'] = dict(
        formula='V_pk = I_pk = VIN * sqrt(COUT / L)',
        VIN=VIN_SET, COUT_F=COUT, L_F=LPOW, value_V=BOUND_V_PK,
        frozen_before_execution=True,
        caveat='lossless L->C exchange with zero damping and zero load: an UPPER bound, so '
               'exceeding it would falsify the corner, not the design.')
    metrics['thresholds_unchanged'] = True
    metrics['note'] = ('Worker output is evidence only. No HOLD is cleared; physical recovery and '
                       'model uncertainty (round_01 line 7) still block any hardware pass.')
    (OUT / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps({k: v.get('status') for k, v in metrics['cases'].items()}, indent=1))


if __name__ == '__main__':
    main()
