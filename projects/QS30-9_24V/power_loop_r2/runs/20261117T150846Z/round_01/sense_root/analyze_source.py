"""sense_root phase A: forensics of the ORIGINAL R1 raw near the 10.040718ms SENSE event.

Read-only on R1 evidence. Writes only inside OUTPUT_DIR.
No simulation is launched here.
"""
import csv, hashlib, json, re, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
sys.path.insert(0, str(R2))
import lab  # noqa: E402

BASE = lab.BASE
SRC_RAW = BASE / 'circuit.raw'
SRC_CIR = BASE / 'circuit.cir'
T0 = 0.010040718423769968          # from R1 cycle_review.json worst_sense_event
HALF = 2e-6
A, B = T0 - HALF, T0 + HALF


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def win(t, y, a, b):
    i, j = np.searchsorted(t, [a, b])
    tt = np.r_[a, t[i:j], b]
    yy = np.r_[np.interp(a, t, y), y[i:j], np.interp(b, t, y)]
    return tt, yy


def integ(t, y, a, b):
    tt, yy = win(t, y, a, b)
    if a < t[0] or b > t[-1]:
        raise ValueError('outside trace')
    return float(np.trapezoid(yy, tt))


def extrema(t, y, a, b):
    tt, yy = win(t, y, a, b)
    i = int(np.argmax(yy)); k = int(np.argmin(yy))
    return dict(max=float(yy[i]), t_max=float(tt[i]), min=float(yy[k]), t_min=float(tt[k]),
                mean=float(np.trapezoid(yy, tt) / (b - a)), pp=float(np.ptp(yy)))


