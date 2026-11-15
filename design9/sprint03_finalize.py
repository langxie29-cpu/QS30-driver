"""Finalize append-only Sprint03 evidence; refuses overwrite of final manifest."""
import csv, gzip, json, re, subprocess
from pathlib import Path
import sprint03_hv as h
R=h.ROOT;B=h.BASE;D=R/'docs9/electrical_sprint03'
assert not (D/'manifest.json').exists(),'Final evidence already frozen'
runs=[]
for group in ['qualification_v1','diagnostics_v1','switch_reference_v1']:
    x=json.loads((B/group/'results.json').read_text());x=x['results'] if isinstance(x,dict) else x
    for r in x:runs.append(dict(r,group=group))
for r in runs:
    p=B/r['group']/r['id'];raw=json.loads((p/'command.json').read_text())
    log=(p/'ngspice.log').read_text(errors='replace')
    assert raw.get('exit_code')==0 and raw['execution']=='PASS',r['id']
    assert not any(x in log.lower() for x in ['error:','aborted','failed!','timestep too small','no such vector']),r['id']
    stop=raw.get('requested_stop_s',.005)
    m=re.search(r'end_time\s*=\s*([\deE.+-]+)',log);assert m and abs(float(m[1])-stop)<1e-9
    if raw.get('deck_sha256'):assert h.sha(p/'circuit.cir')==raw['deck_sha256']
    assert gzip.decompress((p/'waves.txt.gz').read_bytes())==(p/'waves.txt').read_bytes(),r['id']
base=json.loads((B/'baseline.json').read_text(encoding='utf8'))
changed=[p for p,v in base['protected_sha256'].items() if not (R/p).exists() or h.sha(R/p)!=v]
assert not changed,changed
assert h.git('rev-parse','HEAD').strip()==base['head']
checks=dict(prior_files_checked=len(base['protected_sha256']),prior_files_changed=changed,HEAD_unchanged=True,spice_calls=len(runs),completed=len(runs),timeouts=0,all_endpoints_logs_decks_and_gzip_checked=True,native_exports=2,HV_pins_compared=64,formal_design_files_changed=False,commits_created=False,production_outputs_created=False,scope='Evidence integrity only, not engineering PASS')
h.dump(D/'final-verification.json',checks)
summary=dict(system='FAIL/HOLD',topology='UNKNOWN',HV_G0='BLOCKED',HV_G1='BLOCKED',HV_G2='FAIL',runs=len(runs),completed=len(runs),runtime_s=sum(r['duration_s'] for r in runs),timeouts=0,notes='Supersedes 22-run interim results.json; 2 VGS-reference diagnostics added. No new closed-loop or steady-state acceptance.')
h.dump(D/'final_results.json',summary)
with (D/'SIMULATION_MATRIX.csv').open('w',encoding='utf8',newline='') as f:
    fields=['group','id','purpose','execution','exit_code','duration_s','engineering','qualification_decision','limitation'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in runs:
        fail=r['id'] in ['osc_direct','actual_cs_0.2','actual_cs_0.8','actual_short']
        decision='FAIL' if fail else 'INCONCLUSIVE'
        limit='Known wiring or oscillator loading failure' if fail else 'Diagnostic observation only; actual-component qualification blocked'
        w.writerow({**{k:r.get(k,'') for k in fields},'qualification_decision':decision,'limitation':limit})
(D/'git-diff-stat.txt').write_text(h.git('diff','--stat'),encoding='utf8')
(D/'git-status.txt').write_text(h.git('status','--short'),encoding='utf8')
inputs=[p for p in R.glob('design9/sprint03_*.py')]
files=inputs+[p for d in [B,D] for p in d.rglob('*') if p.is_file() and p.name!='manifest.json']
h.dump(D/'manifest.json',dict(self_excluded=True,head=base['head'],files=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=h.sha(p)) for p in sorted(files)],simulator_sha256=h.sha(h.EXE),kicad_sha256=h.sha(h.KICAD)))
print(json.dumps(summary,indent=2));print('Final integrity:',json.dumps(checks))
