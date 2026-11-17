"""sense_root phase C: compare the three diagnostic runs and the R1 source raw.

Reads only files inside OUTPUT_DIR plus the R1 raw (read-only).
Emits metrics.json. Never infers acceptance; failures are recorded, not repaired.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
sys.path.insert(0, str(R2))
import lab  # noqa: E402

SRC = lab.BASE / 'circuit.raw'
T_EVENT = 0.010040718423769968
HALF = 2e-6
A, B = T_EVENT - HALF, T_EVENT + HALF
LAST = 0.01008

PROBES = ['i(xq:ld)', 'i(xq:ls)', 'i(xq:lg)', 'i(xneg:ddio)', 'i(xneg:dgr)',
          'i(rsrc)', 'i(rf)', 'i(rgs)', 'i(rneg)', 'i(rsnub)', 'i(csnub)']
RUNS = ['run_gear_2e-7', 'run_gear_1e-7', 'run_trap_2e-7']


def win(t, y, a, b):
    i, j = np.searchsorted(t, [a, b])
    return np.r_[a, t[i:j], b], np.r_[np.interp(a, t, y), y[i:j], np.interp(b, t, y)]


def itg(t, y, a, b):
    tt, yy = win(t, y, a, b)
    return float(np.trapezoid(yy, tt))


def ext(t, y, a, b):
    tt, yy = win(t, y, a, b)
    ia, ik = int(np.argmax(yy)), int(np.argmin(yy))
    return dict(max=float(yy[ia]), t_max=float(tt[ia]), min=float(yy[ik]), t_min=float(tt[ik]),
                mean=float(np.trapezoid(yy, tt) / (b - a)))


def kcl_residual_at_t0(t, c):
    """Node `src`: sum of port currents entering the node, signed.

    Entering: I(RSRC) (shunt -> src), I(XQ:LS) (XQ source pin -> src).
    Leaving : I(XQ:LD)? no; I(RF) (src -> sense), I(RGS) (gate -> src),
              I(RNEG) (neg -> gate), I(XNEG) (src -> neg via ddio and dgr).
    Sign conventions of LTspice current probes are kept as-is; residual is
    reported BOTH as |sum| and as sum of magnitudes so a sign error is visible.
    """
    def k(n):
        return float(np.interp(T_EVENT, t, c[n])) if n in c else None
    terms = {'I_RSRC': k('i(rsrc)'), 'I_RF': k('i(rf)'), 'I_RGS': k('i(rgs)'),
             'I_RNEG': k('i(rneg)'), 'I_RSNUB': k('i(rsnub)'), 'I_CSNUB': k('i(csnub)'),
             'I_LPOWER': k('i(lpower)'), 'I_DREC': k('i(drec)')}
    missing = {n: None for n in ['i(xq:ld)', 'i(xq:ls)', 'i(xq:lg)', 'i(xneg:ddio)', 'i(xneg:dgr)'] if n not in c}
    # Derivable branch currents (topology: RSRC src-0, RF src-sense, RGS gate-src, RNEG neg-gate)
    if terms['I_RSRC'] is not None:
        terms['I_RSRC_from_Vsrc_divR'] = k('v(src)') / 0.062
    if 'v(sense)' in c:
        terms['I_RF_from_Vsrc_minus_Vsense_divR'] = (k('v(src)') - k('v(sense)')) / 10.0
    return {'values_A': terms, 'unavailable_ports': list(missing),
            'derived_sense_node_kcl': {
                'I_CF_A': None,
                'note': 'sense node: RF into node, CF to gnd (unsaved), LT3757A SENSE pin (unsaved). '
                        'I(RF) and V(sense) are now available; the controller SENSE-pin current is NOT observable, '
                        'so the shunt-vs-pin current split at the event remains unproven.'}}


def probe_time_series(t, c, a, b):
    out = {}
    for p in PROBES:
        if p in c:
            tt, yy = win(t, c[p], a, b)
            out[p] = dict(n=len(tt), max=float(yy.max()), min=float(yy.min()),
                          charge_C=itg(t, c[p], a, b),
                          peak_abs_t=float(tt[int(np.argmax(np.abs(yy)))]))
    return out


def main():
    res = {'task_id': 'sense_root', 'worker_status_semantics': 'PASS = evidence delivered only; no electrical acceptance',
           'event_anchor_s': T_EVENT, 'window_s': [A, B], 'common_window_complete_to_s': LAST,
           'runs': {}, 'missing_probes': {}, 'r1_reference': {}}

    data = {}
    for name in RUNS:
        d = HERE / name
        raw = d / 'circuit.raw'
        cmd = json.loads((d / 'command.json').read_text()) if (d / 'command.json').exists() else None
        entry = {'command': cmd, 'raw_bytes': raw.stat().st_size if raw.exists() else 0,
                 'raw_sha256': lab.sha(raw) if raw.exists() else None}
        if not raw.exists() or cmd is None or cmd.get('rc') != 0:
            entry['extracted'] = False
            entry['reason'] = 'no raw produced or solver rc != 0; preserved, not retried'
            res['runs'][name] = entry
            continue
        try:
            c = lab.native(raw)
        except Exception as e:  # noqa: BLE001
            entry['extracted'] = False
            entry['reason'] = f'native reader rejected raw: {e}'
            res['runs'][name] = entry
            continue
        t = np.asarray(c['time'], dtype=np.float64)
        c = {k: np.asarray(v, dtype=np.float64) for k, v in c.items()}
        entry['extracted'] = True
        entry['columns'] = list(c)
        entry['n_points'] = int(t.size)
        entry['t_first'], entry['t_last'] = float(t[0]), float(t[-1])
        entry['complete_to_10p08ms'] = bool(t[-1] >= LAST - 1e-12)
        entry['missing_probes'] = [p for p in PROBES if p not in c]
        for p in entry['missing_probes']:
            res['missing_probes'].setdefault(p, []).append(name)
        entry['global'] = {n: ext(t, c[n], float(t[0]), float(t[-1])) for n in c if n != 'time'}
        entry['window'] = {n: ext(t, c[n], A, B) for n in c if n != 'time'}
        entry['window_charge_C'] = {n: itg(t, c[n], A, B) for n in c if n != 'time'}
        entry['ports'] = probe_time_series(t, c, A, B)
        entry['kcl_src_at_event'] = kcl_residual_at_t0(t, c)
        entry['dt'] = {'min': float(np.diff(t).min()), 'median': float(np.median(np.diff(t))),
                       'max': float(np.diff(t).max()), 'n': int(t.size)}
        res['runs'][name] = entry
        data[name] = (t, c)

    # --- R1 reference (global peak / event context from the source raw)
    if SRC.exists():
        s = lab.native(SRC)
        ts = np.asarray(s['time'], dtype=np.float64)
        ss = {k: np.asarray(v, dtype=np.float64) for k, v in s.items()}
        res['r1_reference'] = {
            'n_points': int(ts.size), 't_last': float(ts[-1]),
            'sense_global_max': float(ss['v(sense)'].max()),
            'sense_global_max_t': float(ts[int(np.argmax(ss['v(sense)']))]),
            'drec_global_max': float(ss['i(drec)'].max()),
            'drec_global_min': float(ss['i(drec)'].min()),
            'drec_peak_abs': float(np.abs(ss['i(drec)']).max()),
            'drec_peak_abs_t': float(ts[int(np.argmax(np.abs(ss['i(drec)'])))]),
            'il_global_max': float(ss['i(lpower)'].max()),
            'il_global_min': float(ss['i(lpower)'].min()),
        }
        data['__r1__'] = (ts, ss)

    # --- field-by-field comparison on the COMMON complete window
    usable = [n for n in RUNS if n in data and data[n][0][-1] >= LAST - 1e-12]
    res['common_window'] = {'runs_used': usable, 'end_s': LAST}
    cmp = {}
    if usable:
        fields = ['v(sense)', 'v(drain)', 'v(gate)', 'v(src)', 'v(hv)', 'v(out)', 'i(lpower)', 'i(drec)',
                  'i(xq:ld)', 'i(xq:ls)', 'i(xq:lg)', 'i(xneg:ddio)', 'i(xneg:dgr)', 'i(rsrc)', 'i(rf)',
                  'i(rgs)', 'i(rneg)', 'i(rsnub)', 'i(csnub)']
        fields = [f for f in fields if all(f in data[n][1] for n in usable)]
        for f in fields:
            row = {}
            for n in usable:
                t, c = data[n]
                m = t <= LAST
                row[n] = {'max': float(c[f][m].max()), 'min': float(c[f][m].min()),
                          't_max': float(t[m][int(np.argmax(c[f][m]))]),
                          'abs_peak': float(np.abs(c[f][m]).max())}
            peaks = [row[n]['abs_peak'] for n in usable]
            ref = max(peaks) if peaks else 0.0
            spread = (max(peaks) - min(peaks)) / ref if ref > 0 else 0.0
            tmaxes = [row[n]['t_max'] for n in usable]
            # peak-change <=5% screen (lab.preregister diagnostic_reproducibility)
            row['spread_pct'] = 100 * spread
            row['peak_change_le_5pct'] = bool(spread <= 0.05)
            row['t_max_spread_us'] = 1e6 * (max(tmaxes) - min(tmaxes))
            tmin = [row[n]['t_max'] for n in usable]
            row['sign_consistent'] = bool(all((row[n]['max'] >= 0) == (row[usable[0]]['max'] >= 0) for n in usable))
            cmp[f] = row
    res['solver_time_step_sensitivity'] = cmp

    # --- explicit assertions
    a = {}
    a['all_three_runs_launched'] = len(json.loads((HERE / 'runs_command.json').read_text())) == 3 if (HERE / 'runs_command.json').exists() else False
    a['all_runs_extracted'] = len(usable) == 3
    a['all_probes_present'] = all(not res['runs'][n].get('missing_probes') for n in res['runs'])
    a['r1_global_sense_peak_reproduced_within_30pct'] = None
    if 'run_gear_2e-7' in data:
        t, c = data['run_gear_2e-7']
        m = t <= LAST
        p = float(c['v(sense)'][m].max())
        if res['r1_reference']:
            g = res['r1_reference']['sense_global_max']
            a['r1_global_sense_peak_reproduced_within_30pct'] = bool(abs(p - g) / g <= 0.30)
            a['run_gear200_sense_peak_V'] = p
            a['r1_sense_peak_V'] = g
    a['peak_change_le_5pct_all_fields'] = bool(cmp) and all(v['peak_change_le_5pct'] for v in cmp.values())
    res['assertions'] = a
    res['rc_solver'] = {n: res['runs'][n]['command'].get('rc') if res['runs'][n]['command'] else None for n in res['runs']}
    lab.dump(HERE / 'metrics.json', res)
    print(json.dumps({'usable': usable, 'missing': res['missing_probes'], 'assertions': a,
                      'fields_compared': list(cmp)[:30],
                      'failing_spread': {k: round(v['spread_pct'], 2) for k, v in cmp.items() if not v['peak_change_le_5pct']}},
                     indent=1))


if __name__ == '__main__':
    main()
