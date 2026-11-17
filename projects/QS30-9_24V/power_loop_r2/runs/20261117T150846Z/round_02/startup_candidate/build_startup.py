"""startup_candidate — DRAFT ONLY (Round2, CODE GENERATION / READ ONLY).

EXECUTION OF THIS FILE IS FORBIDDEN IN THIS SESSION. It exists so the principal Codex can
inspect it and, only if approved, copy it to the principal execution area and run it there.

Scope, taken verbatim from ROUND1_REVIEW.md line 8 (the ONLY authorized work):
  "Three worst-scenario diagnostic runs: 26.4V, C24.36u, L135u, Rsource .1, gate inhibited;
   uncontrolled 1us; same plus 33ohm; same no 33ohm with 8.49ms fastest datasheet-derived
   47nF-10% slew. Each changes one variable relative to uncontrolled reference; no ideal slew
   qualification of real eFuse. Do not equate a source ramp to a validated device."

Therefore: exactly THREE cases. No extra fixtures, no thermal scan, no compensation scan,
no tuning, no retries. Every vendor model is copied byte-identical by lab.full() and is
verified byte-identical by lab.execute(); nothing here edits a model, a component value of
the base cell, or any acceptance threshold (lab.py's own `limits` dict is used unmodified).

PRINCIPAL MUST CHECK BEFORE RUNNING (each item is a known open question, not an oversight):
  Q1. lab.full() freezes STOP to its default 10.08 ms unless overridden. The uncontrolled
      reference can only reach the HV fault ceiling after the rectifier conducts, which
      requires the controller to switch. With the gate inhibited (Q3) that cannot happen.
      So case A is best interpreted as the passive charging arrival, and the
      `fault_peak_V = 195` assertion is reported as NOT EVALUABLE rather than as a result.
  Q2. `.tran <step> <stop> 0 <step> uic` is written with the same value for maxstep and
      Tstart-0 alignment; lab.py's own `lab.full(step=...)` argument is time_step here.
      5e-8 s is used for all three cases uniformly (solver variable held constant so that
      only the ONE circuit variable per case differs).
  Q3. The review says "gate inhibited" for every case. There is no vendor SHDN/EN pin on
      LT3757A that lab.py drives (SHDN pin 9 is the unconnected 10th positional node and is
      NOT held in that model), so the inhibition used here is a NETLIST-level statement:
      REN1/REN2 divider removed and VEN en 0 0 (identical prerequisite to the approved
      round_01 passive_bounds "SHDN hold"). If the principal requires a different
      inhibition mechanism it MUST be preregistered first — this script does not add one.
  Q4. Case C's 8.49 ms is a datasheet-derived SOURCE RAMP, not a device behaviour. It is
      used only to bound the passive stress; it does not qualify the TPS26601.

Case table (one variable per case relative to A; A itself is the uncontrolled reference):
  A `startup_A_uncontrolled_ref`  : base cell + gate inhibit + 26.4 V / C=24.36u / L=135u /
                                    RINPUT=.1 / 1 us source ramp   (reference, 0 extra variables)
  B `startup_B_precharge_33ohm`   : A + 33 ohm 5% series precharge RESISTOR only
  C `startup_C_slow_slew_8p49ms`  : A + source ramp 1 us -> 8.49 ms only (no 33 ohm)

Case B edit is a genuine .cir text edit applied AFTER lab.full() and BEFORE lab.execute().
lab.full() does not copy `.save`, so the added part is observed through its endpoint
V('pre') (pin-to-pin between in and drain), which is exactly what the precharge node needs.
Nothing else about the netlist changes.

Provenance/hash bookkeeping is derived at run time by lab.py; nothing is hardcoded from a
previous session, so a stale baseline hash can never be reused silently.
"""
import sys, json, re
from pathlib import Path

R2 = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
OUT = Path(r'D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2/runs/20261117T150846Z/round_02/startup_candidate')
RUNS = OUT / 'runs'
sys.path.insert(0, str(R2))

# --- hard guards: nothing may run by accident or with the wrong contract ------------------
if __name__ != '__main__':
    raise SystemExit('build_startup.py is a draft; do not import it.')
if not (R2 / 'lab.py').is_file():
    raise SystemExit('shared lab.py not found; refusing to invent a solver path')
