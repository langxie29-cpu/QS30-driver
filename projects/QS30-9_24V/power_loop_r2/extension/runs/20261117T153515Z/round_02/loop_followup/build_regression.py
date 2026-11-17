"""loop_followup -- FUNCTION-ONLY netlist mutator (QS30-9 extension, Round 4).

No __main__, no filesystem writes, no simulator/shell/network/model call. The
principal inspects this file, then (via lab.py) loads it and calls mutate().

Base cell = the completed filter22R_4p7n_60ms circuit, whose text is passed in by
the caller as ``s`` (read by the principal from
evidence/principal/filter22R_4p7n_60ms/circuit.cir, sha256 796b3466...cca4e,
per that cell's preregister.json).  Each call asserts the exact anchors below
appear EXACTLY ONCE and asserts the untouched anchors are still present exactly
once afterwards; anything else aborts instead of emitting a guessed netlist.

Pre-registered mutation set (3 cases, no extras):
  'vin21p6'    VINPUT plateau 24 -> 21.6, stop 0.2 s
  'vin26p4'    VINPUT plateau 24 -> 26.4, stop 0.2 s
  'load_step'  RLOAD hv 0 5200 -> BLOAD hv 0 I=V(hv)/(if(time<80m,10400,
               if(time<180m,5200,10400))), stop 0.3 s
  'overload'   RLOAD hv 0 5200 -> BLOAD hv 0 I=V(hv)/(if(time<80m,5200,1000)),
               stop 0.16 s

DO NOT TOUCH, asserted below: RF 22 / CF 4.7n (22 ohm, 4.7 nF pin filter), RG 22,
RSRC .062 V/A (62 mohm), RCOMP 22k / CCOMP 6.8n / CHF 100p (compensation), the
include lines, the load resistor removal, any .model, any vendor .sub/.lib byte,
the option tolerances, all electrical thresholds.  Raw output
ripple is checked over FIXED final windows only (see FINAL_WINDOWS); no acceptance
value is introduced, altered or re-derived by this script.

Scope limits recorded in the returned metadata: the load is an equivalent
RESISTIVE load (ideal current sink defined by V(hv)/R); it is NOT nine glow tubes
and NOT any measured lamp; the overload case is a SCREEN of current-limit
behaviour only -- it is not normal-regulation qualification and not 195 V OVP
qualification.
"""
import re

VIN_PLATEAU_RE = r'^(VINPUT\s+vin\s+0\s+PWL\(0\s+0\s+1m\s+)24(\))\s*$'
RLOAD_RE = r'^(RLOAD\s+hv\s+0\s+)5200(\s*)$'
TRAN_RE = r'^(\.tran\s+\S+\s+)\S+(\s+0\s+\S+\s+uic\s*)$'

UNTOUCHED = (
    (r'^RF\s+src\s+sense\s+22\s*$', 'RF 22 (pin filter series R)'),
    (r'^CF\s+sense\s+0\s+4\.7n\s*$', 'CF 4.7n (pin filter C)'),
    (r'^RG\s+out\s+gate\s+22\s*$', 'RG 22 (gate resistor)'),
    (r'^RSRC\s+src\s+0\s+\.062\s*$', 'RSRC .062 (62 mohm shunt)'),
    (r'^RCOMP\s+vc\s+comp\s+22k\s*$', 'RCOMP 22k'),
    (r'^CCOMP\s+comp\s+0\s+6\.8n\s+IC=0\s*$', 'CCOMP 6.8n'),
    (r'^CHF\s+vc\s+0\s+100p\s+IC=0\s*$', 'CHF 100p'),
    (r'^\.include\s+controller\.sub\s*$', 'include controller.sub'),
    (r'^\.include\s+st\.lib\s*$', 'include st.lib'),
    (r'^\.include\s+diode\.lib\s*$', 'include diode.lib'),
    (r'^\.include\s+ss14\.lib\s*$', 'include ss14.lib'),
)
FORBIDDEN = (
    (r'^\.model\b', 'no new .model card may appear'),
    (r'^\.lib\b', 'no new .lib card may appear'),
    (r'^RF\s+src\s+sense\s+(?!22\s*$)', 'RF value changed'),
    (r'^CF\s+sense\s+0\s+(?!4\.7n\s*$)', 'CF value changed'),
)
STOPS = {'vin21p6': '0.2', 'vin26p4': '0.2', 'load_step': '0.3', 'overload': '0.16'}
FINAL_WINDOWS = {'vin21p6': [0.15, 0.2], 'vin26p4': [0.15, 0.2],
                 'load_step': [0.26, 0.3], 'overload': [0.14, 0.16]}
PREREGISTERED = ('vin21p6', 'vin26p4', 'load_step', 'overload')
LOAD_STEP_DRIVE = 'I=V(hv)/(if(time<80m,10400,if(time<180m,5200,10400)))'
OVERLOAD_DRIVE = 'I=V(hv)/(if(time<80m,5200,1000))'


def count(s, pattern):
    return len(re.findall(pattern, s, flags=re.M))


def sub_once(s, pattern, replacement, label):
    """Replace exactly one whole-line match; abort on 0 or >1 match."""
    hits = re.findall(pattern, s, flags=re.M)
    if len(hits) != 1:
        raise AssertionError('anchor %r not unique: %d exact matches' % (label, len(hits)))
    new, n = re.subn(pattern, replacement, s, count=1, flags=re.M)
    if n != 1:
        raise AssertionError('anchor %r replacement failed' % label)
    return new


