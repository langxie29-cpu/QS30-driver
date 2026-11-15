"""S06 evidence summary/index updates; never rewrites S05 evidence or legacy files."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1];OUT=ROOT/'docs/sprint06'
RUNS=['s06_controller_v1','s06_controller_v2','s06_gate_v3','s06_buffered_gate_v1','s06_driver_unit_v1']
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(p,rows):
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 execrows=[]
 for run in RUNS:
  result=json.loads((ROOT/'sim'/run/'results.json').read_text(encoding='utf8'))
  for i,r in enumerate(result['cases']):
   execrows.append(dict(run=run,index=i,case=r.get('case',r.get('mode')),step_s=r.get('step_s'),VDD_V=r.get('vdd_V'),execution=r.get('execution','FAIL'),engineering=r.get('engineering','NOT_EVALUATED'),end_s=r.get('end_s'),frequency_Hz=r.get('frequency_Hz'),CS_delay_s=json.dumps(r.get('CS_to_OUT_6V_delay_s',[])),gate_delay_s=json.dumps(r.get('CS_to_gate_below3V_s',r.get('gate_fall_delay_s',[]))),error=r.get('error','')))
 table(OUT/'EXECUTION_MATRIX.csv',execrows)
 modelrows=[]
 for p in (ROOT/'sources/sprint06').rglob('*'):
  if p.is_file() and p.suffix.lower()=='.lib':
   b=p.read_bytes();enc=b.startswith((b'<Encrypted',b'**$ENCRYPTED'))
   status='FORMAT_UNSUPPORTED_IN_NGSPICE' if enc else 'SOURCE_ONLY_NOT_TESTED'
   if 'UCCx8C43_unencrypted' in p.parts:status='NOMINAL_OSC_UVLO_CS_PARTIAL_QUALIFIED'
   if 'UCC27511_unencrypted' in p.parts:status='SYNTAX_ADAPTATION_STANDALONE_PARTIAL_STEP_CRASH_AND_INTEGRATION_FAIL'
   modelrows.append(dict(file=str(p.relative_to(ROOT)).replace('\\','/'),sha256=sha(p),encrypted=enc,qualification=status))
 table(OUT/'MODEL_QUALIFICATION.csv',modelrows)
 # Plot native numerical results, with each fixture's different time reference explicit.
 fig,ax=plt.subplots(3,1,figsize=(9,9),layout='constrained')
 for case,label in [('osc_nominal_10ns','Unloaded CT'),('osc_load10k_10ns','CT shunt 10k (stopped)'),('osc_buffer1meg_10ns','CT shunt 1M (load surrogate)')]:
  a=np.loadtxt(ROOT/'sim/s06_controller_v1'/case/'waves.txt',skiprows=1);sel=(a[:,0]>=200e-6)&(a[:,0]<=230e-6);ax[0].plot((a[sel,0]-200e-6)*1e6,a[sel,3],label=label)
 ax[0].set(xlabel='Time after 200 us (us)',ylabel='CT (V)',title='Primary UCC28C43 model: CT loading');ax[0].legend(fontsize=8)
 a=np.loadtxt(ROOT/'sim/s06_gate_v3/cs_gate64nc_5ns/waves.txt',skiprows=1);sel=(a[:,0]>299.95e-6)&(a[:,0]<300.6e-6)
 ax[1].plot((a[sel,0]-300e-6)*1e9,a[sel,7],label='Gate, 22 ohm / 64nC surrogate');ax[1].axhline(3,color='gray',ls=':');ax[1].axvline(170,color='red',ls='--',label='S05 total delay allocation170ns');ax[1].set(xlabel='Time after CS step (ns)',ylabel='Gate (V)',title='Controller direct drive: allocation failed');ax[1].legend(fontsize=8)
 a=np.loadtxt(ROOT/'sim/s06_driver_unit_v1/11.4_switch_2ns/waves.txt',skiprows=1);sel=(a[:,0]>29.95e-6)&(a[:,0]<30.3e-6)
 ax[2].plot((a[sel,0]-30.003e-6)*1e9,a[sel,3],label='Standalone UCC27511, 10/2.2ohm');ax[2].axhline(3,color='gray',ls=':');ax[2].set(xlabel='Time after driver IN falling midpoint (ns)',ylabel='Gate (V)',title='Standalone buffer: nominal partial pass; step/integration unqualified');ax[2].legend(fontsize=8)
 for a in ax:a.grid(alpha=.2)
 fig.savefig(OUT/'unit_diagnostics.png',dpi=160);plt.close(fig)
 # Current indices only; old S05 numeric requirements, reports, decks and manifests remain unchanged.
 p=ROOT/'config/project.json';project=json.loads(p.read_text(encoding='utf8'));project.update(revision='S06-UNIT-REVIEW',date='2026-11-15',active_design_baseline='config/sprint06.json',sprint06_report='docs/SPRINT06_REPORT.md',lifecycle='UNIT_QUALIFICATION_PARTIAL_07_NOT_PASSED',manufacturing='HOLD');dump(p,project)
 p=ROOT/'docs/TASKS.csv';rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
 for row in rows:
  row['s06_evidence']='docs/SPRINT06_REPORT.md' if row['id'] in ['24V-01','24V-02','24V-03','24V-04','24V-05','24V-06','24V-07','24V-08','24V-11'] else ''
 table(p,rows)
 snap=json.loads((OUT/'input_snapshot.json').read_text(encoding='utf8'));allowed={'config/project.json','docs/TASKS.csv','README.md'}
 changed=[];missing=[]
 for rel,h in snap.items():
  p=ROOT/rel
  if not p.exists():missing.append(rel)
  elif sha(p)!=h:changed.append(rel)
 unexpected=[x for x in changed if x not in allowed]
 base=json.loads((ROOT/'baseline_snapshot/baseline.json').read_text(encoding='utf8'))['protected_sha256'];legacybad=[rel for rel,h in base.items() if not (REPO/rel).exists() or sha(REPO/rel)!=h]
 analysis=json.loads((OUT/'analysis.json').read_text(encoding='utf8'))
 assert analysis['feedback']['S06_200k']['pass_this_error_budget']
 assert not analysis['feedback']['S05_2Meg']['pass_this_error_budget']
 assert analysis['reset_3V3']['new_rising_max_V_conservative']<3.135
 assert analysis['reset_3V3']['new_falling_interval_V'][0]>3
 assert analysis['24V_07']=='NOT_PASSED' and analysis['24V_08']=='NOT_ENTERED'
 assert not unexpected and not missing and not legacybad,(unexpected,missing,legacybad)
 meta=json.loads((ROOT/'netlist/s06_candidate_power_pins.meta.json').read_text(encoding='utf8'));assert not meta['approved_for_native_generation']
 summary={'date':'2026-11-15','work_started':'2026-11-14','timezone':'Asia/Shanghai','status':'EVIDENCE_INTEGRITY_ONLY_NOT_ELECTRICAL_RELEASE','actual_simulator_invocations':len(execrows),'execution_pass':sum(r['execution']=='PASS' for r in execrows),'execution_fail':sum(r['execution']!='PASS' for r in execrows),'engineering_partial_scope_pass':sum(r['engineering'].startswith('PASS') for r in execrows),'input_project_files_checked':len(snap),'changed_index_files':changed,'unexpected_changed_files':unexpected,'missing_files':missing,'legacy_files_checked':len(base),'legacy_hash_mismatches':legacybad,'native_generated':False,'ERC_DRC':'NOT_RUN_NO_NATIVE24V_DESIGN','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','manufacturing':'HOLD','unresolved':['hot nonlinear magnetic and ST MOS/rectifier model','driver step crash and integrated model nonconvergence','startup/CCM/DCM strategy and CT buffer/ramp hardware','PG/partial-power/RTN and eFuse dynamics/SOA','USB boot/enumeration/inrush and5V fault OVP','independent OVP/OC latch/reset/bleed single faults']}
 dump(OUT/'final_verification.json',summary)
 manifest={str(p.relative_to(ROOT)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size} for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest_s06.json'}
 dump(OUT/'manifest_s06.json',manifest);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
