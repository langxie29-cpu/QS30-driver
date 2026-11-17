"""Cross-check formats using the IDENTICAL uncompressed deck and solver settings."""
import subprocess,json,shutil
from local_probe import HERE,LT
from waveform_review import read_native,read_ascii
if __name__=='__main__':
 d=HERE/'evidence/toolchain_binary_identical_ascii';d.mkdir(parents=True,exist_ok=False)
 src=HERE/'evidence/toolchain_binary_uncompressed/circuit.cir'
 shutil.copy2(src,d/'circuit.cir')
 cmd=[str(LT),'-b','-ascii',str((d/'circuit.cir').resolve())]
 p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 a=read_ascii(d/'circuit.raw');b=read_native(src.with_suffix('.raw'))
 same=len(a['time'])==len(b['time'])
 dt=max(abs(x-y) for x,y in zip(a['time'],b['time'])) if same else None
 dv=max(abs(x-y) for x,y in zip(a['v(out)'],b['v(out)'])) if same else None
 r=dict(argv=cmd,rc=p.returncode,samples_same=same,max_time_difference_s=dt,max_voltage_difference_V=dv,
     preregistered_test='Identical deck/settings, only raw output format changes: time and voltage difference<=1e-14',
     classification='LIMITED_PASS' if same and dt<=1e-14 and dv<=1e-14 else 'EXECUTION_FAIL',
     prior_failures='Compressed-time rejection and6.24e-8 interpolation difference against different numdgt deck remain preserved; neither retroactively PASS')
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r,indent=2))
