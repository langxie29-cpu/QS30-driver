"""Validate binary decoder against an actual solver's RC and ASCII trace."""
from pathlib import Path
import subprocess,json,math,sys
from local_probe import HERE,LT
from waveform_review import read_native,read_ascii,interp
if __name__=='__main__':
 d=HERE/'evidence'/('toolchain_binary_uncompressed' if '--uncompressed' in sys.argv else 'toolchain_binary');d.mkdir(parents=True,exist_ok=False)
 src=HERE/'evidence/toolchain_smoke/ltspice/circuit.cir'
 s=src.read_text().replace('.tran','.options numdgt=15'+(' plotwinsize=0' if '--uncompressed' in sys.argv else '')+'\n.tran')
 (d/'circuit.cir').write_text(s,encoding='ascii',newline='\n')
 cmd=[str(LT),'-b',str((d/'circuit.cir').resolve())]
 p=subprocess.run(cmd,cwd=d,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 (d/'stdout.bin').write_bytes(p.stdout);(d/'stderr.bin').write_bytes(p.stderr)
 a=read_ascii(src.with_suffix('.raw'));b=read_native(d/'circuit.raw')
 diff=max(abs(y-interp(a['time'],a['v(out)'],t)) for t,y in zip(b['time'],b['v(out)']))
 r=dict(argv=cmd,rc=p.returncode,endpoint_V=b['v(out)'][-1],max_difference_from_actual_ASCII_V=diff,
  classification='LIMITED_PASS' if p.returncode==0 and diff<1e-12 else 'EXECUTION_FAIL',scope='Binary decoder only')
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(r,indent=2))
