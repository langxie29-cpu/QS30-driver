"""Real TI driver macro-model isolated low-voltage tests. Not a Boost simulation."""
from pathlib import Path
import hashlib,json,subprocess,re,math,sys,datetime,argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
EXE=ROOT/'tools/ngspice47/Spice64/bin/ngspice_con.exe'
SOURCE=ROOT/'projects/QS30-9_24V/sources/sprint06/UCC27511_unencrypted/unpacked/UCC27511_TRANS.LIB'
if not SOURCE.exists():SOURCE=HERE/'spice_r2/inhibited_2ns/driver.lib'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'spice_reproduction');parser.add_argument('--exe',type=Path,default=EXE);parser.add_argument('--aux',type=float,default=12)
    args=parser.parse_args();dest=args.output.resolve();exe=args.exe.resolve();dest.mkdir(exist_ok=False)
    version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,errors='replace')
    (dest/'version.txt').write_text(version.stdout+version.stderr,encoding='utf8')
    cases=[(kind,ns) for kind in ('inhibited','fault_trip','floating_inhibit','aux_loss') for ns in (2,1)]
    criteria={'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Original TI UCC27511 macro-model + linear gate capacitor at stated AUX12; no MOSFET/Miller, comparator, eFuse, physical watchdog, latch or high-voltage validation',
        'AUX12_V':args.aux,'temperature_C':27,
        'cases':cases,'source_url':'https://www.ti.com/lit/zip/slum488',
        'source_file':str(SOURCE.relative_to(ROOT)), 'source_sha256':sha(SOURCE),
        'exe_sha256':sha(exe),'python':sys.version,
        'criteria':{'end_s':20e-6,'inhibited_gate_max_V':0.55,'active_gate_min_V':10,
                    'post_trip_gate_max_V':0.55,'trip_deadline_s_after_command':300e-9,
                    'half_step_trip_time_difference_s':20e-9},
        'model_limits':'Macro-model is not a guaranteed propagation/temperature/partial-power bound. UIC used for driver unit only; not an HV startup.'}
    dump(dest/'preregister.json',criteria)
    rows=[]
    for kind,ns in cases:
        d=dest/f'{kind}_{ns}ns';d.mkdir()
        (d/'driver.lib').write_bytes(SOURCE.read_bytes())
        (d/'.spiceinit').write_text('set ngbehavior=ps\n',encoding='ascii')
        vdd='PWL(0 0 1u 12 11.999u 12 12u 0 20u 0)' if kind=='aux_loss' else 'PWL(0 0 1u 12 20u 12)'
        vdd=vdd.replace(' 12 ',f' {args.aux} ').replace(' 12)',f' {args.aux})')
        if kind=='fault_trip':inhibit='VIM inm 0 PWL(0 3.3 4.999u 3.3 5u 0 11.999u 0 12u 3.3 20u 3.3)'
        elif kind=='aux_loss':inhibit='VIM inm 0 PWL(0 3.3 4.999u 3.3 5u 0 20u 0)'
        elif kind=='inhibited':inhibit='VIM inm 0 3.3'
        else:inhibit='RDEFAULT vdd inm 47k'
        deck=f'''Safety R1 isolated real TI driver {kind}
.include driver.lib
VDD vdd 0 {vdd}
VIN inp 0 PWL(0 0 2u 0 2.001u 3.3 20u 3.3)
{inhibit}
XD inp inm 0 vdd dh dl UCC27511_TRANS
RGON dh gate 10
RGOFF dl gate 2.2
RGS gate 0 10k
CG gate 0 5.333333n
.options reltol=.001 abstol=1n vntol=1u method=gear itl4=200
.control
set noaskquit
set wr_singlescale
set wr_vecnames
set numdgt=15
tran {ns}n 20u 0 {ns}n uic
wrdata waves.txt v(vdd) v(inp) v(inm) v(gate)
quit
.endc
.end
'''
        (d/'circuit.cir').write_text(deck,encoding='ascii')
        argv=[str(exe),'-b','-o','ngspice.log','circuit.cir']
        r={'name':d.name,'kind':kind,'step_ns':ns,'argv':argv,'timeout_s':30,'model_sha256':sha(d/'driver.lib'),'deck_sha256':sha(d/'circuit.cir')}
        try:
            p=subprocess.run(argv,cwd=d,capture_output=True,text=True,errors='replace',timeout=30)
            r.update(rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
            log=(d/'ngspice.log').read_text(errors='replace')
            data=[[float(x) for x in line.split()] for line in (d/'waves.txt').read_text().splitlines()[1:] if line.strip()]
            valid=p.returncode==0 and data[-1][0]>=20e-6*(1-1e-8) and all(math.isfinite(x) for row in data for x in row) and all(data[i][0]<data[i+1][0] for i in range(len(data)-1)) and not re.search('aborted|time step too small|fatal|error:',log,re.I)
            r.update(execution='PASS' if valid else 'FAIL',electrical='INCONCLUSIVE',samples=len(data),end_s=data[-1][0])
            if valid:
                if kind in ('inhibited','floating_inhibit'):
                    peak=max(row[4] for row in data if row[0]>=1e-6)
                    r.update(inhibited_gate_max_V=peak,electrical='PASS' if peak<=.55 else 'FAIL')
                else:
                    active=min(row[4] for row in data if 8e-6<=row[0]<=11e-6)
                    post=max(row[4] for row in data if row[0]>=12.3e-6)
                    crosses=[row[0] for row in data if row[0]>=12e-6 and row[4]<=.55]
                    delay=crosses[0]-12e-6 if crosses else None
                    r.update(active_gate_min_V=active,post_trip_gate_max_V=post,trip_delay_s=delay,
                             electrical='PASS' if active>=10 and post<=.55 and delay is not None and delay<=300e-9 else 'FAIL')
        except Exception as e:r.update(execution='FAIL',electrical='INCONCLUSIVE',error=repr(e))
        dump(d/'result.json',r);rows.append(r);print(json.dumps(r),flush=True)
    comparisons=[]
    for kind in ('fault_trip','aux_loss'):
        pair=[r for r in rows if r['kind']==kind]
        delta=abs(pair[0]['trip_delay_s']-pair[1]['trip_delay_s']) if all('trip_delay_s' in r and r['trip_delay_s'] is not None for r in pair) else None
        comparisons.append({'kind':kind,'trip_time_delta_s':delta,'result':'PASS' if delta is not None and delta<=20e-9 else 'INCONCLUSIVE'})
    dump(dest/'results.json',{'attempts':len(rows),'execution_pass':sum(r['execution']=='PASS' for r in rows),'electrical_pass':sum(r.get('electrical')=='PASS' for r in rows),'electrical_fail':sum(r.get('electrical')=='FAIL' for r in rows),'electrical_inconclusive':sum(r.get('electrical')=='INCONCLUSIVE' for r in rows),'cases':rows,'half_step_comparisons':comparisons,'manufacturing':'HOLD','24V_07':'NOT_PASSED','24V_08':'NOT_ENTERED','24V_09':'NOT_PASSED'})

if __name__=='__main__':main()
