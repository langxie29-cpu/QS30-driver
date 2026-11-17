"""Bounded, real-controller exploratory cold-start fixture; never hardware approval.

Builds immutable per-case directories. Running requires a reviewed native reference
path supplied by the principal engineer. Original manufacturer model bytes unchanged.
"""
from pathlib import Path
import argparse, shutil, json, hashlib, subprocess, os, time, re
from local_probe import OLD, LT
HERE=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8',newline='\n')

def build(out,vin,step,stop):
    out.mkdir(parents=True,exist_ok=False)
    src=OLD/'sim/s06c_current_cell_v3/ST_AUX12_1ns'
    for name in ('controller.sub','st.lib','diode.lib','ss14.lib'):
        shutil.copy2(src/name,out/name)
    # Physical topology from the candidate, no external SS/VC command and no HV source.
    # A 1ms external input ramp is an explicit fixture condition, not eFuse validation.
    net=f'''QS30 exploratory cold start, genuine controller, initial COUT=0
.include controller.sub
.include st.lib
.include diode.lib
.include ss14.lib
VINPUT vin 0 PWL(0 0 1m {vin})
RINPUT vin in .1
LPOWER in drain 150u Rser=.16
XQ drain gate src STP9NK50Z
RSRC src 0 .062
RF src sense 10
CF sense 0 1n
RG out gate 22
RGS gate src 10k
XNEG src neg ss14
RNEG neg gate 2
DREC drain hv US1G
RSNUB drain sn 330
CSNUB sn hv 100p
COUT hv 0 20.3u Rser=.1 IC=0
RLOAD hv 0 5200
RB1A hv b1 90.9k
RB1B b1 0 90.9k
RB2A hv b2 90.9k
RB2B b2 0 90.9k
RFB1 hv fbmid 100k
RFB2 fbmid fb 100k
RFB3 fb 0 1900.6
VAUX aux 0 PWL(0 0 1m 12)
RAUX aux intvcc .1
CINT intvcc 0 4.7u IC=0
REN1 in en 200k
REN2 en 0 12.8k
CSS ss 0 100n IC=0
RCOMP vc comp 22k
CCOMP comp 0 6.8n IC=0
CHF vc 0 100p IC=0
RRT rt 0 140k
XU vc fb ss rt 0 sense out intvcc en intvcc 0 LT3757A
.temp 25
.options tnom=25 reltol=.001 abstol=1n vntol=1u method=gear plotwinsize=0 numdgt=15
.tran {step} {stop} 0 {step} uic
.save V(hv) V(gate) V(src) V(sense) V(vc) V(ss) V(drain) I(LPOWER) V(in) V(en) V(intvcc) I(DREC)
.end
'''
    (out/'circuit.cir').write_text(net,encoding='ascii',newline='\n')
    dump(out/'preregister.json',dict(scope='Exploratory 25C linear-magnetics cold-start diagnostic, NOT 24V-07/08 release or M2 signoff',
        vin_V=vin,source_ramp_s=.001,source_series_ohm=.1,maxstep_s=step,stop_s=stop,timeout_s=120,
        model_hashes={p.name:sha(p) for p in out.glob('*.lib')}|{'controller.sub':sha(out/'controller.sub')},
        supply='AUX12 is an external explicit fixture rail, not a qualified AUX converter model',
        load='5200ohm + actual two bleeder strings + LT feedback; about6.02W at170V covers revised5.90042W budget as a resistive capacity screen, not actual 9-tube negative resistance/load steps',
        startup='UIC with all capacitors zero, no ideal HV source, no forced PWM, no forced SS/VC; 1ms input/AUX ramp',
        limitations=['150uH/DCR.16 is a linear25C candidate; hot L(I,T), saturation, core losses missing',
            '2ohm SS14 clamp branch is an explicitly isolated damping hypothesis; not inherited gate qualification',
            'Gate high-frequency convergence and current-limit delay remain unqualified',
            'Feedback/compensation values are research hypotheses, not design release'],
        fixed_acceptance=dict(mean_V=[164.9,175.1],ripple_Vpp=1,normal_peak_V=180,startup_s=1,recovery_s=.1,fault_peak_V=195)))

def run(out,reference,binary=False,timeout_s=120):
    ref=Path(reference).resolve()
    if not ref.is_file(): raise ValueError('Reviewed native reference evidence absent')
    env=dict(os.environ)
    for key,sub in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
        env[key]=str((out/sub).resolve()); Path(env[key]).mkdir()
    argv=[str(LT),'-b']+([] if binary else ['-ascii'])+[str((out/'circuit.cir').resolve())]
    start=time.monotonic()
    r=dict(argv=argv,reference_evidence=str(ref),reference_sha256=sha(ref),simulator_sha256=sha(LT),timeout_s=timeout_s)
    try:
        p=subprocess.run(argv,cwd=out,env=env,capture_output=True,timeout=timeout_s,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(rc=p.returncode,elapsed_s=time.monotonic()-start)
        (out/'stdout.bin').write_bytes(p.stdout);(out/'stderr.bin').write_bytes(p.stderr)
    except subprocess.TimeoutExpired as e:
        r.update(rc=None,elapsed_s=time.monotonic()-start,classification='EXECUTION_FAIL',reason=str(timeout_s)+'s wall-time timeout; not proof of electrical failure')
        (out/'stdout.bin').write_bytes(e.stdout or b'');(out/'stderr.bin').write_bytes(e.stderr or b'')
    dump(out/'command.json',r)
    return r

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('name');a.add_argument('--vin',type=float,default=24);a.add_argument('--step',type=float,default=2e-7);a.add_argument('--stop',type=float,default=.06);a.add_argument('--run-with-reviewed-reference');a.add_argument('--binary',action='store_true')
    args=a.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.name): raise ValueError('Invalid case name')
    out=HERE/'evidence/candidate_diagnostic'/args.name
    build(out,args.vin,args.step,args.stop)
    if args.run_with_reviewed_reference:print(json.dumps(run(out,args.run_with_reviewed_reference,args.binary),indent=2))
    else:print('BUILT_ONLY, no simulation:',out)
