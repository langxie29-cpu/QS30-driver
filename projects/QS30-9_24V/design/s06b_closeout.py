"""S06B indices, execution inventory and preservation audit. No electrical release."""
from pathlib import Path
import ast,csv,hashlib,json,collections
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1];OUT=ROOT/'docs/sprint06b'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 # Only current indices change. Historical S05/S06 records remain byte-identical.
 p=ROOT/'config/project.json';c=json.loads(p.read_text());c.update(revision='S06B-QUALIFICATION-AUDIT',lifecycle='07_NOT_PASSED_REAL_MODEL_THERMAL_STARTUP_PG_USB_OPEN',active_design_baseline='config/sprint06b.json',sprint06b_report='docs/SPRINT06B_REPORT.md',latest_breakpoint='docs/BREAKPOINT_S06B_2026-11-15.md');c['unresolved']=[
 'real ST25C transient fails first transition; TI controller/driver coupling fails across engines',
 'hot L(I)/core losses and loss-aware full-load current reserve unqualified',
 'hardware demagnetization detection and current-limited startup mode policy unqualified',
 'RTN-isolated SHDN/FLT/IMON and front-end SOA/default-off not qualified',
 'fast PG loss, guaranteed reset/inhibit timing and partial power not qualified',
 'USB pre-enumeration power, bridge candidate and24to5V failure OVP not qualified',
 'complete protection/latch/bleed/safe reset/native schematic/ERC/PCB remain gated'];dump(p,c)
 p=ROOT/'README.md';s=p.read_text(encoding='utf8');s=s.replace('状态：S06-UNIT-REVIEW，已执行原厂模型/门驱/CT单元与参数审查；24V-07资格仍未通过，08未进入，制造HOLD。','状态：S06B-QUALIFICATION-AUDIT，已接续核查原失败、精确器件模型、损耗/退磁与PG/USB边界；24V-07未通过，08未进入，制造HOLD。');s=s.replace('- 本轮方案与执行：[docs/SPRINT06_PLAN.md](docs/SPRINT06_PLAN.md)、[docs/SPRINT06_REPORT.md](docs/SPRINT06_REPORT.md)','- 本轮方案与执行：[docs/S06B_PLAN.md](docs/S06B_PLAN.md)、[docs/SPRINT06B_REPORT.md](docs/SPRINT06B_REPORT.md)\n- S06历史交付：[docs/SPRINT06_REPORT.md](docs/SPRINT06_REPORT.md)');s=s.replace('[docs/BREAKPOINT_S06_2026-11-15.md](docs/BREAKPOINT_S06_2026-11-15.md)','[docs/BREAKPOINT_S06B_2026-11-15.md](docs/BREAKPOINT_S06B_2026-11-15.md)');s=s.replace('当前为[S06候选增量](config/sprint06.json)，继承[S05数值要求](config/sprint05.json)','当前为[S06B资格审查增量](config/sprint06b.json)，继承[S06候选](config/sprint06.json)与[S05数值要求](config/sprint05.json)');p.write_text(s,encoding='utf8')
 p=ROOT/'docs/TASKS.csv'
 with p.open(encoding='utf-8-sig',newline='') as f:rr=list(csv.DictReader(f))
 for r in rr:r['s06b_evidence']='docs/SPRINT06B_REPORT.md' if r['id'] in ['24V-01','24V-02','24V-03','24V-04','24V-05','24V-06','24V-07','24V-08','24V-11'] else ''
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
 rows=[]
 for p in sorted((ROOT/'sim').glob('s06b_*/results.json')):
  data=json.loads(p.read_text());cases=data.get('cases',[])
  for i,r in enumerate(cases):
   r=dict(r);r.update(run=p.parent.name,index=i,result_file=str(p.relative_to(ROOT)))
   r['scope_class']='TOOL_SETUP_FAILURE' if p.parent.name in ['s06b_engine_compare_v1','s06b_engine_compare_v2','s06b_engine_compare_v3'] and r.get('engine')=='shared' else 'NATIVE_MODEL_DIAGNOSTIC_OR_DEVICE_CELL'
   rows.append(r)
 dump(OUT/'EXECUTION_MATRIX.json',{'cases':rows,'qualification':'Execution PASS is not electrical or07 PASS. Setup failures excluded from device coverage.'})
 replay={p.parent.name:sha(p) for p in sorted((ROOT/'sim/s06b_diagnostic_v1').glob('driver1ns_replay*/waves.txt'))}
 before=json.loads((OUT/'input_snapshot.json').read_text());allowed={'README.md','config/project.json','docs/TASKS.csv'};changed=[];missing=[]
 for name,h in before.items():
  p=ROOT/name
  if not p.exists():missing.append(name)
  elif sha(p)!=h:changed.append(name)
 baseline=json.loads((ROOT/'baseline_snapshot/baseline.json').read_text(encoding='utf8'))['protected_sha256'];legacybad=[]
 for name,h in baseline.items():
  p=REPO/name
  if not p.exists() or sha(p)!=h:legacybad.append(name)
 # S06 recorded manifest comparisons also expose pre-existing edits at turn start.
 m6=json.loads((ROOT/'docs/sprint06/manifest_s06.json').read_text());preexisting=[]
 for n,r in m6.items():
  if n in before and before[n]!=r['sha256']:preexisting.append(n)
 astchecked=[]
 for p in sorted((ROOT/'design').glob('s06b_*.py')):ast.parse(p.read_text(encoding='utf8'),filename=str(p));astchecked.append(str(p.relative_to(ROOT)))
 verification={'date':'2026-11-15','status':'PRESERVATION_AND_AUDIT_ONLY_NOT_ELECTRICAL_RELEASE','process_attempts':len(rows),'native_model_attempts':sum(r['scope_class']!='TOOL_SETUP_FAILURE' for r in rows),'tool_setup_failures':sum(r['scope_class']=='TOOL_SETUP_FAILURE' for r in rows),'execution_pass':sum(r.get('execution')=='PASS' for r in rows),'execution_fail_including_setup':sum(r.get('execution')!='PASS' for r in rows),'new_runs':len(set(r['run'] for r in rows)),'driver_replay_wave_sha256':replay,'driver_replay_identical':len(set(replay.values()))==1,'input_project_files_checked':len(before),'changed_index_files':sorted(changed),'unexpected_changed_files':sorted(set(changed)-allowed),'missing_files':missing,'preexisting_S06_manifest_differences_at_turn_start':preexisting,'legacy_files_checked':len(baseline),'legacy_hash_mismatches':legacybad,'python_AST_checked':astchecked,'native_generated':False,'ERC_DRC':'NOT_RUN_NO_QUALIFIED_NATIVE_DESIGN','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','manufacturing':'HOLD'}
 dump(OUT/'final_verification.json',verification)
 if verification['unexpected_changed_files'] or missing or legacybad:raise RuntimeError('preservation audit failed; inspect final_verification.json')
 # Seal outputs except this self-referential manifest and volatile bytecode.
 manifest={}
 for p in ROOT.rglob('*'):
  if p.is_file() and p!=OUT/'manifest_s06b.json' and '__pycache__' not in p.parts:manifest[str(p.relative_to(ROOT)).replace('\\','/')]={'sha256':sha(p),'bytes':p.stat().st_size}
 dump(OUT/'manifest_s06b.json',manifest);print(json.dumps(verification,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
