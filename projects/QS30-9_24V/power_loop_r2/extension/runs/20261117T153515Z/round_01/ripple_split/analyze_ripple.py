"""ripple_split / analyze_ripple.py -- DRAFT ONLY (CODE GENERATION, NO EXECUTION).
Reads a COMPLETED candidate circuit.raw via lab.native; arithmetic is numpy only.
No simulator, no network, no model edit, no write outside the caller's directory.
Nothing here is an electrical acceptance.
W1 exact time-weighted mean + TRUE raw Vpp of V(hv) on fixed windows 40-50,
50-55, 55-60 ms (interpolated endpoints, no decimation or smoothing).
W2 10 us non-overlapping raw-Vpp block distribution over 55-60 ms, tail apart.
W3 DIAGNOSTIC ideal capacitor, same windows: Vcap = V(hv) - Rser*(I(DREC) +
I(RSNUB) - V(hv)/R); R is computed by numpy, never typed.
W4 OUT 6 V rising edges (hysteresis, >= 5 us apart): per-cycle I(LPOWER) min/max,
measured OUT duty, frequency, phase, jitter. W5 per cycle within-cycle HV max-min
vs ideal-cap max-min, separating ESR/recovery spikes from slow drift. No FFT, no
compensation proposal.
Vcap is MODEL-IMPLIED DIAGNOSTIC ONLY, never delivered-output acceptance. Names
come from an explicit alias table and are echoed; a miss is a hard failure, never a
substitution. IL is I(LPOWER), the inductor mesh current, not the shunt. Rser and
snubber topology are READ from the netlist; the script refuses if R and C are not
in series between drain/sn and hv, since only then is I(RSNUB) the hv-side current.
"""import json, re, sys
from pathlib import Path
import numpy as np
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
sys.path.insert(0, str(R2))
import lab  # noqa: E402  (lab.native raw reader only)
WINDOWS = [(0.040, 0.050), (0.050, 0.055), (0.055, 0.060)]
BLOCK_W, LEVEL, HYST, MIN_SEP = 1e-05, 6.0, 0.5, 5e-06
DIAG = 'DIAGNOSTIC_ONLY_NOT_ACCEPTANCE'
WARN = ('Vcap is a model-implied DIAGNOSTIC of the ideal COUT behind its Rser, reconstructed '
        'from saved currents. It is NOT delivered-output acceptance and must never be '
        'reported as a pass.')
ALIASES = {'hv': ['v(hv)'], 'out': ['v(out)'], 'il': ['i(lpower)'],
           'drec': ['i(drec)'], 'rsnub': ['i(rsnub)']}
def resolve(cols):
    """Map roles to exact raw names; hard fail (never substitute) on any miss."""
    got = {r: next((n for n in ns if n in cols), None) for r, ns in ALIASES.items()}
    if bad := [r for r, v in got.items() if v is None]:
        raise KeyError('raw lacks %r; present: %r' % (bad, sorted(cols)))
    return got
def netlist(cir):
    """Read COUT Rser and the hv-node feed / snubber topology from the netlist."""
    txt = Path(cir).read_text(encoding='ascii', errors='replace')
    m = re.search(r'(?im)^\s*C\w*\s+hv\s+\S+\s+\S+\s+Rser\s*=\s*([0-9.eE+\-]+)', txt)
    if not m:
        raise ValueError('cannot read COUT Rser from netlist; refusing to guess')
    return dict(rser=float(m.group(1)),
                feeds=[f[1] for f in re.findall(r'(?im)^\s*\w+\s+drain\s+hv\s+(\w+)', txt)],
                snub_series=bool(re.search(r'(?im)^\s*C\w*\s+sn\s+hv\s', txt) and
                                 re.search(r'(?im)^\s*R\w*\s+drain\s+sn\s', txt)))
def seg(t, y, a, b):
    """Raw samples strictly inside [a,b] plus linearly interpolated endpoints."""
    i, j = np.searchsorted(t, [a, b], side='right')
    return (np.concatenate(([a], t[i:j], [b])),
            np.concatenate(([np.interp(a, t, y)], np.asarray(y[i:j]), [np.interp(b, t, y)])))
