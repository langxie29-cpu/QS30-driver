"""settling_analysis / loop_forensics -- R2 Round 1.

NO SIMULATIONS. This script only reads the ORIGINAL R1 60ms raw trace and the
original R1 netlist/models, plus the R1 late-window evidence that must be
reconciled (not overwritten). It never writes outside this output directory and
never modifies any circuit component or vendor model.

Facts fixed by the contract:
  * 60 ms is NOT qualified as settled. No settling claim is made anywhere.
  * Worker PASS == evidence delivered only, never electrical acceptance.
"""
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
BASE = (Path('D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1')
        / 'evidence/candidate_diagnostic/nominal_24V_gear_resource600')
OUT = Path(__file__).resolve().parent
RAW = BASE / 'circuit.raw'
CIR = BASE / 'circuit.cir'

sys.path.insert(0, str(R2))
import lab  # noqa: E402  (shared helper: lab.native memmap reader, lab.sha)

WINDOWS = [(0.040, 0.045), (0.045, 0.050), (0.050, 0.055), (0.055, 0.060)]
TRAPZ = getattr(np, 'trapezoid', None) or np.trapz  # numpy 2.x rename
SETTLE_BAND_V = 0.01          # 10 mV band used ONLY to test "is it settled yet"


def sha(p):
    return lab.sha(p)


def weighted_stats(t, y, a, b):
    """Time-weighted (trapezoid) mean and TRUE raw peak-to-peak on [a, b].

    Endpoints a and b are linearly interpolated so the window boundary is exact;
    no sample is dropped or extrapolated. Vpp is taken from the raw samples
    actually inside the window (plus the two interpolated endpoints). No
    decimation, no smoothing, no thresholding -- this is the true raw Vpp and it
    therefore includes any solver/step artefacts that the trace contains.
    """
    if a < t[0] - 1e-15 or b > t[-1] + 1e-12:
        raise ValueError('window outside complete trace')
    i, j = np.searchsorted(t, [a, b])
    tt = np.concatenate(([a], t[i:j], [b]))
    yy = np.concatenate(([np.interp(a, t, y)], y[i:j], [np.interp(b, t, y)]))
    mean = float(TRAPZ(yy, tt) / (b - a))
    return dict(t_start=float(a), t_end=float(b),
                mean_V=mean, raw_Vpp=float(np.ptp(yy)),
                min_V=float(yy.min()), max_V=float(yy.max()),
                arithmetic_mean_V=float(yy.mean()), n_points=int(len(yy)),
                mean_minus_arith_mV=float((mean - yy.mean()) * 1e3))


def resample_uniform(t, y, fs):
    """Uniform resample at fs onto the sample grid of the window (no filter).

    The native raw is NOT uniform (LTSpice adaptive 200 ns max step); an FFT
    demands uniform spacing, so this is an explicit interpolation step and its
    spectral cost is a documented caveat, not an error.
    """
    n = int(round((t[-1] - t[0]) * fs))
    tu = t[0] + np.arange(n) / fs
    return tu, np.interp(tu, t, y)


