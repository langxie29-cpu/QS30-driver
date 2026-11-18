"""Run native, preregistered LTspice experiments and retain compressed original bytes."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OLD = Path(os.getenv('NXT_R4_MODELS', 'D:/PROJECTS/dsharness/QS30-power-loop-r4/projects/QS30-9_24V/power_loop_r4/experiments/sic_1ns_20261118T034706_c01f9cf2'))
EXE = Path(os.getenv('NXT_LTSPICE', 'D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V/toolchain/ltspice26/extracted/LTspice.exe'))
MODELS = ('controller.sub', 'st.lib', 'sic.lib', 'ss14.lib')
SOURCES = ('ADI bundled LT3757A', 'ST STP9NK50Z factory', 'ST STPSC4H065D factory', 'Vishay SS14 factory')
COLD = 'PWL(0 0 100u {vin})'
ZERO = '0'
CASES = {
    'p1c_full': dict(stop=.058, step='350n', model='bounded', wall=260),
    'surrogate_nominal': dict(stop=.095, step='500n', model='bounded', fet='surrogate', wall=110),
    'surrogate_high_line': dict(stop=.095, step='500n', model='bounded', fet='surrogate', vin=13.2, load_wave='2.5', wall=110),
    'surrogate_low_line': dict(stop=.095, step='500n', model='bounded', fet='surrogate', vin=10.8, load_wave='2', wall=110),
    'ovp_pickup': dict(stop=.0008, step='100n', cap_ic='186', vin_wave='13.2', load_wave='0', model='bounded'),
    'isolation_cells': dict(stop=4, step='1m', model='isolation'),
    'warm_line': dict(stop=.006, step='500n', cap_ic='170', vin_wave='PWL(0 10.8 3m 10.8 3.1m 13.2)', model='bounded', temp=25),
    'warm_load': dict(stop=.006, step='500n', cap_ic='170', vin_wave='12', load_wave='PWL(0 1.1475 3m 1.1475 3.1m 1.53)', model='bounded'),
    'warm_max_hot': dict(stop=.004, step='500n', cap_ic='170', vin_wave='10.8', load_wave='2.5', inductance='135u', temp=85, dcr=.20, model='bounded'),
    'warm_ovp': dict(stop=.005, step='500n', cap_ic='170', vin_wave='13.2', load_wave='0', fault_wave='PWL(0 0 2m 0 2.01m 1)', model='bounded'),
    'warm_halfstep': dict(stop=.006, step='250n', cap_ic='170', vin_wave='12', load_wave='PWL(0 1.1475 3m 1.1475 3.1m 1.53)', model='bounded'),
    'warm_retune': dict(stop=.006, step='500n', cap_ic='170', vin_wave='12', load_wave='PWL(0 1.1475 3m 1.1475 3.1m 1.53)', rcomp='10k', ccomp='22n', model='bounded'),
    'bleeder_both': dict(stop=3, step='10m', cap_ic='195', cap='5.5u', vin_wave='0', load_wave='0', model='bounded'),
    'bleeder_single': dict(stop=3, step='10m', cap_ic='195', cap='5.5u', vin_wave='0', load_wave='0', model='bounded', bleed_b='1T'),
    'diagnostic_cold': dict(stop=.023, step='500n', opts='reltol=.006 abstol=10n vntol=50u method=trap plotwinsize=300 numdgt=6 threads=1'),
    'diagnostic_warm': dict(stop=.003, step='250n', cap_ic='168', vin_wave='12', opts='reltol=.006 abstol=10n vntol=50u method=trap plotwinsize=300 numdgt=6 threads=1'),
    'diagnostic_light': dict(stop=.003, step='250n', cap_ic='168', vin_wave='13.2', load_wave='0', opts='reltol=.006 abstol=10n vntol=50u method=trap plotwinsize=300 numdgt=6 threads=1'),
    'diagnostic_ovp': dict(stop=.003, step='250n', cap_ic='186', vin_wave='13.2', load_wave='0', opts='reltol=.006 abstol=10n vntol=50u method=trap plotwinsize=300 numdgt=6 threads=1'),
    'diagnostic_decay': dict(stop=2, step='5m', cap_ic='195', vin_wave='0', load_wave='0', opts='reltol=.003 abstol=1n vntol=10u method=gear plotwinsize=300 numdgt=6 threads=1'),
    'nominal': {},
    'low_high': dict(vin=10.8, load_wave='1.53'),
    'high_max': dict(vin=13.2, load_wave='2.50'),
    'low_2w': dict(vin=10.8, load_wave='2.00'),
    'no_tubes': dict(vin=13.2, load_wave=ZERO),
    'line_step': dict(vin_wave='PWL(0 0 100u 10.8 48m 10.8 48.1m 13.2)', stop=.076),
    'load_step': dict(load_wave='PWL(0 1.1475 48m 1.1475 48.1m 1.53)', stop=.076),
    'ovp_fault': dict(fault_wave='PWL(0 0 45m 0 45.01m 1)', stop=.070, late_end=.044),
    'disconnect': dict(vin_wave='PWL(0 0 100u 12 48m 12 48.1m 0)', stop=.085, late_end=.047),
    'hot_min_l': dict(vin=10.8, temp=85, inductance='135u', dcr=.20, load_wave='2.00'),
    'half_step': dict(step='100n'),
    'p2_nominal': dict(rcomp='10k', ccomp='22n'),
    'p2_no_tubes': dict(rcomp='10k', ccomp='22n', vin=13.2, load_wave=ZERO),
    'p2_low_2w': dict(rcomp='10k', ccomp='22n', vin=10.8, load_wave='2.00'),
    'p3_nominal': dict(shunt=.115, rcomp='10k', ccomp='22n'),
}

def sha(path):
    with path.open('rb') as output:
        digest = hashlib.sha256()
        for block in iter(lambda: output.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def dump(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')

def readlog(path):
    if not path.exists():
        return ''
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-16le' if raw[1:2] == b'\x00' else 'utf-8', errors='replace')

def run(case, dest):
    params = dict(vin=12, vin_wave=COLD, load_wave='1.1475', fault_wave=ZERO, temp=25,
                  step='200n', stop=.064, inductance='150u', dcr=.16, cap='5u',
                  shunt=.13, rcomp='22k', ccomp='6.8n', rt='140k', cap_ic='0', model='esl', bleed_b='249k', fet='vendor', wall=130, opts='reltol=.001 abstol=1n vntol=10u method=gear plotwinsize=300 numdgt=8 threads=1')
    params.update(CASES[case])
    if params['model'] == 'bounded':
        params['opts'] = 'reltol=.006 abstol=10n vntol=50u method=trap plotwinsize=300 numdgt=6 threads=1'
    params['output_cap'] = ('Resr hv vcstore .0211\nCout vcstore 0 {cap}\n.ic V(hv)={cap_ic} V(vcstore)={cap_ic}' if params['model']=='bounded' else 'Cout hv 0 {cap} Rser=.0211 Lser=19n IC={cap_ic}').format(**params)
    params['fet_stage'] = ('Sq sw src gate src FETPROXY\n.model FETPROXY SW(Ron=.75 Roff=100Meg Vt=5 Vh=-1)\nCgs gate src 1n\nCgd gate sw 25p\nCds sw src 80p' if params['fet']=='surrogate' else 'Xq sw gate src STP9NK50Z')
    params['trace_list'] = 'V(raw) V(in) V(hv) V(sw) V(gate) V(src) V(sense) V(pwm) V(vc) V(en) V(latch) I(Lpower) I(Drec) I(Cout) I(VINPUT)'
    params['vin_wave'] = params['vin_wave'].format(**params)
    params.setdefault('late_end', params['stop'] - .001)
    params['late_start'] = max(0, params['late_end'] - min(.008, params['stop']/4))
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    model_dir = dest/'models'
    model_dir.mkdir()
    models = []
    for name, source in zip(MODELS, SOURCES):
        path = model_dir/name
        shutil.copyfile(OLD/name, path)
        models.append(dict(file=name, source=source, sha256=sha(path)))
    deck = dest/'boost.cir'
    deck.write_text((HERE/('isolation.cir' if case=='isolation_cells' else 'boost.cir.template')).read_text(encoding='utf-8').format(**params), encoding='ascii')
    command = [str(EXE), '-b', str(deck)]
    dump(dest/'preregister.json', dict(case=case, hypothesis='See SIMULATION_MATRIX.csv', inputs=params, models=models,
         tool_sha256=sha(EXE), command=command, netlist_sha256=sha(deck),
         limits=dict(mean_V=[165,175], ripple_Vpp=2, normal_peak_V=180, start160_s=.05, fault_peak_V=195),
         scope='Real controller and semiconductor models; driver, pre-stage, tube loads and OVP timing approximated.'))
    start = time.monotonic()
    execution = 'EXITED'
    environment = dict(os.environ, LOCALAPPDATA=str(dest/'cache'), APPDATA=str(dest/'config'))
    for directory in ('cache', 'config'):
        (dest/directory).mkdir()
    rc = None
    try:
        proc = subprocess.run(command, cwd=dest, env=environment, capture_output=True,
                              timeout=params['wall'], creationflags=subprocess.CREATE_NO_WINDOW)
        rc = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        execution = 'EXECUTION_FAIL'
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
    except OSError as exc:
        execution = 'EXECUTION_FAIL'
        stdout, stderr = b'', str(exc).encode()
    (dest/'stdout.txt').write_bytes(stdout)
    (dest/'stderr.txt').write_bytes(stderr)
    log = readlog(dest/'boost.log')
    values = {}
    for key, value in re.findall(r'^([a-z0-9_]+):[^=\r\n]*=\s*(-?[0-9.]+(?:e[+-]?\d+)?)', log, flags=re.I|re.M):
        if not key.lower().startswith(('warning','error')):
            values[key.lower()] = float(value)
    for key in ('start_160','fault_time','dual_60','single_60'):
        hit = re.search(r'^'+key+r':.*?\bAT\s+([0-9.eE+-]+)', log, re.I|re.M)
        values.pop(key, None)
        if hit:
            values[key] = float(hit.group(1))
    raw = dest/'boost.raw'
    classification = execution
    if execution == 'EXITED':
        if re.search(r'unknown subcircuit|cannot open|error on line|undefined model', log, re.I):
            classification = 'MODEL_FAIL'
        elif not raw.exists() or rc or 'hv_end' not in values:
            classification = 'SOLVER_FAIL'
        elif case=='isolation_cells':
            passed = (abs(values.get('dual_60',0)-1.614)<.01 and abs(values.get('single_60',0)-3.228)<.02
                      and values.get('passive_now',0)>9 and abs(values.get('isolated_now',99))<.02)
            classification = 'LIMITED_PASS' if passed else 'ELECTRICAL_FAIL'
        elif case=='ovp_pickup':
            classification = 'LIMITED_PASS' if values.get('fault_time',0)>0 and values.get('hv_peak',1000)<195 else 'ELECTRICAL_FAIL'
        elif case.startswith(('warm_', 'bleeder_')):
            classification = 'INCONCLUSIVE'
            if case.startswith('bleeder_') and 0 < values['hv_end'] < 195.1 and values.get('hv_peak', 1000) < 195.1:
                classification = 'LIMITED_PASS'
            if case == 'warm_ovp' and values.get('hv_peak', 0) > 195:
                classification = 'ELECTRICAL_FAIL'
        elif case.startswith('diagnostic'):
            classification = 'INCONCLUSIVE' if 'diagnostic_decay' != case else 'LIMITED_PASS'
        elif case in ('disconnect', 'ovp_fault'):
            passed = case == 'disconnect' or (
                values.get('fault_time', 0) > .045 and values.get('hv_peak', 1000) <= 195)
            classification = 'LIMITED_PASS' if passed else 'ELECTRICAL_FAIL'
        else:
            passed = (165 <= values.get('hv_avg', -1) <= 175 and values.get('hv_pp', 1000) <= 2
                      and values.get('hv_peak', 1000) <= 180 and values.get('start_160', 1000) <= .05)
            classification = 'LIMITED_PASS' if passed else 'ELECTRICAL_FAIL'
    evidence = []
    for path in (deck, dest/'preregister.json', dest/'boost.log', dest/'stdout.txt', dest/'stderr.txt'):
        if path.exists():
            evidence.append(dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path)))
    if raw.exists():
        with raw.open('rb') as source:
            for i in range(100):
                first = source.read(32*1024*1024)
                if not first:
                    break
                part = dest/f'boost.raw.part{i:02d}.gz'
                with part.open('xb') as container, gzip.GzipFile(filename='', mode='wb', fileobj=container, mtime=0, compresslevel=4) as out:
                    out.write(first)
                evidence.append(dict(file=part.name, bytes=part.stat().st_size, sha256=sha(part)))
            if source.read(1):
                raise ValueError('increase archive capacity with an explicit manifest revision')
        raw_info = dict(bytes=raw.stat().st_size, sha256=sha(raw))
    else:
        raw_info = None
    dump(dest/'result.json', dict(case=case, exit_code=rc, execution=execution,
         classification=classification, seconds=round(time.monotonic()-start,3),
         measures=values, raw=raw_info, evidence=evidence))
    print(case, classification, values, flush=True)

if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('case', choices=CASES)
    cli.add_argument('--output', type=Path)
    args = cli.parse_args()
    run(args.case, args.output or HERE/'runs'/args.case)
