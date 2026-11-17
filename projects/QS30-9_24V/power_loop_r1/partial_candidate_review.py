"""Read a timed-out native double raw; never pass off its partial data as completion."""
from pathlib import Path
import json,re,sys
import numpy as np
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic'/sys.argv[1]
 p=d/'circuit.raw'
 with p.open('rb') as f:head=f.read(10000)
 enc='utf-16-le' if head.startswith(b'T\0') else 'utf8'
 marker='Binary:\n'.encode(enc);pos=head.find(marker)
 if pos<0:marker='Binary:\r\n'.encode(enc);pos=head.find(marker)
 s=head[:pos].decode(enc);offset=pos+len(marker)
 n=int(re.search(r'No\. Variables:\s*(\d+)',s)[1]);declared=int(re.search(r'No\. Points:\s*(\d+)',s)[1])
 assert 'double' in re.search(r'Flags:\s*([^\r\n]+)',s)[1]
 names=[l.split()[1].lower() for l in s.rsplit('Variables:',1)[1].splitlines() if l.strip()]
 actual=(p.stat().st_size-offset)//(8*n);count=min(declared,actual)
 a=np.memmap(p,dtype='<f8',mode='r',offset=offset,shape=(count,n));c={name:a[:,i] for i,name in enumerate(names)}
 il=c['i(lpower)'];vg=c['v(gate)']-c['v(src)']
 r=dict(classification='INCONCLUSIVE',execution='EXECUTION_FAIL_TIMEOUT',scope='Only partial raw diagnostics; no full-stop/steady/startup qualification',
      original_raw_bytes=p.stat().st_size,declared_points=declared,complete_records_on_disk=actual,reviewed_records=count,
      trailing_unreviewed_bytes=p.stat().st_size-offset-count*n*8,
      last_reviewed_time_s=float(c['time'][-1]),required_endpoint_s=.06,
      VOUT_initial_V=float(c['v(hv)'][0]),VOUT_partial_peak_V=float(c['v(hv)'].max()),VOUT_last_V=float(c['v(hv)'][-1]),
      IL_partial_peak_A=float(il.max()),IL_partial_min_A=float(il.min()),
      VGS_partial_min_V=float(vg.min()),VGS_partial_max_V=float(vg.max()),
      finite=bool(np.isfinite(a).all()),time_strictly_monotonic=bool((np.diff(c['time'])>0).all()))
 (d/'partial_review.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r,indent=2))