def wstats(t, y, a, b):
    """Exact time-weighted mean and true raw peak-to-peak on [a,b]."""
    if b <= a or a < t[0] or b > t[-1] + 1e-12:
        raise ValueError('window %r-%r invalid for trace %r..%r' % (a, b, t[0], t[-1]))
    tt, yy = seg(t, y, a, b)
    return dict(t_start=float(a), t_end=float(b), mean=float(np.trapezoid(yy, tt) / (b - a)),
                pp=float(np.ptp(yy)), minimum=float(yy.min()), maximum=float(yy.max()),
                n_raw_points=int(len(yy) - 2))
def blocks(t, y, a, b, w):
    """Non-overlapping w-wide raw-Vpp distribution; incomplete tail reported apart."""
    e, full, tail = np.arange(a, b + 0.5 * w, w), [], None
    for k in range(len(e) - 1):
        s, t2 = float(e[k]), float(e[k + 1])
        if t2 > b + 1e-15:
            tail = dict(t_start=s, t_end=float(b), width_s=float(b - s),
                        pp=float(np.ptp(seg(t, y, s, b)[1])))
            break
        full.append(dict(t_start=s, t_end=t2, pp=float(np.ptp(seg(t, y, s, t2)[1]))))
    if not full:
        raise ValueError('no complete %r s block inside %r-%r' % (w, a, b))
    pp = np.array([f['pp'] for f in full])
    k = int(np.argmax(pp))
    return dict(block_width_s=w, n_full_blocks=len(full), blocks=full,
                minimum=float(pp.min()), median=float(np.median(pp)), maximum=float(pp.max()),
                p90=float(np.percentile(pp, 90)), argmax_block_index=k,
                argmax_t_start=full[k]['t_start'], partial_tail=tail)
def edges_rising(t, v, level, hyst, min_sep):
    """Schmitt rising crossings of `level`: a state below `level-hyst` arms the next
    edge so plateau ringing cannot re-trigger; accepted edges are >= min_sep apart."""
    above, arms, out, armed = v >= level, v <= level - hyst, [], True
    for k in range(1, len(v)):
        if armed and above[k] and not above[k - 1]:
            y0, y1 = float(v[k - 1]), float(v[k])
            f = (level - y0) / (y1 - y0) if y1 != y0 else 0.0
            te = float(t[k - 1]) + f * float(t[k] - t[k - 1])
            if not out or te - out[-1] >= min_sep:
                out.append(te)
            armed = False
        elif arms[k]:
            armed = True
    return np.array(out, dtype=float)
def on_time(st, sv, level):
    """Exact time a piecewise-linear segment spends >= level (interpolated)."""
    total, hi = 0.0, sv >= level
    for z in range(len(sv) - 1):
        dt = float(st[z + 1] - st[z])
        if hi[z] and hi[z + 1]:
            total += dt
        elif hi[z] != hi[z + 1]:
            f = (level - sv[z]) / (sv[z + 1] - sv[z]) if sv[z + 1] != sv[z] else 0.0
            total += dt * ((1.0 - f) if hi[z] else f)
    return total
def cycles(t, cols, nm, ed, cap, level, w):
    """Per-cycle IL min/max, HV swing vs ideal-cap swing, duty, frequency, phase.
    Phase = each OUT edge's position within the mean period, mod 360 deg; jitter is
    its standard deviation over clean cycles (no FFT anywhere)."""
    per = np.diff(ed)
    fm = 1.0 / float(np.mean(per)) if len(per) else float('nan')
    rows = []
    for k in range(len(ed) - 1):
        a, b = float(ed[k]), float(ed[k + 1])
        tt, _ = seg(t, ed, a, b)
        il = np.interp(tt, t, cols[nm['il']])
        hv = np.interp(tt, t, cols[nm['hv']])
        cv = np.interp(tt, t, cap)
        on = float(on_time(*seg(t, cols[nm['out']], a, b), level))
        sh, sc = float(np.ptp(hv)), float(np.ptp(cv))
        rows.append(dict(
            cycle_index=k, t_rise_start=a, t_rise_end=b,
            frequency_hz=1.0 / (b - a) if b > a else float('nan'),
            phase_deg_mod_360=float(((a * fm) % 1.0) * 360.0) if np.isfinite(fm) else None,
            il_min=float(il.min()), il_max=float(il.max()), il_ripple=float(np.ptp(il)),
            hv_max_minus_min=sh, idealcap_max_minus_min=sc, hv_minus_cap_swing=sh - sc,
            idealcap_share_of_hv_swing=(sc / sh) if sh else None, out_on_s=on,
            out_duty=(on / (b - a)) if b > a else float('nan'),
            crosses_window_boundary=bool(any(abs(a - s) <= w or abs(b - s) <= w or
                                             (a <= s and b >= e2) for s, e2 in WINDOWS))))
    return rows
