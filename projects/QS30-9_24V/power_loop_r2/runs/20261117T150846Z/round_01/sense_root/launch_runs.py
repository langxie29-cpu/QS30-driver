"""sense_root phase B: launch exactly the THREE preregistered diagnostic runs via lab.full/lab.execute.

No retries, no new cases, no component or model edits. Failures are preserved verbatim.
Timeout 180 s each; raw files are kept in place.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R2 = Path('D:/PROJECTS/dsharness/QS30-power-loop-r2/projects/QS30-9_24V/power_loop_r2')
sys.path.insert(0, str(R2))
import lab  # noqa: E402

SPEC = [
    ('run_gear_2e-7', 2e-7, 'gear'),
    ('run_gear_1e-7', 1e-7, 'gear'),
    ('run_trap_2e-7', 2e-7, 'trap'),
]
HYP = ('Diagnostic observability/solver sensitivity at the 10.040718ms SENSE event: does adding only '
       'observation probes (no topology/component/model change) preserve the R1 global peak, and are the '
       'MOS/snubber/negative-clamp port currents extractable within 180s to 10.08ms?')

out = []
for name, step, method in SPEC:
    d = HERE / name
    lab.full(d, stop=.01008, step=step, method=method)
    hyp = HYP + f' Case {name}: stop=10.08ms step={step:g}s method={method}.'
    res = lab.execute(d, hyp, f'diagnostic observability only; unique main variable = tran method/step ({method},{step:g}s); stop extended 10.00ms->10.08ms done via lab.full options', timeout=180)
    log = (d / 'circuit.log')
    tail = log.read_text(encoding='latin-1')[-2500:] if log.exists() else 'NO LOG'
    (d / 'run.log').write_text((d / 'circuit.log').read_text(encoding='latin-1') if log.exists() else 'NO LOG PRODUCED\n', encoding='utf8')
    out.append(dict(run=name, step=step, method=method, command=res,
                    raw_exists=(d / 'circuit.raw').exists(),
                    raw_bytes=(d / 'circuit.raw').stat().st_size if (d / 'circuit.raw').exists() else 0,
                    log_tail=tail[-1200:]))
    print(name, res['status'], res['rc'], round(res['elapsed_s'], 1), flush=True)
lab.dump(HERE / 'runs_command.json', out)