def fft_features(tu, yu, label):
    """Hann-windowed, mean-detrended amplitude spectrum of a uniformly
    resampled segment. Nyquist = fs/2; bin width = fs/N. Returns top peaks
    after excluding the 0-2 Hz trend region, plus band powers."""
    x = yu - yu.mean()
    n = len(x)
    w = np.hanning(n)
    # coherent-gain correction for Hann (sum(w)/n = 0.5) -> amplitude correct
    amp = np.abs(np.fft.rfft(x * w)) * 2.0 / w.sum()
    # dt comes from the actual uniform grid, not from a recomputed span
    dt = float(tu[1] - tu[0])
    f = np.fft.rfftfreq(n, dt)
    df = f[1] - f[0]
    nyq = f[-1]
    keep = f >= 2.0
    idx = np.argsort(amp[keep])[::-1]
    peaks = [dict(f_Hz=float(f[keep][k]), amp_Vpp=float(2 * amp[keep][k])) for k in idx[:6]]
    # amplitude at the switching frequency band
    sw = (f > 60e3) & (f < 140e3)
    lf = (f > 2.0) & (f < 1e3)
    mid = (f > 1e3) & (f <= 60e3)
    return dict(label=label, fs_Hz=float(1.0 / (tu[1] - tu[0])),
                nyquist_Hz=float(nyq), n_points=int(n), bin_Hz=float(df),
                detrend='mean subtraction (DC removed)',
                window='Hann, amplitude corrected by 1/sum(w)',
                top_peaks=peaks,
                amp_2_1kHz_V=float(amp[lf].max()) if lf.any() else 0.0,
                amp_1k_60kHz_V=float(amp[mid].max()) if mid.any() else 0.0,
                amp_60_140kHz_V=float(amp[sw].max()) if sw.any() else 0.0)


def switching_numbers(c, a, b):
    """Cycle-level numbers from the ACTUAL raw: VGS edges (gate-src), gate
    period/frequency, inductor ripple, and offline inductor slope estimate."""
    t, hv = c['time'], c['v(hv)']
    gate, src = c['v(gate)'], c['v(src)']
    il = c['i(lpower)']
    i, j = np.searchsorted(t, [a, b])
    vgs = (gate - src)[i:j]
    tt = t[i:j]
    on = vgs > 4.862  # Level-3 VTO from st.lib
    edges = np.flatnonzero(np.diff(on.astype(np.int8)) == 1)
    if len(edges) < 3:
        return dict(cycles=len(edges), note='too few cycles')
    periods = np.diff(tt[edges])
    duty = []
    for e in edges[:-1]:
        seg = on[e:e + (edges[1] - edges[0])]
        duty.append(float(seg.mean()))
    # inductor voltage during OFF intervals: V(drain)-V(hv) across L
    vsw = (c['v(drain)'] - hv)[i:j]
    vo = float(hv[i:j].mean())
    vin = float(c['v(in)'][i:j].mean())
    io = vo / (1 / (1 / 5200 + 1 / 90900 + 1 / 201900.6))  # effective R, see load calc
    return dict(cycles=int(len(edges)),
                f_median_Hz=float(1.0 / np.median(periods)),
                f_mean_Hz=float(1.0 / periods.mean()),
                period_jitter_pp_ns=float(np.ptp(periods) * 1e9),
                duty_mean=float(np.mean(duty)),
                V_swing_min_V=float(vsw.min()), V_swing_max_V=float(vsw.max()),
                I_L_pp_A=float(np.ptp(il[i:j])), I_L_mean_A=float(il[i:j].mean()),
                I_L_min_A=float(il[i:j].min()), I_L_max_A=float(il[i:j].max()),
                v_out_mean_V=vo, v_in_mean_V=vin)


