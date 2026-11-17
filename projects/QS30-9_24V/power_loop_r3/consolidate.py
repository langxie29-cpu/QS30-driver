from analyze import *
import csv,collections
def main():
 results=[]
 for p in sorted((HERE/'experiments').iterdir()):
  if p.name.startswith('pending'):continue
  cached=HERE/'evidence/metrics_final'/f'{p.name}.json'
  if cached.exists():m=json.loads(cached.read_text())
  else:
   m=measure(p)
   if m['case']=='tps_encrypted_probe':m['classification']='INCONCLUSIVE';m['scope']='No TPS instance: smoke execution only, not model compatibility evidence.'
   if m['case']=='tps_instantiated_probe':m['classification']='MODEL_FAIL';m['model_failure']='LTspice parser interprets encrypted body as device syntax: Fatal Error Too few nodes. Execution rc1 kept separately.'
   if m['case']=='front24_restart':m['qualification_scope']='Power interruption fixture only; no real manual-fresh interlock. Automatic resumption is not an approved system behavior.';m['classification']='INCONCLUSIVE'
   dump(cached,m)
  results.append(m)
 dump(HERE/'evidence/final_metrics_index.json',results)
 fixed=dict(mean_V=[164.9,175.1],raw_ripple_Vpp=1,normal_peak_V=180,cold_start_s=1,recovery_s=.1,fault_peak_V=195)
 q=dict(overall='INCONCLUSIVE',actual_frontend_startup='INCONCLUSIVE',manufacturing='HOLD',frozen_limits=fixed,cases=[dict(case=m['case'],software_execution=m['execution']['execution_status'],native_rc=m['execution']['rc'],endpoint_s=m.get('endpoint_s'),electrical=m['classification'],scope=m.get('qualification_scope',m.get('failure_scope',m['scope'])),metrics=str((HERE/'evidence/metrics_final'/f'{Path(m["path"]).name}.json').relative_to(HERE))) for m in results],unexecuted=[dict(test=x,status='INCONCLUSIVE',reason='Model/maximum parameter/physical implementation evidence missing') for x in ['actualTPS26601_fulltemperature_delay_SOA','U100_U101_fuse_coordination','hot_L_I_T_coreloss','real_nine_tube_dynamic','independent_OVP195V_faults','complete_H01_H10_single_and_double_faults','full_R2_loadstep_under_new_frontend','full_emptyload_tolerance_temperature_matrix']])
 dump(HERE/'QUALIFICATION_MATRIX.json',q)
 print(json.dumps([dict(case=m['case'],classification=m['classification'],IL_peak=m.get('i(lpower)',{}).get('max'),ripple=m.get('windows')) for m in results]),flush=True)
if __name__=='__main__':main()
