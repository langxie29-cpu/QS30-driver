"""sense_candidate / build_filter.py  --  DRAFT ONLY (Round2: CODE GENERATION, NO EXECUTION).

Principal Codex decision implemented (ROUND1_REVIEW.md line 7):
  "Approved SENSE candidate: keep RSRC 62mohm, RG 22ohm and all power parts; change only the RC
   filter network from 10ohm/1nF to 22ohm/4.7nF as ONE filter time-constant design choice.
   ... Tau 10ns -> 103.4ns; DC 65uA bias creates 1.43mV offset instead of 0.65mV, tending to lower
   true threshold. At 26.4V/Lmin 135uH, added ramp lag 18.27mA versus 12.58mA earlier threshold
   compensation, not a reduction in shunt sensitivity. Blanking 100ns still limits turn-on
   response. Test pin abs<.3V, true inductor current, turnoff timing and normal peaks; no clamp
   that hides a sustained short. Initial full 60ms run only; if it fails no automatic retuning."

Exactly ONE candidate run, exactly ONE edited variable (RF/CF only). Everything else is the
unmodified R1 baseline. No clamping/short-hiding device is added. No execution happens here:
this script only writes the case tree + receipt; lab.execute() (which performs the mandatory
preregistration of netlist/model/solver hashes) remains a separate, principal-approved call.

Wideband observability is added in the .save line only (purely observational; the R1 .save line is
recorded before replacement, and no vendor model byte is touched).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

R2 = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
OUT = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_02/sense_candidate')
sys.path.insert(0, str(R2))
import lab  # noqa: E402  (only lab.sha / lab.MODEL_SOURCE / lab.BASE are used; nothing is executed)

MODELS = ['controller.sub', 'st.lib', 'diode.lib', 'ss14.lib']
RUN_NAME = 'f1_full_60ms'
STOP, STEP, METHOD, TIMEOUT = 0.060, 2e-7, 'gear', 180   # baseline recipe; risk noted in receipt

# The ONE approved filter variable: 10 ohm / 1nF  ->  22 ohm / 4.7nF.
EDIT_RF = ('RF src sense 10', 'RF src sense 22')
EDIT_CF = ('CF sense 0 1n', 'CF sense 0 4.7n')

# Purely observational probe additions relative to the R1 baseline .save line.
#   V(sense) / V(src) / I(RSRC) / I(RF) : pin integrity, true shunt voltage/current
#   I(LPOWER) / V(drain)                : true inductor current and switch-node timing
#   I(XQ:LD) I(XQ:LS) I(XQ:LG)           : MOS port currents (top-level KCL reconstruction)
#   V(out) / V(gate) / V(vc) / V(ss)     : turn-off timing and controller state
SAVE = ('V(hv) V(gate) V(src) V(sense) V(vc) V(ss) V(drain) V(out) V(in) V(en) V(intvcc) '
        'I(LPOWER) I(DREC) I(RSRC) I(RF) I(RG) I(RGS) I(RNEG) I(COUT) I(CSNUB) '
        'I(XQ:LD) I(XQ:LS) I(XQ:LG)')

# Fixed acceptance identifiers (never recomputed or relaxed by this script).
LIMITS = dict(mean_V=[164.9, 175.1], ripple_Vpp=1, normal_peak_V=180, startup_s=1, recovery_s=0.1,
              fault_peak_V=195, sense_abs_V=0.3)

# Design arithmetic, recorded for audit (not a measurement).
TAU_OLD_NS = 1e3 * 10 * 1e-9           # 10 ohm * 1nF
TAU_NEW_NS = 1e3 * 22 * 4.7e-9         # 22 ohm * 4.7nF
I_BIAS_A = 65e-6                       # controller sense-input bias from the decision text
OFFSET_OLD_MV = 1e3 * I_BIAS_A * 10
OFFSET_NEW_MV = 1e3 * I_BIAS_A * 22
# Added ramp lag quoted by the principal decision at 26.4 V / Lmin 135uH: 12.58mA (tau 10ns) ->
# 18.27mA (tau 103.4ns). These are COPIED, quoted design figures, NOT recomputed here: a
# self-invented Vout would silently disagree with the decision. The implied constant di/dt is
# back-checked below so the numbers are at least mutually consistent.
LAG_OLD_MA = 12.58
LAG_NEW_MA = 18.27
VIN_CORNER, L_MIN = 26.4, 135e-6
DI_DT_IMPLIED = -LAG_OLD_MA * 1e-3 / TAU_OLD_NS * 1e9   # A/s implied by the quoted 12.58mA
LAG_NEW_MA_CHECK = 1e3 * abs(DI_DT_IMPLIED) * TAU_NEW_NS * 1e-9
LAG_CONSISTENT = abs(LAG_NEW_MA_CHECK - LAG_NEW_MA) <= 0.05


def sha256(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = OUT / RUN_NAME
    if d.exists():
        raise SystemExit('refuse to overwrite existing experiment dir: ' + str(d))
    d.mkdir(parents=True)
    for name in MODELS:
        shutil.copy2(lab.MODEL_SOURCE / name, d / name)
    base_models = json.loads((lab.BASE / 'preregister.json').read_text())['model_hashes']
    got = {name: sha256(d / name) for name in MODELS}
    if got != base_models:
        raise SystemExit('vendor model bytes differ from R1')

    orig = (lab.BASE / 'circuit.cir').read_text(encoding='ascii')
    src = orig
    edits = []
    for old, new in (EDIT_RF, EDIT_CF):
        if src.count(old) != 1:
            raise SystemExit('anchor not unique/missing: %r' % old)
        src = src.replace(old, new)
        edits.append([old, new])
    # full 60ms endpoint with the unchanged baseline max step / method
    src = src.replace('.tran 2e-07 0.06 0 2e-07 uic', '.tran 2e-07 0.060 0 2e-07 uic')
    lines = [ln for ln in src.splitlines() if not ln.startswith('.save ')]
    orig_save = [ln for ln in orig.splitlines() if ln.startswith('.save ')][0]
    lines = [ln for ln in lines if not ln.startswith('.end')] + ['.save ' + SAVE, '.end']
    src = '\n'.join(lines) + '\n'

    # Guard rails: nothing except the filter may differ in the component section.
    for must_keep in ('RSRC src 0 .062', 'RG out gate 22', 'LPOWER in drain 150u Rser=.16',
                      'COUT hv 0 20.3u Rser=.1', 'RLOAD hv 0 5200', 'RINPUT vin in .1'):
        if must_keep not in src:
            raise SystemExit('power part altered: ' + must_keep)
    for banned in ('DCLAMP', 'DZENER', 'BTURN', 'BV', 'GCLAMP'):
        if banned in src.split('.save')[0]:
            raise SystemExit('clamp/short-hiding element present: ' + banned)
    if 'reltol=.001' not in src or 'abstol=1n vntol=1u' not in src:
        raise SystemExit('original tolerances changed')

    (d / 'circuit.cir').write_text(src, encoding='ascii')
    (d / 'baseline_text_sha256.txt').write_text(
        sha256(lab.BASE / 'circuit.cir') + '\n' + orig_save + '\n', encoding='ascii')

    receipt = dict(
        kind='DRAFT_BUILD_RECEIPT', executed=False, solver_calls=0, run_name=RUN_NAME,
        decision_ref='ROUND1_REVIEW.md line 7',
        hypothesis=('Replacing only the sense RC filter 10ohm/1nF -> 22ohm/4.7nF (tau 10ns -> 103.4ns) '
                    'keeps |V(sense)| < 0.3V across the full 60ms cold start without hiding a sustained '
                    'short, while true inductor-current turn-off timing and normal output peaks do not '
                    'degrade beyond the fixed limits'),
        variable='sense filter only: RF 10ohm -> 22ohm and CF 1nF -> 4.7nF (ONE design choice, two '
                 'components of the same filter). No other component, no tolerance, no model change.',
        edits=edits,
        unchanged=['RSRC .062', 'RG 22', 'LPOWER 150u Rser .16', 'COUT 20.3u Rser .1', 'RLOAD 5200',
                   'RINPUT .1', 'all vendor model bytes'],
        tran=[ln for ln in src.splitlines() if ln.startswith('.tran')][0],
        options=[ln for ln in src.splitlines() if ln.startswith('.options')][0],
        save_original=orig_save,
        save_new=SAVE,
        baseline_netlist_sha256=sha256(lab.BASE / 'circuit.cir'),
        netlist_sha256=sha256(d / 'circuit.cir'),
        model_hashes=got,
        solver='LTspice 24.0.12.0 Windows Normal (via lab.execute)',
        fixed_limits=LIMITS,
        timeout_s=TIMEOUT,
        design_arithmetic=dict(tau_old_ns=TAU_OLD_NS, tau_new_ns=TAU_NEW_NS,
                               bias_offset_old_mV=OFFSET_OLD_MV, bias_offset_new_mV=OFFSET_NEW_MV,
                               lag_old_mA_quoted=LAG_OLD_MA, lag_new_mA_quoted=LAG_NEW_MA,
                               lag_new_mA_backcheck=LAG_NEW_MA_CHECK, lag_quoted_consistent=LAG_CONSISTENT,
                               di_dt_implied_by_quoted_lag_A_per_s=DI_DT_IMPLIED,
                               vin_corner=VIN_CORNER, l_min_H=L_MIN, blanking_ns=100),
        assertions_for_principal=[
            'abort if I(LPOWER) is absent from the raw -> true-current test not evaluable (INCONCLUSIVE)',
            'pin integrity: max|V(sense)| < 0.3 V AND max|V(src)-V(sense)| <= RF_max*|I(RSRC)| (Ohm-level check)',
            'shunt sensitivity retained: I(RSRC) tracks I(LPOWER)-I(shunt-divider) to <=1 mA in the switching band',
            'no clamp: netlist contains no added clamp/short-hiding device (checked at build time)',
            'turn-off timing: compare delay from I(LPOWER) zero crossing to V(gate) < 1 V against the '
            'unchanged-baseline R1 core% record',
            'normal peaks: max V(hv) <= 180 V; settled mean in [164.9,175.1] V; ripple <= 1 Vpp',
            'risk: baseline 60ms at 2e-7 maxstep may exceed the 300 s worker budget -> principal runs it '
            'outside the worker runtime; no automatic retuning on failure',
        ],
        notes=['No execution performed by this draft; lab.execute performs the mandatory preregistration '
               'immediately before solver launch.',
               'Runtime risk: measure elapsed_s in command.json; a timeout leaves the attempt consumed and '
               'may NOT be retried unless preregistered.'],
    )
    (OUT / 'filter_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n',
                                             encoding='utf8')
    if not LAG_CONSISTENT:
        print('WARNING: quoted ramp-lag figures are not mutually consistent with tau ratio '
              '(backcheck %.3f mA); principal must re-derive before use' % LAG_NEW_MA_CHECK)
    print('BUILT', RUN_NAME, 'no solver was invoked')


if __name__ == '__main__':
    main()