def main(argv):
    if len(argv) < 2 or not Path(argv[1]).is_file():
        raise SystemExit('usage: analyze_ripple.py <circuit.raw> [circuit.cir] [out.json]')
    raw = Path(argv[1]).resolve()
    cir = Path(argv[2]) if len(argv) > 2 else raw.with_name('circuit.cir')
    dst = Path(argv[3]) if len(argv) > 3 else None
    if dst is not None and dst.exists():
        raise FileExistsError('never overwrite an existing artifact: %s' % dst)
    cols = lab.native(raw)
    nm, net = resolve(cols), netlist(cir)
    t = np.asarray(cols['time'], dtype=float)
    if not net['snub_series']:
        raise ValueError('snubber R and C not in series drain->sn->hv; refusing to sum '
                         'I(RSNUB) with I(CSNUB) as one hv-side current')
    hv = np.asarray(cols[nm['hv']], dtype=float)
    r_load = 1.0 / (1.0 / 5200 + 2.0 / (90900 + 90900) + 1.0 / (200000 + 1900.6))
    feed = np.asarray(cols[nm['drec']], dtype=float) + np.asarray(cols[nm['rsnub']], dtype=float)
    cap = hv - net['rser'] * (feed - hv / r_load)  # diagnostic only, never acceptance
    a5, b6 = WINDOWS[-1]
    ed = edges_rising(t, np.asarray(cols[nm['out']], dtype=float), LEVEL, HYST, MIN_SEP)
    rows = cycles(t, cols, nm, ed, cap, LEVEL, BLOCK_W)
    clean = [r for r in rows if not r['crosses_window_boundary']]
    mm = {k: ([float(x) for x in (v.min(), np.median(v), v.max())] if len(v) else None)
          for k, v in (('frequency_hz', np.array([r['frequency_hz'] for r in clean])),
                       ('out_duty', np.array([r['out_duty'] for r in clean])),
                       ('phase_deg', np.array([r['phase_deg_mod_360'] for r in clean])))}
    res = dict(
        script='analyze_ripple.py', status='DRAFT_NOT_EXECUTED_IN_THIS_SESSION',
        raw=raw.name, raw_sha256=lab.sha(raw), netlist=Path(cir).name, resolved_names=nm,
        r_load_ohm=r_load, cout_rser_ohm=net['rser'], hv_feed_subcircuits=net['feeds'],
        windows_s=[list(w) for w in WINDOWS], diagnostic_warning=WARN,
        hv_windows=[wstats(t, hv, a, b) for a, b in WINDOWS], cycles=rows,
        idealcap_diagnostic_windows=[dict(wstats(t, cap, a, b), status=DIAG) for a, b in WINDOWS],
        hv_10us_blocks_55_60ms=blocks(t, hv, a5, b6, BLOCK_W),
        idealcap_10us_blocks_55_60ms=dict(blocks(t, cap, a5, b6, BLOCK_W), status=DIAG),
        edge_detection=dict(level_v=LEVEL, hysteresis_v=HYST, min_separation_s=MIN_SEP,
                            n_edges=int(len(ed)), edges_s=ed.tolist()),
        cycle_summary=dict(n_cycles=len(rows), n_clean_cycles=len(clean), **mm,
                           order='[min, median, max] over clean cycles' if clean else None,
                           phase_jitter_deg_std=float(np.std(
                               [r['phase_deg_mod_360'] for r in clean])) if clean else None),
        assertions=dict(
            signals_resolved=all(nm.values()), monotonic_time=bool(np.all(np.diff(t) > 0)),
            complete_60ms_trace=bool(t[-1] >= 0.060), snubber_r_c_in_series=net['snub_series'],
            hv_feed_subcircuits=net['feeds'], idealcap_is_diagnostic_not_acceptance=True,
            edges_separated_ge_5us=bool(len(ed) < 2 or np.all(np.diff(ed) >= MIN_SEP)),
            compensation_proposal_made=False, fft_performed=False))
    text = json.dumps(res, indent=2, allow_nan=False)
    if dst is None:
        print(text)
    else:
        dst.write_text(text + '\n', encoding='utf8')
    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv))
