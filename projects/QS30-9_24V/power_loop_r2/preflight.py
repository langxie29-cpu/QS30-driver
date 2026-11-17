from pathlib import Path
import json,subprocess,re
import lab,numpy as np
out=lab.HERE/'evidence/preflight';out.mkdir(parents=True,exist_ok=True)
if (out/'baseline_review.json').exists():raise FileExistsError('Audit already recorded')
b=lab.BASE;c=lab.native(b/'circuit.raw');t=c['time'];i=int(np.argmax(c['v(sense)']))
review={'baseline':'96a1afef5e55f84d002f754510b97d8cbd49334f','local_r1_head':subprocess.check_output(['git','-C',str(lab.R1_LOCAL),'rev-parse','HEAD'],text=True).strip(),'r1_diff':subprocess.check_output(['git','-C',str(lab.R1_LOCAL),'diff','HEAD','--','projects/QS30-9_24V/power_loop_r1'],text=True),'raw_sha256':lab.sha(b/'circuit.raw'),'net_sha256':lab.sha(b/'circuit.cir'),'points':len(t),'endpoint':float(t[-1]),'peak_event':{k:float(v[i]) for k,v in c.items()},'source_current_at_peak_A':float(c['v(src)'][i]/.062),'historical_55_60ms':lab.stats(c,.055,.06),'models':{p.name:lab.sha(p) for p in lab.MODEL_SOURCE.iterdir() if p.name in ['controller.sub','st.lib','diode.lib','ss14.lib']},'holds':json.loads((lab.HERE.parent/'safety_r1/governance/holds.json').read_text()),'solver_exe_sha256':lab.sha(lab.LT)}
paths=[lab.R1_LOCAL/f for f in ['ENGINEERING_REPORT.md','CONTROLLER_REVIEW.md','MODEL_MATRIX.md','REPRODUCE.md','orchestrate.py','config.json','tasks.json']]+[p for p in b.iterdir() if p.is_file()]+list((lab.R1_LOCAL/'evidence/independent').glob('*'))
review['required_inputs']=[dict(path=str(p),bytes=p.stat().st_size,sha256=lab.sha(p)) for p in paths if p.is_file()]
log=(b/'circuit.log').read_text(encoding='utf8');review['log_review']={'header':log.splitlines()[:14],'tail':log.splitlines()[-16:],'heightened_def_con_count':log.count('Heightened Def Con'),'fatal_lines':[l for l in log.splitlines() if re.search('fatal|failed|too small|error',l,re.I)]}
lab.dump(out/'baseline_review.json',review)
np.savetxt(out/'historical_sense_event.csv',np.column_stack([v[(t>=t[i]-2e-6)&(t<=t[i]+2e-6)] for v in c.values()]),delimiter=',',header=','.join(c),comments='')
print(json.dumps({k:review[k] for k in ['local_r1_head','raw_sha256','points','endpoint','peak_event','source_current_at_peak_A','historical_55_60ms']},indent=2))
