"""device_energy_audit -- QS30-9 extension, Round 1 (code only).

Reads ONLY committed principal evidence via the shared lab.native memmap reader
(evidence/principal/minimum_native_probes/circuit.raw) plus numpy. No simulator,
shell, network or model edit; models are hashed, never written.

st.lib STP9NK50Z topology: LG 2 4 7.5n / LS 12 3 7.5n / LD 6 1 4.5n; MOS
13(drain) 5(gate) 9(source). So Vq12-Vsrc is the voltage across the source
package inductor LS and Vq6-Vdrain across the drain package inductor LD.
Per window the contract's identities are evaluated exactly as written:
  integral (Vq12-Vsrc)*I(VQS) dt     ~= .5*7.5n*(Iend^2-Istart^2)
  integral (Vq6 -Vdrain)*(-I(VQD)) dt ~= .5*4.5n*(Iend^2-Istart^2)
The opposite orientation of each is also evaluated: a closed inductor obeys
v*i = d/dt(.5 L i^2) either way, and probe label vs pin direction cannot be
settled from probe text alone. A disagreement is reported as possible (a) non-L
branch, (b) coarse trapezoid sum at a narrow event, or (c) orientation/name
mismatch -- never inferred as a physical or model failure, never hand-resolved.
No automatic physics or model PASS is derived here.
"""
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
EVID = R2 / 'evidence' / 'principal' / 'minimum_native_probes'
RAW = EVID / 'circuit.raw'
CIR = EVID / 'circuit.cir'
LIB = EVID / 'st.lib'
IA = EVID / 'internal_analysis.json'
REQUIRED = ['v(q:12)', 'v(q:6)', 'v(src)', 'v(drain)', 'i(vqs)', 'i(vqd)',
            'v(q:5)', 'v(q:9)', 'v(q:13)']
LS_H = 7.5e-9
LD_H = 4.5e-9
WINDOWS = [(1.02e-6, 1.10e-6), (0.0, 10e-6)]
ABS_FLOOR_J = 1e-12     # below this the energy is numerically zero
REL_TOL = 0.05          # PRELIMINARY disagreement flag only, not acceptance

sys.path.insert(0, str(R2))
import lab  # noqa: E402  (shared reader; nothing is executed by it)


def window_points(t, y, a, b):
    """Subset [a,b] with endpoint interpolation; raises on empty window."""
    if b <= a:
        raise ValueError('empty/reversed window')
    if a < t[0] - 1e-18 or b > t[-1] * (1 + 1e-12):
        raise ValueError('window outside trace extent')
    i, j = int(np.searchsorted(t, a)), int(np.searchsorted(t, b))
    tt = np.r_[a, t[i:j], b]
    yy = np.r_[np.interp(a, t, y), y[i:j], np.interp(b, t, y)]
    keep = np.r_[True, np.diff(tt) > 0]
    return tt[keep], yy[keep]


def branch(c, a, b, vname, iname, L, sign):
    """Integrate v*i over [a,b] and compare to .5*L*(Iend^2-Istart^2)."""
    t, v = window_points(c['time'], c[vname], a, b)
    _, i = window_points(c['time'], c[iname], a, b)
    p = sign * v * i
    energy = float(np.trapezoid(p, t))
    istart, iend = float(i[0]), float(i[-1])
    dstore = 0.5 * L * (iend ** 2 - istart ** 2)
    resid = energy - dstore
    scale = max(abs(energy), abs(dstore), ABS_FLOOR_J)
    return {
        'window_s': [a, b],
        'v_probe': vname, 'i_probe': iname, 'current_sign': sign,
        'inductance_H': L, 'points': int(t.size),
        'I_start_A': istart, 'I_end_A': iend,
        'energy_integral_J': energy,
        'delta_stored_J': dstore,
        'residual_J': resid,
        'relative_error': abs(resid) / scale,
        'v_extreme_V': [float(v.min()), float(v.max())],
        'i_extreme_A': [float(i.min()), float(i.max())],
    }


