"""A9.2 meaningful evidence regression checks; no ERC/DRC suppression."""
from pathlib import Path
import hashlib
import json
import re
import csv
from safety_sim9 import execution_ok

ROOT=Path(__file__).resolve().parents[1]


def main():
    checks=[]
    def check(cid,ok,why):
        checks.append(dict(id=cid,status='PASS' if ok else 'FAIL',evidence=why))
    good='No. of Data Rows : 100\nend_time = 8.00000e-02\n'
    check('V01',execution_ok(good,.08,0,True),'Completed endpoint accepted')
    check('V02',not execution_ok(good+'tran simulation(s) aborted',.08,0,True),'rc=0 and linearized endpoint cannot conceal aborted analysis')
    check('V03',not execution_ok(good+'Timestep too small',.08,0,True),'rc=0 timestep failure rejected')
    check('V04',not execution_ok(good+'Error: vector missing',.08,0,True),'rc=0 vector export failure rejected')
    check('V05',not execution_ok('No. of Data Rows : 10\nend_time = .001',.08,0,True),'Incomplete genuine endpoint rejected')
    check('V06',not execution_ok(good,.08,1,True) and not execution_ok(good,.08,0,False),'nonzero return/missing wave rejected')
    expected={'baseline_final_model':17,'final_actual_model':17,'comp_precharged':7,'full_ref_corners':2}
    for run,count in expected.items():
        folder=ROOT/'sim/a9_2'/run
        results=json.loads((folder/'results.json').read_text())['results']
        valid=len(results)==count
        for rec in results:
            case=rec['scenario'];path=folder/case['id']
            log=(path/'ngspice.log').read_text(errors='replace')
            valid &= execution_ok(log,case.get('stop',.08 if case.get('mode','boost')=='boost' else .04),rec['rc'],(path/'waves.csv.gz').exists())
            valid &= rec['execution']=='PASS' and rec['protection_signoff']=='FAIL'
        check('V-SIM-'+run,valid,f'{count} genuine completed runs; protection signoff remains FAIL')
    invalidated=json.loads((ROOT/'sim/a9_2/invalidated_runs.json').read_text())
    check('V07',invalidated['a9_2_actual']['status']=='FAIL' and all(not execution_ok(
        p.read_text(errors='replace'),.04,0,True) for p in (ROOT/'sim/a9_2/a9_2_actual').glob('*/ngspice.log')),
        'All 17 aborted intermediate analyses are explicitly invalidated, prior JSON retained')
    erc=[];drc=[]
    native=json.loads((ROOT/'kicad/logs/a9_2_final/results.json').read_text(encoding='utf8'))
    for board,data in native['boards'].items():
        check('V-NET-'+board,data['reconciliation']=='PASS' and not data['merges'] and not data['splits'] and not data['pcb_pad_mismatches'],'Exact native connected members / PCB attributes / explicit NC inventory')
        erc.append(data['erc']);drc.append(data['drc'])
    check('V08',sum(e['severity'].get('error',0) for e in erc)==0 and sum(e['severity'].get('warning',0) for e in erc)==364,'ERC 7 original errors removed, 364 warnings remain')
    check('V09',sum(e['total'] for e in drc)==753 and sum(e['by_type'].get('shorting_items',0)+e['by_type'].get('clearance',0)+e['by_type'].get('solder_mask_bridge',0)+e['by_type'].get('copper_edge_clearance',0) for e in drc)==0,'488 placeholder geometry findings removed, DRC still FAIL 753')
    check('V10',all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in native['input_sha256'].items()),'Final native capture hashes still match current design inputs')
    before=json.loads((ROOT/'kicad/logs/a9_2_before/results.json').read_text(encoding='utf8'))
    after=native
    check('V11',sum(e[k]['total'] for e in before['boards'].values() for k in ('erc','drc'))==1587 and sum(e[k]['total'] for e in after['boards'].values() for k in ('erc','drc'))==1117,'Original 1587 means ERC+DRC; final 1117, delta470')
    rows=list(csv.DictReader((ROOT/'docs9/a9_2_evidence/all_native_items.csv').open(encoding='utf-8-sig')))
    check('V12',len(rows)==2704 and len({r['id'] for r in rows})==2704 and all(r['refs'] for r in rows if r['rule']=='shorting_items'),'Every before/final native item uniquely indexed; Chinese shorting descriptions mapped to real refs')
    audit=json.loads((ROOT/'kicad/logs/a9_2_final/electrical_audit.json').read_text(encoding='utf8'))
    check('V13',all(c['status']=='PASS' for c in audit['checks']),'12 architecture/90 cathode/9 anode/interface/return/serial checks still PASS')
    dest=ROOT/'sim/a9_2/verification.json'
    dest.write_text(json.dumps(dict(status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',checks=checks),indent=2)+'\n')
    print(dest.read_text())
    return 0 if all(c['status']=='PASS' for c in checks) else 1


if __name__=='__main__':raise SystemExit(main())
