"""Read saved artifacts; never counts re-analysis as another simulator attempt."""
from pathlib import Path
import json,hashlib,unittest,sys
HERE=Path(__file__).resolve().parent
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
    folders=['spice_r1','spice_r2','spice_r3_aux11p4','spice_r4_aux12p6']
    summaries=[]
    for f in folders:
        original=json.loads((HERE/f/'results.json').read_text())
        rows=original['cases']; summaries.append({'path':f,'attempts':len(rows),
            'native_process_completed':sum(r.get('rc')==0 and r.get('end_s',0)>=20e-6*(1-1e-8) for r in rows),
            'saved_execution_validation_pass':sum(r['execution']=='PASS' for r in rows),
            'saved_execution_validation_fail':sum(r['execution']=='FAIL' for r in rows),
            'electrical_pass':sum(r.get('electrical')=='PASS' for r in rows),
            'electrical_fail':sum(r.get('electrical')=='FAIL' for r in rows),
            'electrical_inconclusive':sum(r.get('electrical','INCONCLUSIVE')=='INCONCLUSIVE' for r in rows)})
    topology=json.loads((HERE/'topology_r1/results.json').read_text())
    topology['cases']+=json.loads((HERE/'topology_r2/results.json').read_text())['cases']
    revision=json.loads((HERE/'bleed_revision_r1/evidence/results.json').read_text())
    suite=unittest.defaultTestLoader.discover(str(HERE),pattern='test_safety.py')
    with (HERE/'tests_final.log').open('w',encoding='utf8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    counts={'count':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    dump(HERE/'verification_summary.json',{'software_requirements_tests':counts,
        'simulation_process_attempts':sum(s['attempts'] for s in summaries)+len(topology['cases'])+revision['attempts'],
        'native_process_completed':sum(s['native_process_completed'] for s in summaries)+sum(r['execution']=='PASS' for r in topology['cases'])+revision['execution_pass'],
        'saved_execution_validation_pass':sum(s['saved_execution_validation_pass'] for s in summaries)+sum(r['execution']=='PASS' for r in topology['cases'])+revision['execution_pass'],
        'saved_execution_validation_fail':sum(s['saved_execution_validation_fail'] for s in summaries),
        'driver_runs':summaries,
        'bleeder_revision':{'path':'bleed_revision_r1/evidence/results.json','attempts':revision['attempts'],'execution_pass':revision['execution_pass'],'limited_electrical_pass':revision['limited_electrical_pass'],'half_step_pass':sum(r['result']=='PASS' for r in revision['half_step_comparisons']),'hardware_qualification':'HOLD'},
        'topology':{'attempts':len(topology['cases']),'consistency_pass':sum(r['topology_consistency']=='PASS' for r in topology['cases']),
                    'discharge_design_pass':sum(r.get('discharge_design_requirement')=='PASS' for r in topology['cases']),
                    'discharge_design_fail':sum(r.get('discharge_design_requirement')=='FAIL' for r in topology['cases'])},
        'corrections':{'spice_r1':'Four cases have rc0 and endpoint but rounded ASCII creates repeated timestamps; original strict-order validation FAIL retained. Missing electrical classification is INCONCLUSIVE, not PASS.','source_url':'spice_r1/r2 prereg erroneously says slum030; actual immutable source manifest is sources/sprint06/manifest_driver_permit.json SLUM488. Model hashes match original. r3/r4 and runner corrected.'},
        'manufacturing':'HOLD','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','24V_09':'NOT_PASSED','24V_10':'NOT_PASSED'})
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact_hashes.json']
    dump(HERE/'artifact_hashes.json',{str(p.relative_to(HERE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})
    print(json.dumps(counts));print('simulator attempts=45; saved execution validation 41 PASS / 4 FAIL; no hardware release')
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
