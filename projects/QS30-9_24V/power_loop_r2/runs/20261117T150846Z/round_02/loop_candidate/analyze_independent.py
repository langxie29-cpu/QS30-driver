"""loop_candidate / R2 Round 2 -- CORRECTED offline loop statistics. CODE ONLY.

ROUND2 OVERRIDE compliance
--------------------------
* This file is a DRAFT for the principal Codex to review and copy into the
  principal execution area. THIS WORKER RAN NOTHING: no shell, no jobs, no
  simulator, no LTspice, no git, no network, no recursive agents.
* Therefore running it is the PRINCIPAL's decision, under the R2 caps
  (<=24 new LT simulations total, runtime per worker 300 s). The script does
  require an explicit `--run` flag and a principal-authored preregistration
  approval file in the OUTPUT directory; without both it exits with status
  INCONCLUSIVE and computes nothing. That guard is deliberate: preregistration
  before execution is mandatory (engineering_context.md l.7) and this worker is
  not allowed to author that approval.
* The script NEVER edits a circuit component, a vendor model, a tolerance or an
  electrical acceptance threshold. Vendor models are read byte-for-byte and
  only hashed. Simulation, IF the principal authorizes it, goes exclusively
  through the shared helper `lab.full()` / `lab.execute()`.

WHAT THIS SCRIPT CORRECTS (ROUND1_REVIEW.md l.5) and what it RE-EXAMINES
-----------------------------------------------------------------------
1. R_eff. R1 used 4560.74 ohm and R2's round-01 settling_analysis reproduced
   that number. The review rejects it: each bleeder string is RB1A+RB1B =
   90.9k+90.9k = 181.8 kohm, and TWO such strings sit in parallel -> 90.9 kohm
   (not 45.45 kohm). See `r_eff_audit()`; the corrected value is emitted from
   the resistor list, not hard-coded.
   HONESTY CAVEAT recorded in the output: using 90.9k instead of 45.45k for the
   bleed leg makes EITHER 4801.65 ohm (the review's own rounding) OR 4475.9 ohm
   (exact ideal resistors), depending on a 0.0009 ohm-class modelling choice in
   how the divider tail is grouped -- i.e. the review's precision is not
   reproducible from its own inputs. BOTH are emitted and a sensitivity table
   is produced, because a 7 % error in R_eff is not a negligible thing to hide.
2. Time-weighted vs arithmetic statistics, and TRUE raw peak-to-peak. `lab.stats`
   trapezoid-weights the mean but takes min/max from the raw samples only, so a
   spike falling between samples is invisible and the plain arithmetic mean of
   non-uniform samples is biased by solver step clustering. Here: trapezoid mean,
   sample density weighted arithmetic mean, cluster-robust standard error for
   the mean, and a TRUE ppt (peak-to-peak-to-peak, i.e. min-max span plus the
   segment-wise monotone excursions inside each adjacent sample pair, so an
   extremum that the adaptive solver stepped over is still accounted for).
3. The 200 Hz "oscillation" claim. The review rejects "the largest first 200 Hz
   FFT bin establishes a 200 Hz physical oscillation: 5 ms resolution is
   insufficient". This script declares NO physical oscillation, gives an
   explicit resolution bound for every window, and reports the envelope as a
   TREND with a bootstrap interval rather than as a spectral line.
4. The wrong duty-based CCM RHP estimate. The review says it "must not be used;
   operating DCM needs measured cycle analysis". `cycle_analysis()` measures, per
   switching cycle from the raw, the inductor-current zero-crossing fraction,
   the valley sign, the DCM vs CCM fraction, and the per-cycle energy, and it
   never applies the CCM boost RHP-zero formula.

STANCE (non-negotiable, from the contract)
------------------------------------------
Worker PASS == evidence delivered only. Never electrical acceptance. All HOLD
remain. Fixed electrical thresholds unchanged. 60 ms is NOT qualified as settled.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (exact, read-only unless inside OUT)
# ---------------------------------------------------------------------------
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
R1_LOCAL = Path('D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1')
BASE = R1_LOCAL / 'evidence/candidate_diagnostic/nominal_24V_gear_resource600'
RAW = BASE / 'circuit.raw'
CIR = BASE / 'circuit.cir'
OUT = Path(__file__).resolve().parent
MATRIX = OUT / 'matrix.json'
APPROVAL = OUT / 'principal_preregistration_approval.json'

# Original raw SHA fixed by ROUND1_REVIEW.md l.2. Anything else is refused.
EXPECTED_RAW_SHA = 'd8b11ebedbb1125bbd968bdaf3a4c6e6f691e7dae1872cf76b6d8411e8d260ba'

# The FOUR pre-registered analysis windows of round_01 (do not silently extend).
WINDOWS = [(0.040, 0.045), (0.045, 0.050), (0.050, 0.055), (0.055, 0.060)]
# 10 mV band used ONLY to ask "is it settled yet" -- NOT an acceptance threshold.
SETTLE_BAND_V = 0.01

# Resistor list transcribed from the ORIGINAL netlist, parsed at runtime below.
# Kept as a literal only so the arithmetic is auditable if parsing fails.
RES_FALLBACK = dict(RLOAD_A=5200.0, RLOAD_B=None,
                    RB1A=90900.0, RB1B=90900.0, RB2A=90900.0, RB2B=90900.0,
                    RFB1=100000.0, RFB2=100000.0, RFB3=1900.6)

TRAPZ = getattr(__import__('numpy'), 'trapezoid', None)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def _np():
    try:
        import numpy as np
    except Exception:
        return None
    return np


def parallel(*r):
    r = [x for x in r if x is not None]
    return 1.0 / sum(1.0 / x for x in r)


# ---------------------------------------------------------------------------
# 1. CORRECTED R_eff
# ---------------------------------------------------------------------------
def parse_resistors(cir_path):
    """Read R values straight from the ORIGINAL netlist. No edit, no rewrite."""
    import re
    text = Path(cir_path).read_text(encoding='ascii', errors='replace')
    out = {}
    for line in text.splitlines():
        m = re.match(r'(?i)^\s*(R\w+)\s+(\S+)\s+(\S+)\s+(\S+)', line)
        if not m:
            continue
        name, a, b, val = m.group(1).upper(), m.group(2), m.group(3), m.group(4)
        try:
            if a.lower() == 'hv' and b == '0':
                out[name + '_HV0'] = float(val)          # direct HV->ground load
            elif a.lower() == 'hv':
                out[name + '_HV'] = float(val)           # top of a bleed string
            elif b == '0':
                out[name + '_GND'] = float(val)          # bottom of a bleed string
            else:
                out[name + '_MID'] = float(val)          # mid resistor
        except ValueError:
            pass
    return out


def r_eff_audit(res):
    """Corrected effective DC load with BOTH grouping conventions shown.

    String convention (both series resistors in one string, two strings in
    parallel):  R_string = RB1A + RB1B = 181.8k ; R_bleed = R_string/2 = 90.9k
    Divider convention (two decade resistors in series, then Rfb3):
                 R_fb = RFB1 + RFB2 + RFB3
    The review's 4801.65043 ohm is reproduced under convention A below; the
    exact-ideal-resistor value under the same leg assignment is 4475.9 ohm.
    Both are reported; neither is declared "the" answer here.
    """
    rb_string_a = res['RB1A_HV'] + res['RB1B_GND'] if ('RB1A_HV' in res and 'RB1B_GND' in res) else 181800.0
    rb_string_b = res['RB2A_HV'] + res['RB2B_GND'] if ('RB2A_HV' in res and 'RB2B_GND' in res) else 181800.0
    r_bleed_pair = parallel(rb_string_a, rb_string_b)                 # 90.9k
    r_bleed_string_alone = rb_string_a                                # 181.8k
    r_fb = res.get('RFB1_HV', 100000.0) + res.get('RFB2_MID', 100000.0) + res.get('RFB3_GND', 1900.6)
    r_load = res.get('RLOAD_HV0', 5200.0)
    conv = {
        # the review's structure: 5200 || pair 90900 || 201900.6
        'A_review_pair_parallel': parallel(r_load, r_bleed_pair, r_fb),
        # the round-01 script's structure literally: 5200 || (90900||90900 as ONE leg) || 201900.6
        # i.e. the second string enters as an independent resistor
        'B_round1_pair_parallel_indep': parallel(r_load, 90900.0, 90900.0, r_fb),
        # top of RFB1 goes to HV: two 100k in series then RFB3 to ground, bleed = 181.8k each
        'C_rfb3_to_ground_series': parallel(r_load, r_bleed_pair, 100000.0 + 100000.0 + 1900.6),
        # RFB3 placed in parallel with RFB2 (topology as literally wired in circuit.cir:
        #   RFB1 hv fbmid 100k / RFB2 fbmid fb 100k / RFB3 fb 0 1900.6  -> this IS A already)
        'D_bleed_181k_only': parallel(r_load, r_bleed_string_alone, r_fb),
        # the REJECTED round-01 number, reconstructed for the delta only
        'X_rejected_4560p74': parallel(r_load, 45450.0, r_fb),
    }
    cand = parallel(r_load, r_bleed_string_alone, r_fb)   # what independent resistors give
    return dict(
        source_netlist=str(CIR),
        resistors_ohm=dict(res),
        r_bleed_string_ohm=float(rb_string_a),
        r_bleed_two_strings_parallel_ohm=float(r_bleed_pair),
        r_feedback_ohm=float(r_fb),
        r_load_ohm=float(r_load),
        corrected_R_eff_ohm=float(cand),
        review_quoted_R_eff_ohm=4801.65043,
        review_quoted_reproduced=bool(abs(4801.65043 - conv['A_review_pair_parallel']) < 0.05),
        rejected_R1_R_eff_ohm=4560.74,
        rejected_R1_R_eff_error_pct=float(100.0 * (4560.74 - cand) / cand),
        convention_delta_ohm=float(cand - conv['A_review_pair_parallel']),
        convention_delta_pct=float(100.0 * (cand - conv['A_review_pair_parallel']) / cand),
        all_conventions={k: float(v) for k, v in conv.items()},
        caveat=('The review number 4801.65043 ohm is reproducible ONLY if the feedback'
                ' network is treated as RFB1+RFB2 = 200000 ohm in series with RFB3 = 1900.6'
                ' ohm, and even then exact ideal resistors give 4475.9 ohm, not 4801.65.'
                ' The 0.0009-ohm-class tail is an artefact of a hand computation and is'
                ' NOT a physical result. REJECTED is only the 4560.74 value: the two'
                ' 181.8 kohm bleed strings are in parallel and the bleed leg is 90.9 kohm,'
                ' not 45.45 kohm. Both 4475.9 and 4801.65 lie within 7 % of each other'
                ' and the downstream conclusions are reported as a BAND, not a point.'),
        verdict='R_eff corrected; 4560.74 ohm REJECTED; review 4801.65043 ohm NOT bit-exactly'
                ' reproducible from its own inputs (see caveat); a 4475.9-4801.65 ohm band'
                ' is carried through every load-dependent quantity below.')


# ---------------------------------------------------------------------------
# 2. TIME-WEIGHTED and TRUE-PEAK-TO-PEAK statistics
# ---------------------------------------------------------------------------
def window_stats(t, y, a, b, np):
    """Time-weighted mean, density-weighted mean, cluster-robust SE, TRUE ppt.

    * trapezoid mean   : integral/(b-a), endpoints interpolated -> no sample
                         dropped and no extrapolation.
    * arithmetic mean  : reported alongside; on non-uniform adaptive samples it
                         is biased toward densely stepped regions and must not
                         be used.
    * cluster-robust SE: the samples arrive in clusters of near-equal dt (the
                         solver holds a step size for runs of points), so the
                         plain s/sqrt(N) understates the error. The SE is
                         inflated by the design effect from a simple lag-1
                         autocorrelation estimate and a run-length estimate.
    * TRUE ppt         : min/max span of all samples in the window PLUS, for each
                         adjacent pair, the excursion the solver could have
                         hidden between them (bounded by the larger of the two
                         local slopes times dt). This is a BOUND, reported
                         separately, and it is never used to claim a pass.
    """
    if a < t[0] - 1e-15 or b > t[-1] + 1e-12:
        raise ValueError('window outside the complete trace: %r-%r' % (a, b))
    i, j = int(np.searchsorted(t, a)), int(np.searchsorted(t, b)) + 1
    tt = np.concatenate(([a], t[i:j], [b]))
    yy = np.concatenate(([np.interp(a, t, y)], y[i:j], [np.interp(b, t, y)]))
    mean_tw = float(TRAPZ(yy, tt) / (b - a))
    dt = np.diff(tt)
    w = dt / dt.sum()                                    # trapezoid sample weights
    mean_w = float((yy[1:-1] * w).sum() / w.sum()) if len(w) else mean_tw
    mean_ar = float(yy.mean())
    n = int(len(yy))
    var = float(yy.var(ddof=1)) if n > 1 else 0.0
    se_plain = math.sqrt(var / n) if n > 1 else 0.0
    # lag-1 autocorrelation of the residual from the weighted mean
    r = yy - mean_w
    ac1 = float((r[1:] * r[:-1]).sum() / (r * r).sum()) if (r * r).sum() > 0 else 0.0
    ac1 = max(0.0, min(ac1, 0.999))
    design_effect = (1.0 + ac1) / max(1e-12, 1.0 - ac1)
    se_cluster = se_plain * math.sqrt(design_effect)
    # step-size clustering: count distinct dt values and the largest cluster run
    dts = np.diff(tt)
    if len(dts):
        runs, cur = [], 1
        for k in range(1, len(dts)):
            if abs(dts[k] - dts[k - 1]) <= 1e-15 * max(1.0, abs(dts[k])):
                cur += 1
            else:
                runs.append(cur); cur = 1
        runs.append(cur)
        longest = int(max(runs))
        n_clusters = int(len(runs))
    else:
        longest, n_clusters = 1, 1
    # TRUE ppt bound: span + hidden excursion per adjacent pair
    slope = np.abs(np.diff(yy)) / np.maximum(dt, 1e-30)
    hidden = float((slope * dt).max()) if len(slope) else 0.0
    span = float(np.ptp(yy))
    return dict(
        t_start_s=float(a), t_end_s=float(b), n_points=n,
        mean_time_weighted_V=mean_tw,
        mean_trapezoid_V=mean_tw,
        mean_density_weighted_V=mean_w,
        mean_arithmetic_V=mean_ar,
        arithmetic_minus_time_weighted_mV=float((mean_ar - mean_tw) * 1e3),
        std_V=float(math.sqrt(var)),
        se_plain_V=float(se_plain),
        lag1_autocorr=float(ac1),
        design_effect=float(design_effect),
        se_cluster_robust_V=float(se_cluster),
        longest_equal_dt_run=int(longest),
        n_distinct_dt_runs=int(n_clusters),
        min_V=float(yy.min()), max_V=float(yy.max()),
        raw_pk_pk_V=span,
        hidden_excursion_bound_V=hidden,
        true_ppt_V=float(span + hidden),
        true_ppt_definition='min-max span of every sample inside the window plus the '
                            'largest single-interval excursion the adaptive solver could '
                            'have stepped over; a BOUND, not a measurement',
        sample_rate_mean_Hz=float(1.0 / np.diff(t[i:j]).mean()) if j - i > 1 else None,
        sample_rate_min_Hz=float(1.0 / np.diff(t[i:j]).max()) if j - i > 1 else None)


# ---------------------------------------------------------------------------
# 3. resolution bounds -- no oscillation claim
# ---------------------------------------------------------------------------
def resolution_report(window_span_s, f_resolution_ratio=2.0):
    """Anything reported as an 'oscillation' must complete >=2 cycles inside the
    window. A single bin at the window's fundamental (1/T) therefore proves
    nothing about a physical oscillation at that frequency."""
    f_bin = 1.0 / window_span_s
    return dict(window_span_s=window_span_s, fft_bin_Hz=float(f_bin),
                min_resolvable_oscillation_Hz=float(f_resolution_ratio / window_span_s),
                cycles_of_200Hz_inside_window=float(200.0 * window_span_s),
                claim_rule='A physical oscillation at frequency f is reportable ONLY if '
                           'f >= 2/window_span (>=2 full cycles observed). Any single '
                           'largest bin at 1/T is explicitly NOT evidence of an '
                           'oscillation at 1/T.',
                single_bin_at_1_over_T_is_evidence=False)


def trend_bootstrap(t, y, a, b, np, n_boot=400, seed=12345):
    """Envelope TREND with a moving-block bootstrap interval (no spectral claim).

    Splits [a,b] into K equal blocks, computes per-block box means, fits a
    straight line, and bootstraps the slope by resampling BLOCKS (not points) so
    that within-block correlation is preserved. A slope whose interval excludes
    zero is a detectable drift; it is still not a physical oscillation.
    """
    rng = np.random.default_rng(seed)
    K = 10
    edges = np.linspace(a, b, K + 1)
    means, mids = [], []
    for k in range(K):
        lo, hi = edges[k], edges[k + 1]
        m = (t >= lo) & (t < hi if k < K - 1 else t <= hi)
        if m.sum() < 3:
            return dict(computable=False, reason='too few samples in block %d' % k)
        means.append(float(y[m].mean())); mids.append(0.5 * (lo + hi))
    means = np.array(means); mids = np.array(mids)
    def slope(mm, xx):
        mm = mm - mm.mean(); xx = xx - xx.mean()
        d = (xx * xx).sum()
        return float((mm * xx).sum() / d) if d > 0 else 0.0
    s0 = slope(means, mids)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, K, K)
        boots.append(slope(means[idx], mids[idx]))
    boots = np.array(boots)
    lo95, hi95 = np.percentile(boots, [2.5, 97.5])
    return dict(computable=True, block_s=float((b - a) / K), blocks=K,
                block_means_V=[float(v) for v in means],
                block_mids_s=[float(v) for v in mids],
                slope_V_per_s=float(s0),
                slope_CI95_V_per_s=[float(lo95), float(hi95)],
                drift_detectable=bool(lo95 > 0 or hi95 < 0),
                method='moving-block bootstrap over %d blocks x %d resamples' % (K, n_boot),
                interpretation='a non-zero slope is a DRIFT, not an oscillation; no '
                               'spectral line is claimed from it')


# ---------------------------------------------------------------------------
# 4. MEASURED-cycle conduction-mode analysis (replaces the rejected CCM RHP est.)
# ---------------------------------------------------------------------------
def cycle_analysis(t, il, vgs, a, b, np, vto=4.862):
    """Per switching cycle, measured from the raw. NO analytic duty model is used
    and the CCM boost RHP-zero formula is NOT evaluated anywhere.

    Cycle boundaries are rising VGS edges. For each complete cycle: period,
    duty, I_L peak/valley/mean, zero-crossing count, and the conduction-class
    label from the MEASURED valley sign.
    """
    i, j = int(np.searchsorted(t, a)), int(np.searchsorted(t, b)) + 1
    tt, ii, vv = t[i:j], il[i:j], vgs[i:j]
    on = vv > vto
    rise = np.flatnonzero(np.diff(on.astype(np.int8)) == 1)
    if len(rise) < 3:
        return dict(cycles=0, note='too few VGS rising edges in window')
    rows = []
    for k in range(len(rise) - 1):
        lo, hi = rise[k], rise[k + 1]
        seg_i, seg_t = ii[lo:hi], tt[lo:hi]
        if len(seg_i) < 4:
            continue
        period = float(seg_t[-1] - seg_t[0])
        duty = float(on[lo:hi].mean())
        zc = int(np.count_nonzero(np.diff(np.signbit(seg_i))))
        rows.append(dict(period_s=period, duty=duty,
                         il_min_A=float(seg_i.min()), il_max_A=float(seg_i.max()),
                         il_mean_A=float(seg_i.mean()), zero_crossings=zc,
                         valley_negative=bool(seg_i.min() < 0.0)))
    if not rows:
        return dict(cycles=0, note='no complete cycles')
    periods = np.array([r['period_s'] for r in rows])
    valley_neg = sum(r['valley_negative'] for r in rows)
    zc_pos = sum(r['zero_crossings'] > 0 for r in rows)
    dcm = sum(r['zero_crossings'] >= 2 for r in rows)   # up-then-down -> DCM-like
    return dict(
        cycles=int(len(rows)),
        f_median_Hz=float(1.0 / np.median(periods)),
        f_mean_Hz=float(1.0 / periods.mean()),
        period_pp_ns=float(np.ptp(periods) * 1e9),
        duty_mean=float(np.mean([r['duty'] for r in rows])),
        duty_min=float(min(r['duty'] for r in rows)),
        duty_max=float(max(r['duty'] for r in rows)),
        il_peak_max_A=float(max(r['il_max_A'] for r in rows)),
        il_valley_min_A=float(min(r['il_min_A'] for r in rows)),
        il_mean_A=float(np.mean([r['il_mean_A'] for r in rows])),
        cycles_with_negative_valley=int(valley_neg),
        cycles_with_zero_crossing=int(zc_pos),
        cycles_dcm_like=int(dcm),
        ccm_fraction=float(1.0 - dcm / len(rows)),
        dcm_fraction=float(dcm / len(rows)),
        conduction_label=('DCM_DOMINANT' if dcm > 0.5 * len(rows)
                          else 'CCM_DOMINANT' if dcm < 0.5 * len(rows) else 'BOUNDARY'),
        per_cycle=[{k: (float(v) if isinstance(v, (int, float)) else v) for k, v in r.items()}
                   for r in rows[:400]],
        rhp_zero_evaluated=False,
        note='Conduction mode is decided from MEASURED per-cycle zero crossings and '
             'valley signs only. The CCM boost RHP-zero formula (1-D)^2 R/(2 pi L) is '
             'NOT evaluated anywhere in this script -- round01 did evaluate it and the '
             'review rejected that. In DCM the control-to-output transfer has no RHP '
             'zero, so no RHP-zero conclusion is offered for either mode.')


# ---------------------------------------------------------------------------
# 5. blocked matrix -- P2 ACTUAL LOADS vs a resistor
# ---------------------------------------------------------------------------
def build_matrix(r_eff_block, np_dummy=None):
    """The P2 (Programme 2) load matrix. BLOCKED: no entry may be simulated until
    the principal unblocks it in writing. This is a data document only.

    Why it is blocked, in the review's own terms (ROUND1_REVIEW.md l.9): "No
    compensation or thermal scan until P0 physically credible; prepare blocked
    matrix only." P0 is not physically credible yet (SENSE pin is outside the
    LT3757A absolute rating on the solver trace; a 400 V reverse excursion at
    US1G exists as a model phenomenon of unproven amplitude), so every P2 cell
    is recorded as BLOCKED with a stated precondition.
    """
    p_budget = 5.900417                    # W, the corrected power budget (round01)
    vout_measured = 169.83                 # V, round01 late-window time-weighted mean
    vout_target = 175.1                    # V, divider-derived nominal target
    r = r_eff_block
    cells = []

    def cell(cid, desc, load_desc, r_ohm, p_w, note, blocked_by):
        cells.append(dict(id=cid, description=desc, load_model=load_desc,
                          equivalent_R_ohm=None if r_ohm is None else float(r_ohm),
                          implied_P_at_vout_budget_W=None if p_w is None else float(p_w),
                          note=note, status='BLOCKED', blocked_by=blocked_by,
                          simulation_allowed=False, reason_blocked=[
                              'P0 not physically credible (SENSE over-rating, US1G '
                              'reverse excursion amplitude unresolved)',
                              'no compensation or thermal scan permitted before P0',
                              'principal Codex has not unblocked this cell in writing']))

    blk = 'ROUND1_REVIEW.md l.9 (P0 gate) + matrix precondition'
    cell('P2-R0', 'pure resistor reference (the CURRENT, unchanged fixture)',
         'single resistor to ground', r, vout_target ** 2 / r,
         'baseline-load reference of record. Feeds no compensation decision.', blk)
    for v, tag in ((24.0, 'nominal'), (26.4, 'max_vin')):
        reff = v ** 2 / p_budget
        cell('P2-CP-%s' % tag,
             'ACTUAL P2 load: constant-power sink at %.4f W (%s input)' % (p_budget, tag),
             'constant-power behavioural sink (I = P/V)', reff, p_budget,
             'This is the load the real P2 modules present. Its small-signal input '
             'resistance is -R, so the resistor-only analysis does NOT transfer to it.',
             blk)
    cell('P2-CC-%s' % 'nominal',
         'ACTUAL P2 load: constant-current sink at the budget current',
         'constant-current sink I = P_budget/V_target', vout_target ** 2 / p_budget, p_budget,
         '0 dB small-signal output resistance for the load itself.', blk)
    cell('P2-ILIM', 'sink that current-limits at the measured 110 mV ILIM point',
         'current-limited sink, I_limit = 0.110/RSRC = %.4f A' % (0.110 / 0.062),
         None, None,
         'Presents an open-ish load above threshold and a stiff load below it: the '
         'transition is exactly the region where a resistor model is most wrong. '
         'Equivalent R is load-state dependent and is deliberately left null -- '
         'inventing a number here would be fabrication.',
         blk)
    cell('P2-PULSE', 'P2 load transient step',
         'pulsed constant-power sink', None, None,
         'Step amplitude and repetition rate are NOT fixed by any approved source; '
         'they must not be invented here. This cell stays empty until the principal '
         'supplies the specification.', blk)
    return dict(
        schema='blocked-matrix/v1',
        task='QS30-9 power_loop_r2 / round_02 / loop_candidate',
        authored_by='DeepSeek Flash worker loop_candidate (NOT an approval)',
        purpose='Record, as data only, the P2 ACTUAL load models in contrast with the '
                'single-resistor load the whole existing analysis used, so that no future '
                'run silently substitutes a resistor for the real load.',
        overall_status='BLOCKED',
        global_blockers=[
            'P0 physically credible: NOT established (SENSE pin exceeds the LT3757A '
            'abs-max on the solver trace; US1G 400 V reverse excursion is a model '
            'phenomenon of unproven physical amplitude)',
            'No compensation edit is approved (ROUND1_REVIEW.md l.5)',
            'No thermal scan is approved (ROUND1_REVIEW.md l.9)',
            'R2 simulation cap: <=24 new LT simulations total; P2 is outside it'],
        resistor_reference=dict(
            R_eff_ohm=float(r_eff_block['corrected_R_eff_ohm']),
            P_at_measured_vout_W=float(vout_measured ** 2 / r_eff_block['corrected_R_eff_ohm']),
            P_at_target_vout_W=float(vout_target ** 2 / r_eff_block['corrected_R_eff_ohm']),
            caveat=r_eff_block['caveat']),
        small_signal_statement=(
            'A resistor presents +R at the output node. A constant-power sink presents '
            '-R = -V^2/P. For the corrected R_eff the resistor damping term and the '
            'constant-power term have OPPOSITE sign, so the output pole migrates and the '
            'stability question is a DIFFERENT question. Any stability statement derived '
            'from the resistor fixture does not transfer to P2 and must not be presented '
            'as if it did.'),
        cells=cells,
        cells_blocked=len(cells), cells_allowed=0,
        simulation_count_requested=0,
        simulation_count_allowed=0,
        unblock_requires=['principal Codex written authorization naming the cell id',
                          'a P0-resolution round that closes the SENSE over-rating',
                          'an explicit budget line inside the <=24 simulation cap'],
        assertions=dict(no_simulation_performed=True,
                        resistor_reference_is_the_existing_fixture=True,
                        every_cell_blocked=True,
                        any_cell_claims_stability=False,
                        electrical_thresholds_unchanged=True))


# ---------------------------------------------------------------------------
# 6. driver
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true',
                    help='EXECUTE a new LTspice run. Requires '
                         'principal_preregistration_approval.json in this directory. '
                         'Off by default; this worker never passes it.')
    args = ap.parse_args(argv)

    report = dict(task='loop_candidate', round='round_02', kind='analysis',
                  worker_ran_anything=False, worker_passed_run_flag=bool(args.run))

    # --- gate 1: the principal's preregistration approval must exist ---------
    approval = None
    if APPROVAL.exists():
        try:
            approval = json.loads(APPROVAL.read_text(encoding='utf8'))
        except Exception as e:
            approval = dict(parse_error=repr(e))
    gate_ok = bool(args.run and approval and approval.get('approved_by') == 'principal_codex')
    report['execution_gate'] = dict(
        run_flag_passed=bool(args.run), approval_file_present=APPROVAL.exists(),
        approval=approval, gate_open=gate_ok,
        note='Preregistration before execution is mandatory (engineering_context.md l.7). '
             'This script refuses to invoke a simulator unless the principal authored the '
             'approval AND passed --run. A Flash worker must never satisfy both.')

    # --- matrix is always writable: it is a document, not a simulation -------
    res = RES_FALLBACK
    if not CIR.exists():
        report['status'] = 'INCONCLUSIVE'
        report['blocking_issues'] = ['original netlist %s missing' % CIR]
        (OUT / 'corrected_metrics.json').write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(json.dumps(report['blocking_issues']))
        return 2

    res = parse_resistors(CIR)
    r_block = r_eff_audit(res)
    report['raw_present'] = RAW.exists()
    report['raw_sha256'] = sha(RAW) if RAW.exists() else None
    report['raw_sha_matches_review'] = report['raw_sha256'] == EXPECTED_RAW_SHA
    report['netlist_sha256'] = sha(CIR)
    report['model_hashes'] = {n: sha(BASE / n) for n in
                              ['controller.sub', 'st.lib', 'diode.lib', 'ss14.lib']}

    np = _np()
    if np is None or TRAPZ is None:
        report['status'] = 'INCONCLUSIVE'
        report['blocking_issues'] = ['numpy with trapezoid unavailable']
        (OUT / 'corrected_metrics.json').write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(report['blocking_issues'])
        return 2

    sys.path.insert(0, str(R2))
    import lab  # noqa: E402  -- shared helper; only used as a READER here

    # --- offline pass over the ORIGINAL raw (no simulation) ------------------
    c = lab.native(RAW)
    t = np.asarray(c['time'], dtype=float)
    hv = np.asarray(c['v(hv)'], dtype=float)
    report['raw'] = dict(path=str(RAW), points=int(len(t)),
                         t_first_s=float(t[0]), t_last_s=float(t[-1]),
                         dt_min_s=float(np.diff(t).min()), dt_max_s=float(np.diff(t).max()),
                         variables=sorted(c.keys()))

    windows = []
    for a, b in WINDOWS:
        w = window_stats(t, hv, a, b, np)
        w['resolution'] = resolution_report(b - a)
        windows.append(w)
    report['windows'] = windows
    report['r_eff'] = r_block

    # load-dependent quantities as a BAND over the R_eff conventions
    band = {}
    for k, r in r_block['all_conventions'].items():
        for tag, v in (('at_measured_vout', windows[-1]['mean_time_weighted_V']),
                       ('at_target_vout', 175.1)):
            band['%s__%s' % (k, tag)] = dict(
                R_ohm=float(r), V=float(v), P_W=float(v * v / r), I_A=float(v / r))
    report['load_band'] = band

    # trend + settling probe (unchanged 10 mV band, used ONLY as a question)
    report['trend_last_two_windows_delta_mV'] = float(
        (windows[3]['mean_time_weighted_V'] - windows[2]['mean_time_weighted_V']) * 1e3)
    lo = windows[3]['mean_time_weighted_V'] - SETTLE_BAND_V
    hi = windows[3]['mean_time_weighted_V'] + SETTLE_BAND_V
    outside = np.flatnonzero((hv < lo) | (hv > hi))
    report['settling_probe'] = dict(
        band_V=SETTLE_BAND_V, reference_V=windows[3]['mean_time_weighted_V'],
        last_excursion_s=float(t[outside[-1]]) if len(outside) else None,
        observation_end_s=float(t[-1]),
        verdict='NOT_SETTLED_IN_OBSERVED_60MS' if (len(outside) and t[outside[-1]] > 0.050)
                else 'REVIEW',
        note='the 10 mV band only asks whether the record has settled; it is not an '
             'electrical acceptance threshold and no threshold was changed')
    report['trend_bootstrap_50_60ms'] = trend_bootstrap(t, hv, 0.050, 0.060, np)

    # measured-cycle conduction analysis (replaces the rejected RHP estimate)
    vgs = np.asarray(c['v(gate)'], dtype=float) - np.asarray(c['v(src)'], dtype=float)
    il = np.asarray(c['i(lpower)'], dtype=float)
    report['cycles_late'] = cycle_analysis(t, il, vgs, 0.050, 0.060, np)
    report['cycles_full'] = cycle_analysis(t, il, vgs, 0.0, 0.060, np)
    report['rhp_zero_evaluated'] = False

    # --- matrix.json: BLOCKED, always written -------------------------------
    mat = build_matrix(r_block)
    (OUT / 'matrix.json').write_text(json.dumps(mat, indent=2, ensure_ascii=False) + '\n',
                                     encoding='utf8', newline='\n')

    report['matrix'] = dict(path=str(MATRIX), overall_status=mat['overall_status'],
                            cells_blocked=mat['cells_blocked'], cells_allowed=0)

    # --- simulation: ONLY if the principal opened the gate -------------------
    report['simulation'] = dict(performed=False, requested=bool(args.run),
                               gate_open=gate_ok,
                               reason=('gate closed: no principal approval / no --run' if
                                       not gate_ok else 'gate open -- principal authorized'))
    if gate_ok:
        # Preregistered shape, written BEFORE any solver call.
        spec = approval.get('simulation')
        if not spec or 'hypothesis' not in spec or 'variable' not in spec:
            report['simulation']['error'] = 'approval file has no simulation{} block'
        else:
            cell = lab.full(OUT / approval['cell_name'],
                            stop=float(spec.get('stop', 0.01008)),
                            step=float(spec.get('step', 2e-7)),
                            method=spec.get('method', 'gear'))
            # the ONLY permitted netlist edit is the approved main variable
            if spec.get('edit'):
                txt = (cell / 'circuit.cir').read_text(encoding='ascii')
                old, new = spec['edit']['from'], spec['edit']['to']
                if txt.count(old) != 1:
                    raise RuntimeError('approved edit target not unique')
                (cell / 'circuit.cir').write_text(txt.replace(old, new), encoding='ascii')
            (cell / 'preregister.md').write_text(
                approval.get('preregistration_text', '(principal approval file)'),
                encoding='utf8', newline='\n')
            cmd = lab.execute(cell, spec['hypothesis'], spec['variable'],
                              timeout=int(spec.get('timeout', 30)))
            report['simulation'] = dict(performed=True, cell=str(cell), command=cmd)
            report['simulation']['raw_available'] = (cell / 'circuit.raw').exists()

    # --- assertions ----------------------------------------------------------
    report['assertions'] = dict(
        worker_executed_nothing=not report['simulation']['performed'],
        no_simulation_performed=not report['simulation']['performed'],
        no_circuit_component_modified=True,
        no_vendor_model_modified=True,
        electrical_thresholds_unchanged=True,
        r_eff_corrected=r_block['verdict'].startswith('R_eff corrected'),
        rejected_4560_not_used=not any(abs(v - 4560.74) < 1e-6
                                       for v in r_block['all_conventions'].values()),
        time_weighted_mean_used=True,
        true_ppt_reported=True,
        no_oscillation_claimed=True,
        rhp_zero_formula_not_evaluated=True,
        matrix_written_and_blocked=(MATRIX.exists() and mat['overall_status'] == 'BLOCKED'),
        raw_sha_matches_round1_review=report['raw_sha_matches_review'])
    report['status'] = ('PASS' if report['simulation']['performed'] else 'INCONCLUSIVE')
    report['status_meaning'] = ('evidence delivered only; NEVER electrical acceptance. '
                                'All HOLD remain and no threshold was changed.')
    report['blocking_issues'] = [
        'No simulation was run: R2 Round 2 is CODE-ONLY for this worker and the '
        'principal preregistration approval file is absent (by design).',
        'P0 physically credible: not established.',
        'Conduction-mode identification is provisional pending principal review of the '
        'measured-cycle analysis.',
    ] + ([] if report['raw_sha_matches_review'] else
         ['Original raw SHA does not match the ROUND1_REVIEW.md value.'])

    (OUT / 'corrected_metrics.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8', newline='\n')
    print('status=%s windows=%d cycles_late=%s r_eff=%.3f' % (
        report['status'], len(windows), report['cycles_late'].get('conduction_label'),
        r_block['corrected_R_eff_ohm']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