def main():
    findings = {}
    t_full = []
    enc_ok = True
    c = lab.native(RAW)
    t = c['time']
    hv = c['v(hv)']  # lab.native lowercases the raw variable names
    findings['raw'] = dict(path=str(RAW), sha256=sha(RAW), size_bytes=RAW.stat().st_size,
                           points=int(len(t)), variables=sorted(c.keys()),
                           t_first_s=float(t[0]), t_last_s=float(t[-1]),
                           dt_min_s=float(np.diff(t).min()), dt_max_s=float(np.diff(t).max()),
                           flags='real double forward nocompression (binary, 13 vars)',
                           native_reader='lab.native memmap (R2/lab.py)')
    findings['netlist'] = dict(path=str(CIR), sha256=sha(CIR),
                               text=CIR.read_text(encoding='ascii'))
    findings['model_hashes'] = {n: sha(BASE / n) for n in
                                ['controller.sub', 'st.lib', 'diode.lib', 'ss14.lib']}
    findings['log'] = dict(path=str(BASE / 'circuit.log'),
                           sha256=sha(BASE / 'circuit.log'),
                           note='original R1 native LTSpice log; not regenerated here')
    findings['command'] = json.loads((BASE / 'command.json').read_text(encoding='utf8'))

    # ---------- 1. windows: time-weighted mean and TRUE raw Vpp ----------
    windows = [weighted_stats(t, hv, a, b) for a, b in WINDOWS]
    deciles = []
    for k in range(10):
        a, b = 0.04 + 0.002 * k, 0.042 + 0.002 * k
        windows_ = weighted_stats(t, hv, a, b)
        deciles.append(dict(t=a, mean_V=windows_['mean_V'], raw_Vpp=windows_['raw_Vpp']))
    findings['windows_5ms'] = windows
    findings['deciles_2ms'] = deciles
    # is the trace settled at all? compare halves of last 10 ms
    last10 = weighted_stats(t, hv, 0.050, 0.060)
    findings['trend_test_10ms'] = dict(
        mean_50_55_V=windows[2]['mean_V'], mean_55_60_V=windows[3]['mean_V'],
        delta_mV=(windows[3]['mean_V'] - windows[2]['mean_V']) * 1e3,
        total_Vpp_50_60=last10['raw_Vpp'],
        within_band=bool(last10['raw_Vpp'] <= SETTLE_BAND_V and
                         abs(windows[3]['mean_V'] - windows[2]['mean_V']) <= SETTLE_BAND_V))
    # sustained-band entry: last time |hv-mean_final| exceeds band
    lo, hi = last10['mean_V'] - SETTLE_BAND_V, last10['mean_V'] + SETTLE_BAND_V
    outside = np.flatnonzero((hv < lo) | (hv > hi))
    findings['settling_probe'] = dict(
        band_V=SETTLE_BAND_V, reference_final_mean_V=last10['mean_V'],
        last_excursion_s=float(t[outside[-1]]) if len(outside) else None,
        observation_end_s=float(t[-1]),
        margin_to_end_s=float(t[-1] - t[outside[-1]]) if len(outside) else None,
        verdict='NOT_SETTLED_IN_OBSERVED_60MS' if (len(outside) and t[outside[-1]] > 0.050) else 'review')
    # how tight does the last decile look vs a 1 ms smoothing of a 2 ms bin?
    findings['settling_probe']['band_floor_from_switching_alone_V'] = float(
        weighted_stats(t, hv, 0.058, 0.060)['raw_Vpp'])

    # ---------- 2. FFT on uniformly resampled data ----------
    fs = 20e6
    tu, hu = resample_uniform(t, hv, fs)
    fft_all = fft_features(tu, hu, 'whole 0-60ms @fs=20MHz')
    fft_late = []
    for a, b in WINDOWS:
        i, j = np.searchsorted(t, [a, b])
        tu_w, hu_w = resample_uniform(t[i:j + 1], hv[i:j + 1], fs)
        fft_late.append(fft_features(tu_w, hu_w, f'{a*1e3:.0f}-{b*1e3:.0f}ms @fs=20MHz'))
    findings['fft'] = dict(method='Hann window, mean detrend, uniform resample at fs=20 MHz '
                                  '(nyquist 10 MHz) from native adaptive-step samples; '
                                  'linear interpolation acts as a mild low-pass/alias '
                                  'shaper on content above the mean sample rate (~105 kHz '
                                  'in the native trace), so switching harmonics above '
                                  '10 MHz are aliased and NOT resolved; envelope content '
                                  'below 1 kHz is resolved exactly. Windows as labelled.',
                           whole_trace=fft_all, windows=fft_late)
    findings['nyquist'] = dict(fs_resampled_Hz=fs, nyquist_Hz=fs / 2,
                               native_mean_sample_rate_Hz=float(1.0 / np.diff(t).mean()),
                               native_min_sample_rate_Hz=float(1.0 / np.diff(t).max()),
                               note='Native trace is NOT uniformly spaced (adaptive '
                                    'LTSpice step); spacing irregularity is a documented '
                                    'alias/smearing source for any FFT of the true raw.',
                               maxstep_s=float(np.diff(t).max()))
    findings['fft_selfcheck'] = dict(
        first_draft_error='An earlier draft built the frequency axis from a '
                          'recomputed span expression; it produced nyquist_Hz=0.0025 '
                          'and empty peak lists. That erroneous intermediate is '
                          'recorded here and was NOT used for any conclusion.',
        fix='frequency axis now taken from np.fft.rfftfreq(n, dt) with dt measured '
            'from the actual uniform grid',
        san_checks=dict(
            nyquist_equals_fs_over_2=[(w['nyquist_Hz'] - w['fs_Hz'] / 2) < 1e-6 for w in fft_late],
            bin_equals_fs_over_N=[abs(w['bin_Hz'] - w['fs_Hz'] / w['n_points']) < 1e-3
                                  for w in fft_late],
            peaks_populated=[len(w['top_peaks']) > 0 for w in fft_late]))

    # ---------- 3. envelope vs switching, from the actual raw ----------
    sw = []
    for a, b in WINDOWS:
        sw.append(dict(t=a, **switching_numbers(c, a, b)))
    findings['switching_late'] = sw
    # envelope: 5ms boxcar mean of the true raw (low-frequency component)
    a, b = 0.04, 0.06
    i, j = np.searchsorted(t, [a, b])
    tw, hw = t[i:j], hv[i:j]
    bw = 5e-3
    env = []
    for k in range(4):
        lo_, hi_ = 0.04 + bw * k, 0.04 + bw * (k + 1)
        m = (tw >= lo_) & (tw <= hi_)
        env.append(dict(t_mid=0.5 * (lo_ + hi_), box_mean_V=float(hw[m].mean())))
    findings['envelope_5ms_box'] = env
    findings['envelope_vs_switching'] = dict(
        switching_component_Vpp=float(statistics.fmean(w['raw_Vpp'] for w in windows)),
        note='Raw Vpp reported above is the TRUE raw total; the switching component is '
             'bounded here only by the FFT switching-band amplitude and by the '
             'per-cycle I_L ripple, not by a de-noised reconstruction.')

    # ---------- 4. load, CCM, RHP zero, current-mode pole, compensation ----------
    rl, rb, rf_up, rf_lo = 5200.0, 90900.0, 100000.0 + 100000.0, 1900.6
    r_bleed = 1.0 / (1.0 / rb + 1.0 / rb)     # two strings, each 90.9k+90.9k
    r_fb = rf_up + rf_lo
    r_eff = 1.0 / (1.0 / rl + 1.0 / r_bleed + 1.0 / r_fb)
    cout = 20.3e-6
    lh = 150e-6
    vref = 1.6
    vout_target = vref * (1 + rf_up / rf_lo)
    rcs, l_sense = 0.062, 150e-6
    ilim_a = 0.110 / rcs
    fsw = sw[-1]['f_median_Hz']
    duty = sw[-1]['duty_mean']
    vo = sw[-1]['v_out_mean_V']
    vin = sw[-1]['v_in_mean_V']
    io = vo / r_eff
    # CCM RHP zero for a BOOST (1-D)^2 R/(2 pi L) -- compute it, but the
    # MEASURED duty (0.272) and V(drain) swing (~+171 V relative to V(hv))
    # show the power stage is NOT the D=84-87% boost that R1's ideal CCM
    # estimate assumed. The formula is therefore reported only as a
    # formula-on-measured-D artifact and explicitly NOT used as the plant zero.
    rhp_boost_formula = (1 - duty) ** 2 * r_eff / (2 * math.pi * lh)
    rhp_applicable = bool(duty > 0.5)
    # DCM/BCM bound: in DCM there is NO RHP zero in the control-to-output
    # transfer function; the pole and gain change. Reported as a bound only.
    # Current-mode averaged output pole: fp ~= 2/(2 pi R C) for a boost with
    # resistive load in the CCM average-current-mode small-signal model
    # (product of output RC and the input-side RC = R(1-D)^2 C / 2 ... ), the
    # conservative, mode-independent bound is 1/(pi R C) and the DCM-ish
    # bound 2/(2 pi R C) = 1/(pi R C). Both coincide -> report 1/(pi R C).
    fp_cm = 1.0 / (math.pi * r_eff * cout)
    fp_rc = 1.0 / (2 * math.pi * r_eff * cout)          # passive RC, for contrast
    fz_comp = 1.0 / (2 * math.pi * 22000 * 6.8e-9)      # RCOMP*CCOMP zero
    f_400ns = 1.0 / (2 * math.pi * 400e-9)
    findings['small_signal'] = dict(
        Vref_assumed_V=vref, Vout_target_V=float(vout_target),
        R_load_ohm=rl, R_bleed_ohm=float(r_bleed), R_fb_ohm=r_fb,
        R_eff_ohm=float(r_eff), C_out_F=cout, L_H=lh,
        P_measured_W=float(vo ** 2 / r_eff), I_out_measured_A=float(io),
        I_out_power_budget_A=float(5.900417 / 175.1),
        P_budget_W=5.900417,
        duty_measured=duty, fsw_measured_Hz=fsw,
        IL_avg_A=float(sw[-1]['I_L_mean_A']), IL_pp_A=float(sw[-1]['I_L_pp_A']),
        I_lim_A_nominal=float(ilim_a),
        DCM_peak_check_A=float(2 * io / (1 - duty)),
        conduction_mode_outline='CCM iff I_L valley > 0; measured valley '
                               f"{sw[-1]['I_L_min_A']:.3f} A over the late window",
        f_RHP_zero_CCM_formula_Hz=float(rhp_boost_formula),
        RHP_applicable=rhp_applicable,
        RHP_mode_caveat='NOT APPLIED as the plant zero. The (1-D)^2 R/(2 pi L) form is a '
                        'BOOST CCM average-model result requiring D near the R1 ideal '
                        'boost estimate 0.845-0.873. The MEASURED late-window duty is '
                        f'{duty:.4f} and the measured inductor current goes NEGATIVE '
                        f"({sw[-1]['I_L_min_A']:.3f} A), so the CCM boost formula is "
                        'outside its validity here (R1 reported 882/1134 late cycles with '
                        'a zero crossing). In DCM there is no RHP zero in the '
                        'control-to-output transfer; the value is recorded only to show '
                        'the formula-on-measured-D residual and is NOT an estimate of any '
                        'actual RHP zero. Actual topology/conduction mode remains '
                        'INCONCLUSIVE from this offline pass.',
        f_out_pole_CM_Hz=float(fp_cm),
        f_out_pole_note='Current-mode averaged output pole 1/(pi R C) using measured '
                        'R_eff/V(out)/C_out. This 1/(pi R C) form is the constant-power '
                        'input-side RC approximation from R1 compensation_screen.py, '
                        'NOT a validated mode-resolved current-mode plant; it is twice the '
                        'passive RC pole. Derivation only, no Bode measurement, no '
                        'margins.',
        f_passive_RC_Hz=float(fp_rc),
        f_comp_zero_Hz=float(fz_comp),
        f_comp_pole_Hz=float(f_400ns),
        comp_zero_over_plant_pole=float(fz_comp / fp_cm),
        existing_compensation=dict(RCOMP=22e3, CCOMP=6.8e-9, CHF=100e-12, RT=140e3),
        recommendation='No compensation edit is justified by this offline analysis and '
                       'none is proposed. The observed residual is a slow envelope drift '
                       '(window means 162.18/166.94/170.44/169.81 V over successive 5 ms '
                       'windows) rather than a fast limit-cycle at the 100.85 kHz switching '
                       'rate, and the estimated CM output pole (~3.4 Hz) is far below the '
                       'existing RCOMP*CCOMP zero (~1.06 kHz), so the chain is not shown '
                       'to be mis-compensated. Conversely nothing here proves it adequate: '
                       'the plant is not mode-resolved, the ~170V topology assumption '
                       'contradicts the measured duty, and no gain/phase margin exists. '
                       'Keep 22k/6.8n/100p/140k unchanged and measure first.',
        recommendation_values_justified=False)

    # ---------- 5. extended unchanged 200 ms observation ----------
    # decay-rate support: log-ratio of successive *excursion* amplitudes about
    # the late mean, NOT a settling claim; only shows the tail is still moving.
    exc = [windows[k]['max_V'] - last10['mean_V'] for k in range(4)]
    tau_est = []
    for k in range(1, 4):
        if exc[k] > 0 and exc[k - 1] > exc[k]:
            tau_est.append(5e-3 / math.log(exc[k - 1] / exc[k]))
    findings['envelope_decay_probe'] = dict(
        positive_excursion_V=[float(v) for v in exc],
        estimated_tau_s=[float(v) for v in tau_est],
        note='Crude single-exponential probe on positive excursions above the '
             '55-60ms mean. The sign change between window 3 and 4 (mean falls '
             'from 170.44 to 169.81 V) breaks any monotonic-decay assumption, so '
             'this is NOT a settling time and NOT an extrapolation to 200 ms.')
    findings['extended_observation'] = dict(
        recommendation='RECOMMEND a single unchanged 200 ms observation run in a later '
                       'round under principal Codex approval, using lab.full(stop=0.2) '
                       'with the identical models/tolerances and the SAME 200ns max '
                       'step. It is the only way to see whether the 200 Hz envelope '
                       'component and the ~630 mV/5ms drift continue, reverse or decay. '
                       '60 ms is NOT qualified as settled here and no 200 ms outcome is '
                       'predicted.',
        why='settling_probe.last_excursion_s reaches the trace end; delta_mV=-629.6 '
            'over 50-55 vs 55-60 ms; dominant non-DC FFT lobe is 200-600 Hz, which '
            'the 5 ms windows resolve but which is not demonstrated to be finished',
        proposed_only_not_executed=True, simulations_run=0,
        cost_caveat='R1 wall time was ~600 s for 60 ms at 200 ns max step; a 200 ms stop '
                    'is ~3.3x and must be budgeted by the principal, not assumed.')

    # ---------- 6. explicit assertions (evidence-level, not acceptance) ----------
    findings['assertions'] = dict(
        no_simulation_performed=True,
        all_four_5ms_windows_present=len(windows) == 4,
        vpp_computed_from_raw=True,
        time_weighted_mean_used=True,
        fft_uniform_resampled=True,
        nyquist_documented=True,
        not_qualified_as_settled=abs(windows[3]['mean_V'] - windows[2]['mean_V']) > SETTLE_BAND_V
        or windows[3]['raw_Vpp'] > SETTLE_BAND_V,
        component_or_model_modified=False)
    findings['evaluation_status'] = 'ANALYSIS_ONLY_NOT_SETTLED'

    (OUT / 'analysis.json').write_text(json.dumps(findings, indent=2, ensure_ascii=False) + '\n',
                                       encoding='utf8', newline='\n')

    # console summary
    print('wins', [(w['t_start'], round(w['mean_V'], 4), round(w['raw_Vpp'], 4)) for w in windows])
    print('trend', findings['trend_test_10ms'])
    print('settle', findings['settling_probe'])
    print('fsw', round(fsw, 1), 'duty', round(duty, 4), 'io', round(io, 5),
          'rhp_formula*', round(rhp_boost_formula, 1), 'applicable', rhp_applicable,
          'fp_cm', round(fp_cm, 2), 'fz', round(fz_comp, 1))
    print('sw', sw[-1])


if __name__ == '__main__':
    main()