def main():
    manifest = {
        'source_raw': str(SRC_RAW),
        'source_raw_sha256': sha(SRC_RAW),
        'source_raw_bytes': SRC_RAW.stat().st_size,
        'source_cir': str(SRC_CIR),
        'source_cir_sha256': sha(SRC_CIR),
        'models': {p.name: sha(p) for p in sorted(BASE.iterdir()) if p.suffix.lower() in ('.sub', '.lib')},
        'solver': 'LTspice 24.0.12 for Windows, solver = Normal, method = Gear (from R1 circuit.log)',
    }
    c = lab.native(SRC_RAW)
    t = np.asarray(c['time'], dtype=np.float64)
    cols = {k: np.asarray(v, dtype=np.float64) for k, v in c.items() if k != 'time'}
    manifest['columns'] = list(cols)
    manifest['n_points'] = int(t.size)
    manifest['t_first'] = float(t[0]); manifest['t_last'] = float(t[-1])
    lab.dump(HERE / 'source_raw_inventory.json', manifest)

    # ---- extraction of the event window -------------------------------
    i, j = np.searchsorted(t, [A, B])
    sl = slice(int(i), int(j))
    with (HERE / 'event_window.csv').open('w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        names = ['time'] + list(cols)
        w.writerow(names)
        for k in range(i, j):
            w.writerow([f'{t[k]:.15g}'] + [f'{cols[n][k]:.15g}' for n in cols])

    dt = np.diff(t)
    ev = {
        'window_s': [A, B],
        'event_anchor_s': T0,
        'samples_in_window': int(j - i),
        'dt_in_window_local': {
            'min': float(dt[max(i - 1, 0):j].min()), 'median': float(np.median(dt[max(i - 1, 0):j])),
            'max': float(dt[max(i - 1, 0):j].max())},
        'global_dt': {'min': float(dt.min()), 'median': float(np.median(dt)), 'max': float(dt.max())},
        'global_peak_sense': float(cols['v(sense)'].max()),
        'global_peak_sense_t': float(t[int(np.argmax(cols['v(sense)']))]),
        'signals': {n: extrema(t, cols[n], A, B) for n in cols},
    }
    # local (>= global/2) and global extrema of v(sense) for the local/global distinction
    s = cols['v(sense)']
    gmax = float(s.max())
    li = i + int(np.argmax(s[i:j]))
    ev['local_peak_sense'] = {'value': float(s[li]), 't': float(t[li]),
                              'is_global_max': bool(abs(s[li] - gmax) < 1e-15)}
    ev['samples_above_0p3V_global'] = int((s > 0.3).sum())
    ev['samples_above_0p3V_window'] = int((s[i:j] > 0.3).sum())
    ev['window_above_0p3V_inclusive'] = bool(s[i - 1:i + (j - i) + 1].max() > 0.3)

    # ---- KCL at nodes observed by the original .save ------------------
    # V(src) node: RSRC feeds it, RF + RGS + XNEG(XQ source pin) leave it.
    # I(RF) is NOT saved in the R1 raw; it is inferred from the CF sense node
    # (I(RF) = I(CF) + I(into sense node through LT3757A SENSE pin, unsaved)).
    is_rsrc = cols['v(src)'] / 0.062
    il = cols['i(lpower)']
    ev['node_src_kcl_A'] = {
        'I_RSRC_note': 'V(src)/0.062 is a SIGN CONVENTION assumption treated as unsigned shunt magnitude',
        'event_IR_RSRC_magnitude': float(np.interp(T0, t, is_rsrc)),
        'event_IL': float(np.interp(T0, t, il)),
        'event_IL_minus_IRSRC': float(np.interp(T0, t, il) - np.interp(T0, t, is_rsrc)),
        'restart_note': 'if |I_RSRC| > |IL| at T0 the branch must be carrying a negative (source-to-shunt) current;'
                        ' unobservable without XQ source-pin current',
        'window_IL_mean': extrema(t, il, A, B)['mean'],
        'window_IR_RSRC_mean': extrema(t, is_rsrc, A, B)['mean'],
    }
    # COUT node (hv): I(DREC) + I(LPOWER-side? no) into hv: DREC flows drain->hv; snubber CSNUB sn->hv,
    # RLOAD hv->0, RB* hv->0, RFB1 hv->fbmid, COUT via Rser. Only I(DREC) is saved -> partial KCL.
    ev['node_hv_kcl'] = {
        'saved_terms': ['I(DREC)'],
        'unsaved_terms': ['RSNUB', 'RLOAD', 'RB1A', 'RB2A', 'RFB1', 'COUT branch'],
        'charge_drec_window_C': integ(t, cols['i(drec)'], A, B),
        'window_note': 'charge through DREC over +-2us; sign convention: positive when current flows drain->hv',
    }
    # gate node: V(gate) is node 'gate'; I through RG/RGS/RNEG unsaved.
    ev['node_gate_kcl'] = {
        'unsaved_terms': ['I(RG)', 'I(RGS)', 'I(RNEG)', 'I(controller gate pin)'],
        'VGS_relation_unsaved': 'source pin current not saved, VGS = V(gate)-V(src) available only',
    }
    ev['node_sense_kcl'] = {
        'I_RF': 'unsaved', 'I_RGS': 'unsaved', 'measurement': 'V(sense) only, 0.524V > 0.3V abs max rating',
    }
    # energy of the event (resistive losses in observed shunt only)
    lab.dump(HERE / 'event_json.json', ev)

    # ---- solver step accounting in the R1 log (no new simulation) -----
    log = (BASE / 'circuit.log').read_text(encoding='latin-1')
    hd = [float(m) for m in re.findall(r'Heightened Def Con from ([\d.eE+-]+)', log)]
    ev2 = {
        'heightened_def_con_count': len(hd),
        'heightened_in_window': [x for x in hd if A <= x <= B],
        'heightened_near_event_100us': sorted([x for x in hd if T0 - 1e-4 <= x <= T0 + 1e-4]),
        'any_newton_failure': bool(re.search(r'Direct Newton iteration failed|Timestep too small|singular', log)),
        'total_elapsed_s': float(re.search(r'Total elapsed time: ([\d.]+)', log)[1]),
        'method_lines': re.findall(r'(?m)^(?:method|abstol|volttol|solver|temp) = .*$', log),
    }
    lab.dump(HERE / 'source_log_diagnostics.json', ev2)
    print(json.dumps({'n': manifest['n_points'], 'samples_in_window': ev['samples_in_window'],
                      'global_peak': ev['global_peak_sense'], 'local_peak': ev['local_peak_sense'],
                      'hd_count': len(hd), 'hd_window': ev2['heightened_in_window'],
                      'IRSRC_T0': ev['node_src_kcl_A']['event_IR_RSRC_magnitude'],
                      'IL_T0': ev['node_src_kcl_A']['event_IL']}, indent=1))


if __name__ == '__main__':
    main()