import lab  # noqa: E402

STOP, STEP, METHOD, TIMEOUT = 0.01008, 5e-8, 'gear', 30
HOLD_AUX = ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1us 26.4)')
GATE_INHIBIT = ('REN1 in en 200k\nREN2 en 0 12.8k', 'VEN en 0 0')
CORNER = [
    ('VINPUT vin 0 PWL(0 0 1m 24)', 'VINPUT vin 0 PWL(0 0 1us 26.4)'),   # replaces VIN line only
    ('COUT hv 0 20.3u', 'COUT hv 0 24.36u'),
    ('LPOWER in drain 150u', 'LPOWER in drain 135u'),
]  # RINPUT .1 is already the nominal; stated explicitly so the corner is fully spelled out.
PRECHARGE = ('LPOWER in drain 150u Rser=.16', 'LPOWER in drain 150u Rser=.16\nRPRE in drain 33')
SLOW_SLEW = ('VINPUT vin 0 PWL(0 0 1us 26.4)', 'VINPUT vin 0 PWL(0 0 8.49m 26.4)')

CASES = [
    dict(name='startup_A_uncontrolled_ref',
         hypothesis=('Corner worst-case passive cell (26.4V, COUT 24.36u, L 135u, RINPUT .1, gate '
                     'inhibited) with the 1us uncontrolled source ramp: reference for the bounded '
                     'startup alternatives. Establishes the uncontrolled passive peak, not a pass.'),
         variable=('gate inhibit only (REN1/REN2 -> VEN en 0 0) plus the preregistered corner values '
                   '26.4V/24.36u/135u; uncontrolled 1us source ramp = reference'),
         edits=[GATE_INHIBIT, HOLD_AUX] + [CORNER[1], CORNER[2], ('RINPUT vin in .1', 'RINPUT vin in .1')],
         extra=[]),
    dict(name='startup_B_precharge_33ohm',
         hypothesis=('A 33 ohm 5% independent series precharge resistor applied downstream of input '
                     'bulk (here: in series with the drain-side power path, i.e. after COUT/input '
                     'bulk) bounds the passive charging current of the same uncontrolled ramp and '
                     'therefore the arrival peak, at the cost of a DC drop not modelled by RLOAD.'),
         variable='RPRE = 33 ohm inserted in the power path only; every other element identical to case A',
         edits=[GATE_INHIBIT, HOLD_AUX, CORNER[1], CORNER[2], PRECHARGE],
         extra=[]),
    dict(name='startup_C_slow_slew_8p49ms',
         hypothesis=('The fastest datasheet-derived 47nF-10% slew (8.49 ms) is used as a SOURCE ramp '
                     'on the otherwise identical uncontrolled cell. This is a bound on passive '
                     'stress, never evidence about TPS26601 device behaviour or SOA.'),
         variable='source ramp 1 us -> 8.49 ms only (no 33 ohm, all parts identical to case A)',
         edits=[GATE_INHIBIT, HOLD_AUX, CORNER[1], CORNER[2], SLOW_SLEW],
         extra=[]),
]


def apply(path, edits):
    """Apply literal, unique replacements. Refuse on any anchor not found exactly once."""
    cir = (path / 'circuit.cir').read_text(encoding='ascii')
    for old, new in edits:
        if old == new:            # explicit no-op used to spell out the nominal value
            assert cir.count(old) == 1, f'nominal anchor missing: {old!r}'
            continue
        if cir.count(old) != 1:
            raise SystemExit(f'anchor not unique/missing in {path.name}: {old!r}')
        cir = cir.replace(old, new)
    (path / 'circuit.cir').write_text(cir, encoding='ascii')
    return cir


