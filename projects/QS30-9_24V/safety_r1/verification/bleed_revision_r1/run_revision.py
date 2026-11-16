"""Pre-registered independent bleeder redesign; 24V scaled RC only."""
from pathlib import Path
import datetime,hashlib,json,math,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=HERE/'evidence';out.mkdir(exist_ok=False)
    cases=[(kind,step) for kind in ('both_strings','one_string_open','one_resistor_short') for step in (.002,.001)]
    cap=21.315e-6;resistor=90900*1.01;threshold=24*60/195
    dump(out/'preregister.json',{'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Passive 24V scaled linear RC only. Real resistor MPN/package/thermal/voltage qualification HOLD.',
        'Cmax_F':cap,'each_resistor_max_ohm':resistor,'cases':cases,
        'criteria':{'scaled_threshold_V':threshold,'time_max_s':5,'analytic_wave_relative_error_max':.002,'half_step_time_delta_s_max':.002},
        'physical_requirement':'Each resistor must withstand195V and >=0.42W hot-rated under its series partner short; exact MPN still HOLD.',
        'exe_sha256':sha(EXE),'version':subprocess.check_output([str(EXE),'--version'],text=True,errors='replace'),'python':sys.version})
    rows=[]
    for kind,step in cases:
        d=out/f'{kind}_{step*1000:g}ms';d.mkdir()
        if kind=='both_strings':network=f'R1 bus a {resistor}\nR2 a 0 {resistor}\nR3 bus b {resistor}\nR4 b 0 {resistor}\n';req=resistor
        elif kind=='one_string_open':network=f'R1 bus a {resistor}\nR2 a 0 {resistor}\n';req=2*resistor
        else:network=f'R1 bus 0 {resistor}\nR3 bus b {resistor}\nR4 b 0 {resistor}\n';req=2*resistor/3
        deck=f'''Safety R1 revised bleeder {kind}; low voltage scaled only
C1 bus 0 {cap} IC=24
{network}
.options reltol=.0001 abstol=1n vntol=1u
.control
set noaskquit
set numdgt=15
set wr_singlescale
set wr_vecnames
tran {step} 6 0 {step} uic
wrdata waves.txt v(bus)
quit
.endc
.end
'''
        (d/'circuit.cir').write_text(deck,encoding='ascii');argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']
        process=subprocess.run(argv,cwd=d,capture_output=True,text=True,errors='replace',timeout=20)
        data=[[float(x) for x in l.split()] for l in (d/'waves.txt').read_text().splitlines()[1:] if l.strip()]
        log=(d/'ngspice.log').read_text(errors='replace')
        valid=process.returncode==0 and data[-1][0]>=6-1e-9 and all(math.isfinite(x) for row in data for x in row) and all(a[0]<b[0] for a,b in zip(data,data[1:])) and not any(k in log.lower() for k in ('aborted','time step too small','fatal','error:'))
        crossing=None
        for (ta,va),(tb,vb) in zip(data,data[1:]):
            if va>=threshold>=vb:
                crossing=ta+(tb-ta)*(va-threshold)/(va-vb);break
        error=max(abs(v-24*math.exp(-t/(req*cap)))/24 for t,v in data)
        row={'kind':kind,'step_s':step,'argv':argv,'rc':process.returncode,'stdout':process.stdout,'stderr':process.stderr,
             'execution':'PASS' if valid else 'FAIL','end_s':data[-1][0],'analytic_t60_s':req*cap*math.log(195/60),
             'scaled_interpolated_t60_s':crossing,'max_normalized_wave_error':error,
             'limited_electrical':'PASS' if valid and crossing is not None and crossing<=5 and error<=.002 else 'FAIL',
             'deck_sha256':sha(d/'circuit.cir')}
        dump(d/'result.json',row);rows.append(row)
    compare=[]
    for kind in ('both_strings','one_string_open','one_resistor_short'):
        pair=[r for r in rows if r['kind']==kind];delta=abs(pair[0]['scaled_interpolated_t60_s']-pair[1]['scaled_interpolated_t60_s'])
        compare.append({'kind':kind,'t60_delta_s':delta,'result':'PASS' if delta<=.002 else 'FAIL'})
    dump(out/'results.json',{'attempts':6,'execution_pass':sum(r['execution']=='PASS' for r in rows),'limited_electrical_pass':sum(r['limited_electrical']=='PASS' for r in rows),'cases':rows,'half_step_comparisons':compare,
         'extra170V_load_W':170**2*(2/181800-1/200000),'24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','24V_10':'NOT_PASSED','manufacturing':'HOLD'})
    print(json.dumps({'attempts':6,'pass':sum(r['limited_electrical']=='PASS' for r in rows),'worst_t60_s':max(r['scaled_interpolated_t60_s'] for r in rows),'half_steps':compare},indent=2))
if __name__=='__main__':main()
