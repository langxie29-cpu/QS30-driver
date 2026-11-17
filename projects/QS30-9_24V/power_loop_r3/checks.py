"""Read-only evidence regression, no new SPICE/model calls."""
from r3lib import *
import argparse,subprocess,csv,collections
def main():
 a=argparse.ArgumentParser();a.add_argument('--historical',action='store_true');v=a.parse_args();checks=[]
 ledger=json.loads((HERE/'evidence/execution_ledger.json').read_text());rs=ledger['records']
 assert len(rs)<=16 and len({r['run_id'] for r in rs})==len(rs);checks.append('unique_runs_and_budget')
 assert not any(p.name.startswith('pending') for p in (HERE/'experiments').iterdir());checks.append('no_unsealed_pending_runs')
 for r in rs:
  p=HERE/r['path'];reg=json.loads((p/'preregister.json').read_text());assert sha(p/'circuit.cir')==reg['netlist_sha256'];assert sha(p/'preregister.json')==r['preregister_sha256']
  for m in json.loads((p/'SHA256.json').read_text()):assert (p/m['path']).stat().st_size==m['bytes'] and sha(p/m['path'])==m['sha256']
 checks.append('all_sealed_file_manifest_bytes')
 metrics=json.loads((HERE/'evidence/final_metrics_index.json').read_text());assert len(metrics)==len(rs)
 for m in metrics:
  if m['classification']=='LIMITED_PASS':assert m['execution']['rc']==0 and m.get('output_only_pass') is True
  if 'short' in m['case']:assert m['classification']=='ELECTRICAL_FAIL'
 assert next(x for x in metrics if x['case']=='tps_instantiated_probe')['classification']=='MODEL_FAIL';checks.append('execution_model_electrical_separation')
 q=json.loads((HERE/'QUALIFICATION_MATRIX.json').read_text());assert q['manufacturing']=='HOLD' and q['actual_frontend_startup']=='INCONCLUSIVE';checks.append('holds_and_actual_frontend_not_promoted')
 # Original R1/R2 and safety paths have no staged or working diff from frozen parent.
 changed=subprocess.check_output(['git','diff','--name-only','bd1762f6b801a004b01de0f31ba5bbb8e2a60a3d'],cwd=ROOT,text=True).splitlines()
 assert all(x.startswith('projects/QS30-9_24V/power_loop_r3/') for x in changed);checks.append('git_changes_R3_only')
 if v.historical:
  before=json.loads((HERE/'evidence/historical_before.json').read_text());bad=[]
  for rec in before:
   p=Path(rec['path'])
   if not p.exists() or p.stat().st_size!=rec['bytes'] or sha(p)!=rec['sha256']:bad.append(str(p))
  dump(HERE/'evidence/historical_after.json',dict(utc=utc(),verified_files=len(before),mismatches=bad,R2_permanently_missing_raws=2));assert not bad;checks.append('all2172_historical_files_byte_identical')
 dump(HERE/'evidence/regression_checks.json',dict(utc=utc(),checks=checks,status='SOFTWARE_EVIDENCE_CHECKS_PASS',electrical_qualification='NOT_INFERRED'));print(json.dumps(checks))
if __name__=='__main__':main()
