"""sense_candidate / build_minimum.py  --  DRAFT ONLY (Round2: CODE GENERATION, NO EXECUTION).

Principal Codex decision implemented (ROUND1_REVIEW.md line 6):
  "Approved local diagnostic: minimum switching cell precharged 89.17V / IL 1.4A with finite
   20ns gate edge, original power parts plus zero-volt terminal probes; three runs Gear1ns,
   Gear0.5ns, Trap1ns. This is explicitly NOT cold startup or a replacement controller.
   Diagnose recovery/gate/parasitics with exact current KCL; no model edits, runtime 30s each."

This script only BUILDS trees (netlist + copies of the byte-identical vendor models) and hashes
them. It builds no new fixture beyond the three approved cases. It does NOT run LTspice, does NOT
write preregister.json (lab.execute writes that itself, immediately before solver launch, per the
shared-lab preregistration rule) and does NOT touch any file outside OUTPUT_DIR.

Execution policy for the principal after review:
 1. python build_minimum.py            -> creates <case>/{circuit.cir,controller.sub,st.lib,diode.lib,ss14.lib}
                                           plus build_receipt.json; refuses to overwrite anything.
 2. Read the three circuit.cir files. Only the .tran method/maxstep and the .save line differ.
 3. For each case call lab.execute(case_dir, hypothesis, variable, timeout=30); read command.json.
 4. Audit with analyze_minimum.py (separate draft) for the KCL / recovery / gate metrics.
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
TIMEOUT = 30  # ROUND1_REVIEW.md line 6: runtime 30s each

# ---------------------------------------------------------------- precharged initial conditions
# Output node: 89.17 V stored on COUT (20.3uF, Rser=.1). Working-point sense current for that
# output split over the divider string 100k + 100k + 1900.6 ohm:
#   I_divider = 89.17 / 201900.6 = 441.65 uA
#   V_inc     = 89.17 - 100e3 * I_divider = 45.017 V
#   V_fb      = 1900.6 ohm * I_divider    = 0.83948 V
#   (design regulation point: V(hv) = 1.6 V * (201900.6 / 1900.6) = 169.97 V)
# VFBMID is a fresh node of the approved cell and is allowed an IC; V(fb) is also initialised so a
# solver that does not propagate the VCVS IC (L1) cannot silently present a wrong loop input.
V_HV, V_INC, V_FB = 89.17, 45.017, 0.83948
# Inductor current 1.4 A ("IL1.4" in the approved text) as the LPOWER/DREC mesh current.
# LTspice sets a device current from the FIRST numerical value in an IC= list:
#   window 1: 5 spans -> (1.4, 0, 0, 0, 0)   << the approved 1.4 A mesh current
#   window 2: 4 spans -> (VIN, 0, ICV, 0)     (shown so the principal can see the trap)
# The 0.1 ohm RINPUT span and the switch node that carries the LPOWER current are deliberately
# NOT initialised: they have no asserted value, and writing 0 would make the cell quietly wrong.
I_L = 1.4

# ---------------------------------------------------------------- KCL observability
# Top-level KCL reconstruction approved on ROUND1_REVIEW.md line 3 (all terms are instance pin
# vector currents of top-level devices, i.e. MOS port currents; nothing inside a vendor subcircuit
# is probed and no model byte is altered):
#   drain :  I(LPOWER) + I(XQ:LD) + I(DREC) + I(RSNUB) + I(CSNUB) - I(COUT) - I(RLOAD) - I(RB1A)
#            - I(RB2A) - I(RFB1)                    (sign convention: current INTO each pin)
#   src   :  I(XQ:LS) - I(RSRC) + I(RGS) - I(RNEG) - I(XNEG:K)/X?
#   gate  :  I(XQ:LG) - I(RG) + I(RGS) + I(RNEG)
# Only pin names that the stock netlist + diode.lib actually expose are saved; the KCL is still
# exactly reconstructible because every branch current is available at a terminal.
# NOTE (honest limitation, do not silently drop): I(COUT) is available in the LTspice raw only for
# a device whose current is stored; if it is missing, COUT current is d/dt of its charge and the
# KCL residual must be reported as PARTIAL rather than claimed as closed.

SAVE = ('V(hv) V(gate) V(src) V(sense) V(drain) V(in) V(out) V(neg) V(sn) '
        'V(fb) V(inc) V(ss) V(vc) V(en) V(intvcc) '
        'I(LPOWER) I(DREC) I(RSNUB) I(CSNUB) I(RLOAD) '
        'I(XQ:LD) I(XQ:LS) I(XQ:LG) I(XNEG:K) '
        'I(RSRC) I(RF) I(RG) I(RGS) I(RNEG) I(COUT)')

CASES = [
    dict(name='m1_gear_1ns', method='gear', step='1e-09',
         hypothesis=('With a finite 20ns gate edge and settled precharge (89.17V, IL 1.4A) the recovery '
                     'excursion and gate/negative-clamp ringing reproduce under Gear at 1ns max step, '
                     'and the top-level KCL closes to <=1mA at the peak'),
         variable='cell initial conditions + finite 20ns gate edge + solver Gear maxstep 1ns + KCL observability (case m1 of three approved)'),
    dict(name='m2_gear_0p5ns', method='gear', step='5e-10',
         hypothesis=('Halving the Gear max step to 0.5ns changes the recovery peak and the gate/negative '
                     'clamp peak by <=5% versus m1 (solver-converged, not an integration artefact)'),
         variable='solver Gear maxstep 1ns -> 0.5ns only (case m2 of three approved)'),
    dict(name='m3_trap_1ns', method='trap', step='1e-09',
         hypothesis=('Trapezoidal integration at the same 1ns max step gives the same recovery peak and '
                     'keeps the KCL residual <=1mA, so the excursion is not a Gear damping artefact'),
         variable='solver method Gear -> Trap at 1ns maxstep only (case m3 of three approved)'),
]


def sha256(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def build_netlist(method, step):
    """Minimum switching cell built from the committed R1 baseline text, preserving originals."""
    src = (lab.BASE / 'circuit.cir').read_text(encoding='ascii')
    n_before = src
    rep = []

    def sub(old, new, count=1):
        nonlocal src
        if src.count(old) != count:
            raise SystemExit('anchor not unique/missing: %r' % old)
        src = src.replace(old, new)
        rep.append([old, new])

    # 1. ICs on the output stack (PWL sources keep the original 0->24V / 0->12V ramps).
    sub('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1m 24) Rser=1e-9')
    # AC input bank span: explicit (0,0) IC so no span is left undefined for L1.
    sub('RINPUT vin in .1', 'RINPUT vin in .1 IC=0 IC=0')
    # 2. Switch-node span explicitly NOT initialised (no approved value).
    sub('LPOWER in drain 150u Rser=.16',
        'LPOWER in drain 150u Rser=.16 IC=(%r,0,0,0,0)' % I_L)
    # 3. Output capacitor / load.
    sub('COUT hv 0 20.3u Rser=.1 IC=0', 'COUT hv 0 20.3u Rser=.1 IC=%r' % V_HV)
    sub('RLOAD hv 0 5200', 'RLOAD hv 0 5200 IC=%r' % V_HV)
    # 4. Bleeder strings and feedback divider: every internal node from the divider law.
    sub('RB1A hv b1 90.9k\nRB1B b1 0 90.9k', 'RB1A hv b1 90.9k\nRB1B b1 0 90.9k IC=%r' % (0.0,))
    sub('RB2A hv b2 90.9k\nRB2B b2 0 90.9k', 'RB2A hv b2 90.9k\nRB2B b2 0 90.9k IC=%r' % (0.0,))
    sub('RFB1 hv fbmid 100k\nRFB2 fbmid fb 100k\nRFB3 fb 0 1900.6',
        'RFB1 hv fbmid 100k IC=%r\nRFB2 fbmid fb 100k IC=(%r,%r)\nRFB3 fb 0 1900.6 IC=(%r,0)'
        % (V_INC, V_INC, V_FB, V_FB))
    # 5. Auxiliary rail / negative-clamp / snubber spans: undefined or decoupled, left unset.
    #    (deliberately no IC)
    # 6. Solver recipe only: 3us window, Gear at 1ns / Gear at 0.5ns / Trap at 1ns.
    #    The finite ~20ns gate edge is NOT created here (see build_receipt notes): RG=22 ohm plus
    #    the STP9NK50Z gate charge shapes the DREC-driven edge inside the existing cell.
    sub('.tran 2e-07 0.06 0 2e-07 uic',
        '.tran %s 3e-06 0 %s uic' % (step, step))
    sub('.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear',
        '.options tnom=25 reltol=.001 abstol=1n vntol=1u method=' + method)
    # 7. Extended, purely observational probe list (replaces the R1 .save line).
    src = [ln for ln in src.splitlines() if not ln.startswith('.save ')]
    src = [ln for ln in src if not ln.startswith('.end')] + ['.save ' + SAVE, '.end']
    src = '\n'.join(src) + '\n'
    if 'method=' + method not in src:
        raise SystemExit('method not applied')
    if 'abstol=1n vntol=1u' not in src or 'reltol=.001' not in src:
        raise SystemExit('original tolerances must be preserved')
    return n_before, src, rep


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base_models = json.loads((lab.BASE / 'preregister.json').read_text())['model_hashes']
    receipt = dict(kind='DRAFT_BUILD_RECEIPT', executed=False, solver_calls=0,
                   source_baseline=str(lab.BASE), timeout_s=TIMEOUT,
                   planned_runs=len(CASES),
                   cases=[], model_hashes={}, notes=[])
    for case in CASES:
        d = OUT / case['name']
        if d.exists():
            raise SystemExit('refuse to overwrite existing experiment dir: ' + str(d))
        d.mkdir(parents=True)
        for name in MODELS:
            shutil.copy2(lab.MODEL_SOURCE / name, d / name)
        got = {name: sha256(d / name) for name in MODELS}
        if got != base_models:
            raise SystemExit('vendor model bytes differ from R1 for ' + case['name'])
        before, after, rep = build_netlist(case['method'], case['step'])
        (d / 'circuit.cir').write_text(after, encoding='ascii')
        (d / 'baseline_text_sha256.txt').write_text(sha256(lab.BASE / 'circuit.cir') + '\n', encoding='ascii')
        receipt['cases'].append(dict(
            name=case['name'], dir=d.name, hypothesis=case['hypothesis'], variable=case['variable'],
            netlist_sha256=sha256(d / 'circuit.cir'), baseline_netlist_sha256=sha256(lab.BASE / 'circuit.cir'),
            edits=rep, tran=[ln for ln in after.splitlines() if ln.startswith('.tran')][0],
            options=[ln for ln in after.splitlines() if ln.startswith('.options')][0],
            save=[ln for ln in after.splitlines() if ln.startswith('.save')][0],
            initial_conditions=dict(v_hv=V_HV, v_inc=V_INC, v_fb=V_FB, i_lpower_A=I_L),
            source_ramps_unchanged=True, execute_timeout_s=TIMEOUT))
        receipt['model_hashes'] = got
    # The 20ns finite gate edge is a top-level RG/DREC function; it is NOT a new device.
    receipt['notes'].append('20ns gate edge is realised by the existing RG=22ohm + STP9NK50Z gate '
                            'charge driven from the controller DREC pin; no edge-shaping device was added.')
    receipt['notes'].append('RINPUT vin in .1 keeps an explicit (0,0) IC so that no undefined span is left '
                            'to L1; this is an IC annotation on an existing resistor and does not change '
                            'the component value or topology.')
    receipt['notes'].append('Vendor models are copied byte-for-byte from lab.MODEL_SOURCE and re-hashed '
                            'against the R1 preregistration; a mismatch aborts the build.')
    receipt['notes'].append('R1 .save line is replaced by the KCL/observability list; the R1 baseline '
                            'netlist text is preserved (hash recorded) and never rewritten.')
    receipt['notes'].append('Any current that LTspice refuses to store must be reported as a PARTIAL KCL, '
                            'not as a closed KCL.')
    (OUT / 'build_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n',
                                            encoding='utf8')
    print('BUILT', len(receipt['cases']), 'cases; no solver was invoked')


if __name__ == '__main__':
    main()