def kcl_check(path):
    """Purely additive post-hoc check on whatever raw exists. No new simulation, no probe added.

    Only ports that lab.py's baseline .save line already exposes can be used here; if the
    names that round_01 extracted (I(XNEG:ddio)/I(XNEG:dgr)) are absent the check reports
    NOT_EVALUABLE with the variable names that were present instead of silently skipping.
    """
    try:
        c = lab.native(path / 'circuit.raw')
    except Exception as exc:                       # noqa: BLE001 - record, never hide
        return dict(status='RAW_UNREADABLE', error=f'{type(exc).__name__}: {exc}')
    need = {'v(hv)', 'i(lpower)', 'i(drec)', 'i(rsnub)', 'i(csnub)'}
    have = set(c)
    if not need <= have:
        return dict(status='NOT_EVALUABLE', missing=sorted(need - have), available=sorted(have))
    t = c['time']
    i_lp, i_drec = c['i(lpower)'], c['i(drec)']
    i_sn = c['i(rsnub)'] + c['i(csnub)']
    i_load = c['v(hv)'] / 5200.0                   # RLOAD only; bleeders/feedback not summed
    resid = i_lp - i_drec - i_sn - i_load
    # Worst residual is only meaningful at points the solver actually resolved; report both
    # the full-trace and the post-arrival (coarse) figures rather than a single number.
    return dict(status='EVALUATED',
                residual_max_A=float(abs(resid).max()),
                residual_max_after_1ms_A=float(abs(resid[t >= 1e-3]).max()) if (t >= 1e-3).any() else None,
                note='residual includes bleeder+feedback+HPF+controller-current not restored here')


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    idx_path = RUNS / 'startup_raw_index.json'
    done = json.loads(idx_path.read_text(encoding='utf8')) if idx_path.exists() else {}
    summary = []
    for d in CASES:
        p = RUNS / d['name']
        if (p / 'preregister.json').exists() or (p / 'circuit.raw').exists():
            # Never overwrite a previous wave. Resume semantics only.
            summary.append(dict(name=d['name'], status='ALREADY_EXISTS_SKIPPED'))
            print(d['name'], 'SKIP (exists)', flush=True)
            continue
        lab.full(p, stop=STOP, step=STEP, method=METHOD)          # copies models byte-identical
        cir = apply(p, d['edits'])
        assert 'method=' + METHOD in cir
        assert f'.tran {STEP:g} {STOP:g} 0 {STEP:g} uic' in cir
        assert 'REN1' not in cir and 'VEN en 0 0' in cir, 'gate inhibit not applied'
        if d['name'].endswith('_precharge_33ohm'):
            assert 'RPRE in drain 33' in cir and '8.49m' not in cir
        if d['name'].endswith('_slow_slew_8p49ms'):
            assert 'RPRE' not in cir and '8.49m' in cir
        if d['name'].endswith('_uncontrolled_ref'):
            assert 'RPRE' not in cir and '1us' in cir and '8.49m' not in cir
        cmd = lab.execute(p, d['hypothesis'], d['variable'], timeout=TIMEOUT)
        prereg = json.loads((p / 'preregister.json').read_text(encoding='utf8'))
        row = dict(name=d['name'], variable=d['variable'], hypothesis=d['hypothesis'],
                   edits=[[a, b] for a, b in d['edits']], command=cmd,
                   netlist_sha256=prereg['netlist_sha256'], tran=prereg['tran'],
                   options=prereg['options'], model_hashes=prereg['model_hashes'],
                   solver=prereg['solver'], max_runtime_s=prereg['max_runtime_s'],
                   acceptance_limits_unchanged=prereg['acceptance'],
                   kcl=kcl_check(p) if (p / 'circuit.raw').exists() else dict(status='NO_RAW'))
        log = p / 'circuit.log'
        tail = log.read_text(encoding='latin-1').splitlines()[-4:] if log.exists() else ['NO LOG']
        row['log_tail'] = tail
        (p / 'derived.json').write_text(json.dumps(row, indent=2) + '\n', encoding='utf8')
        done[d['name']] = {k: row[k] for k in ('variable', 'command', 'netlist_sha256',
                                               'model_hashes', 'tran', 'kcl', 'log_tail')}
        idx_path.write_text(json.dumps(done, indent=2) + '\n', encoding='utf8')
        summary.append(row)
        print(d['name'], cmd['status'], cmd['rc'], round(cmd['elapsed_s'], 1), flush=True)

    # Post-hoc measurement is deliberately in a SEPARATE, principal-reviewed step
    # (measure_startup.py). This file only creates and executes; measuring here would let a
    # reading of the data influence what was run, which the preregistration contract forbids.
    (OUT / 'startup_runs_summary_draft.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf8')
    print('DONE', len(summary))


if __name__ == '__main__':
    main()