def remove_lines(s, pattern):
    """Delete exactly one whole-line match (including its newline); abort otherwise."""
    hits = re.findall(pattern, s, flags=re.M)
    if len(hits) != 1:
        raise AssertionError('anchor %r not unique: %d exact matches' % (pattern, len(hits)))
    new, n = re.subn(pattern + r'\n', '', s, count=1, flags=re.M)
    if n != 1:
        raise AssertionError('anchor %r removal failed' % pattern)
    return new


def mutate(s, kind):
    """Return the mutated netlist string. Pure: no I/O, no global state."""
    if not isinstance(s, str):
        raise TypeError('s must be the netlist text')
    if kind not in STOPS:
        raise ValueError('kind must be one of %r' % (STOPS,))
    if '\r' in s:
        raise AssertionError('CRLF netlist rejected: normalise before mutation')
    if not s.endswith('\n'):
        raise AssertionError('netlist must end with a newline')
    for pattern, label in UNTOUCHED:
        if count(s, pattern) != 1:
            raise AssertionError('base cell missing/unstable anchor: %s' % label)
    for pattern, label in FORBIDDEN:
        if count(s, pattern) != 0:
            raise AssertionError('base cell already violates: %s' % label)
    if count(s, TRAN_RE) != 1:
        raise AssertionError('.tran line not unique')
    out = dict(kind=kind)

    if kind in ('vin21p6', 'vin26p4'):
        value = '21.6' if kind == 'vin21p6' else '26.4'
        s = sub_once(s, VIN_PLATEAU_RE, r'\g<1>%s\g<2>' % value, 'VINPUT plateau 24')
        if count(s, RLOAD_RE) != 1:
            raise AssertionError('RLOAD hv 0 5200 not unique: load must stay as-is')
        out.update(changed='VINPUT plateau 24 -> %s only' % value, rload='unchanged 5200')
    elif kind in ('load_step', 'overload'):
        drive = LOAD_STEP_DRIVE if kind == 'load_step' else OVERLOAD_DRIVE
        line = 'BLOAD hv 0 %s\n' % drive
        if re.search(r'^BLOAD\b', s, flags=re.M):
            raise AssertionError('BLOAD already present; refusing to duplicate')
        s = remove_lines(s, RLOAD_RE)
        if count(s, RLOAD_RE) != 0:
            raise AssertionError('RLOAD hv 0 5200 still present after removal')
        if count(s, r'^RLOAD\b') != 0:
            raise AssertionError('a different RLOAD card remains; only the 5200 ohm one is registered')
        if count(s, r'^\.temp\s+25\s*$') != 1:
            raise AssertionError('.temp 25 anchor not unique; cannot place BLOAD')
        s = s.replace('.temp 25\n', line + '.temp 25\n', 1)
        out.update(changed='RLOAD hv 0 5200 removed -> %s' % line.strip(),
                   rload='removed (replaced by BLOAD)')
    else:  # pragma: no cover - unreachable, guarded by STOPS above
        raise ValueError(kind)

    s = sub_once(s, TRAN_RE, r'\g<1>' + STOPS[kind] + r'\g<2>', '.tran stop time')
    for pattern, label in UNTOUCHED:
        if count(s, pattern) != 1:
            raise AssertionError('mutation damaged anchor: %s' % label)
    for pattern, label in FORBIDDEN:
        if count(s, pattern) != 0:
            raise AssertionError('mutation introduced: %s' % label)
    if '.tran' not in s or STOPS[kind] not in re.search(TRAN_RE, s, flags=re.M).group(0):
        raise AssertionError('.tran stop not written')
    if count(s, r'(?i)^\.options\s.*reltol=\.001\s+abstol=1n\s+vntol=1u.*$') != 1:
        raise AssertionError('solver tolerances were altered')
    if count(s, r'^\.tran\s+\S+\s+\S+\s+0\s+\S+\s+uic\s*$') != 1:
        raise AssertionError('.tran form changed')

    out.update(
        stop_s=float(STOPS[kind]),
        final_window_s=FINAL_WINDOWS[kind],
        raw_ripple_rule='Vpp of V(hv) over final_window_s only, raw saved points, no resampling',
        recovery_screen=0.1, normal_band_V=[164.9, 175.1], normal_peak_V=180.0,
        thresholds_changed=False, compensation='22k / 6.8n / 100p unchanged',
        load_nature='equivalent resistive sink I=V(hv)/R; NOT glow tubes, NOT a measured lamp',
        overload_scope=('SCREEN of current-limit behaviour only; not normal-regulation '
                        'qualification, not 195 V OVP qualification'),
        extra_cases=0, preregistered_kinds=list(PREREGISTERED),
        runtime_budget_s=900, solver='single LTspice run per case, Normal solver, unchanged .options',
        acceptance_invented=False,
        status='PRELIMINARY: execution and measurement belong to the principal/lab.execute',
    )
    return s


def describe(kind):
    """Metadata only (same dict as mutate's out-dict); pure, no netlist needed."""
    return dict(kind=kind, stop_s=float(STOPS[kind]), final_window_s=FINAL_WINDOWS[kind],
                load=(LOAD_STEP_DRIVE if kind == 'load_step' else
                      OVERLOAD_DRIVE if kind == 'overload' else 'RLOAD hv 0 5200 (unchanged)'),
                recovery_screen=0.1, normal_band_V=[164.9, 175.1], normal_peak_V=180.0,
                runtime_budget_s=900, preregistered_kinds=list(PREREGISTERED))
