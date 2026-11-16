"""24V scaled passive-path and RC topology checks, NOT component qualification."""
from pathlib import Path
import subprocess,json,hashlib,math,datetime,argparse
from run_spice import HERE,EXE,dump,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=HERE/'topology_reproduction');p.add_argument('--only')
    args=p.parse_args();out=args.output.resolve();out.mkdir(exist_ok=False)
    cases=[('all_bleeders',21.315e-6,202e3/4),('one_bleeder_open',21.315e-6,202e3/3),
           ('main_only',21e-6,202e3),('main_bleeder_open',21e-6,1e15),
           ('input_switch_off',0,1e12),('input_switch_stuck_on',0,1),
           ('main_bleeder_only_modules_cap_connected',21.315e-6,202e3)]
    if args.only:cases=[x for x in cases if x[0]==args.only]
    if not cases:raise ValueError('Unknown case')
    dump(out/'preregister.json',{'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Linear passive topology with 24V maximum; discharge scaled from195V by factor24/195. No true HV or physical component model.',
        'criteria':{'discharge_scaled_threshold_V':60*24/195,'discharge_s_max':5,'analytic_wave_relative_error_max':.002,'off_bus_max_V':.01,'stuck_bus_min_V':20},
        'capacitance_assumption':'20uF +5% main,3x100n +5% modules; actual full MPN/DC rating/temperature pending',
        'resistance_assumption':'each200k+1%; disconnected modules remove own capacitors AND bleeders',
        'cases':cases,'exe_sha256':sha(EXE),'touch_criterion':'60V/5s is design-only, uncertified; does not establish touch safety'})
    rows=[]
    for name,c,r in cases:
        d=out/name;d.mkdir();discharge=bool(c)
        if discharge:
            circuit=f'C1 bus 0 {c} IC=24\nR1 bus 0 {r}\n';stop=6;step=.001;uic='uic'
        else:
            circuit=f'VIN src 0 24\nRSW src li {r}\nL1 li sw 1m\nD1 sw bus DTOP\n.model DTOP D(Is=1e-12 N=1 Rs=.01)\nC1 bus 0 1u\nRB bus 0 50k\nVGATE gate 0 0\n'
            stop=.02;step=.000001;uic=''
        deck=f'''Safety R1 low-voltage topology {name}
{circuit}
.options reltol=.0001 abstol=1n vntol=1u
.control
set noaskquit
set numdgt=15
set wr_singlescale
set wr_vecnames
tran {step} {stop} {uic}
wrdata waves.txt v(bus)
quit
.endc
.end
'''
        (d/'circuit.cir').write_text(deck,encoding='ascii');argv=[str(EXE),'-b','-o','ngspice.log','circuit.cir']
        p=subprocess.run(argv,cwd=d,capture_output=True,text=True,errors='replace',timeout=20)
        rows_data=[[float(x) for x in line.split()] for line in (d/'waves.txt').read_text().splitlines()[1:] if line.strip()]
        valid=p.returncode==0 and rows_data[-1][0]>=stop*(1-1e-9) and all(math.isfinite(x) for row in rows_data for x in row)
        row={'case':name,'argv':argv,'rc':p.returncode,'execution':'PASS' if valid else 'FAIL','end_s':rows_data[-1][0],'bus_final_V':rows_data[-1][1],'deck_sha256':sha(d/'circuit.cir')}
        if discharge:
            t60=r*c*math.log(195/60);first=next((t for t,v in rows_data if v<=60*24/195),None)
            err=max(abs(v-24*math.exp(-t/(r*c)))/24 for t,v in rows_data)
            row.update(analytic_t60_s=t60,scaled_measured_t60_s=first,max_normalized_wave_error=err,
                       topology_consistency='PASS' if err<=.002 else 'FAIL',
                       discharge_design_requirement='PASS' if first is not None and first<=5 else 'FAIL')
        else:row['topology_consistency']='PASS' if ((name.endswith('stuck_on') and row['bus_final_V']>=20) or (name.endswith('_off') and row['bus_final_V']<=.01)) else 'FAIL'
        dump(d/'result.json',row);rows.append(row)
    dump(out/'results.json',{'attempts':len(rows),'execution_pass':sum(r['execution']=='PASS' for r in rows),'cases':rows,'manufacturing':'HOLD'})
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