def main():
    for p in (RAW, CIR, LIB, IA):
        if not p.exists():
            raise SystemExit('missing required source: %s' % p)
    c = lab.native(RAW)
    missing = [n for n in REQUIRED if n not in c]
    if missing:
        raise SystemExit('missing probes in raw: %s' % missing)
    ia = json.loads(IA.read_text(encoding='utf-8'))
    hashes = {'circuit.cir': lab.sha(CIR), 'st.lib': lab.sha(LIB),
              'circuit.raw': lab.sha(RAW),
              'internal_analysis.json': lab.sha(IA),
              'analyze_energy.py': lab.sha(Path(__file__))}

    c = dict(c)
    c['v(ls)'] = c['v(q:12)'] - c['v(src)']
    c['v(ld)'] = c['v(q:6)'] - c['v(drain)']
    t = c['time']
    checks = {}
    rows = []
    for a, b in WINDOWS:
        # Evaluated exactly as the contract writes them.
        ls = branch(c, a, b, 'v(ls)', 'i(vqs)', LS_H, +1.0)
        ls_alt = branch(c, a, b, 'v(ls)', 'i(vqs)', LS_H, -1.0)
        ld = branch(c, a, b, 'v(ld)', 'i(vqd)', LD_H, -1.0)
        ld_alt = branch(c, a, b, 'v(ld)', 'i(vqd)', LD_H, +1.0)
        # Pin-current extrema per window are reported, not assumed equal.
        _, iqs = window_points(t, c['i(vqs)'], a, b)
        _, iqd = window_points(t, c['i(vqd)'], a, b)
        rows.append({'window': [a, b], 'LS_source_package': ls, 'LD_drain_package': ld,
                     'LS_opposite_sign_reference': ls_alt,
                     'LD_opposite_sign_reference': ld_alt,
                     'pin_current_pair_extremes_A': {
                         'I(VQS)': [float(iqs.min()), float(iqs.max())],
                         'I(VQD)': [float(iqd.min()), float(iqd.max())]}})
    for key in ('LS_source_package', 'LD_drain_package'):
        worst = max(r[key]['relative_error'] for r in rows)
        checks[key + '_identity_within_%g%%' % (100 * REL_TOL)] = bool(worst <= REL_TOL)
        checks[key + '_worst_relative_error'] = worst

    win_a, win_b = WINDOWS[0]
    vgs = c['v(q:5)'] - c['v(q:9)']
    vds = c['v(q:13)'] - c['v(q:9)']
    _, vgs_w = window_points(t, vgs, win_a, win_b)
    _, vds_w = window_points(t, vds, win_a, win_b)
    # Package-voltage extremes over the whole trace (grid extrema, no resampling).
    extrema = {}
    for name in ('v(src)', 'v(drain)'):
        extrema[name] = {'minimum': float(c[name].min()), 'maximum': float(c[name].max()),
                         'abs_max': float(np.abs(c[name]).max())}
    # Cross-check intrinsic nodes against the principal's committed analysis.
    prov = ia.get('ranges', {})
    cross = {k: {'scripts_min': float(c[k].min()), 'scripts_max': float(c[k].max()),
                 'internal_analysis_min': prov.get(k, {}).get('minimum'),
                 'internal_analysis_max': prov.get(k, {}).get('maximum')}
             for k in ('v(q:5)', 'v(q:9)', 'v(q:13)') if k in prov}

    metrics = {
        'task': 'device_energy_audit',
        'raw_sha256': hashes['circuit.raw'],
        'raw_sha256_matches_internal_analysis': bool(
            ia.get('raw_sha256') == hashes['circuit.raw']),
        'solver': 'LTspice 24.0.12 (Gear, reltol=1e-3, abstol=1n, vntol=1u)',
        'solver_tolerance_v': 1e-6,
        'solver_tolerance_A': 1e-9,
        'integration_rule': 'numpy.trapezoid on saved points with interpolated endpoints',
        'points_total': int(t.size),
        'dt_min_s': float(np.diff(t).min()), 'dt_max_s': float(np.diff(t).max()),
        'windows': rows,
        'checks': checks,
        'intrinsic_voltage_1p02_1p10us': {
            'VGS_intrinsic_V': {'min': float(vgs_w.min()), 'max': float(vgs_w.max())},
            'VDS_intrinsic_V': {'min': float(vds_w.min()), 'max': float(vds_w.max())}},
        'intrinsic_voltage_full_trace': {
            'VGS_intrinsic_V': {'min': float(vgs.min()), 'max': float(vgs.max())},
            'VDS_intrinsic_V': {'min': float(vds.min()), 'max': float(vds.max())}},
        'package_voltage_extrema_V': extrema,
        'cross_check_internal_analysis': cross,
        'model_hashes': hashes,
        'identity_failure_caveat': (
            'The gross trace contains an extremely narrow reverse-drive event near '
            '1.052us; a trapezoid sum over sparse saved points can under- or '
            'over-estimate work there. Failure of this discrete identity can '
            'therefore indicate coarse integration of a narrow event rather than '
            'a physical finding, and success does not certify the model. No '
            'physics, thermal or model PASS is claimed.'),
    }
    (OUT / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
    lines = ['%s %s integral=%.6e J delta_store=%.6e J rel=%.3e pts=%d'
             % (k[:2], r['window'], r[k]['energy_integral_J'], r[k]['delta_stored_J'],
                r[k]['relative_error'], r[k]['points'])
             for r in rows for k in ('LS_source_package', 'LD_drain_package')]
    (OUT / 'waves.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    for k, v in checks.items():
        print(k, v)


if __name__ == '__main__':
    main()