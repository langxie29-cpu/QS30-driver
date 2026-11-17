"""One bounded solver-method cross-check; no model/tolerance retuning."""
import json
from candidate_diagnostic import HERE,build,run,dump
if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic/nominal_24V_trap_200ns'
 build(d,24,2e-7,.06)
 p=d/'circuit.cir';p.write_text(p.read_text().replace('method=gear','method=trap'),encoding='ascii',newline='\n')
 j=json.loads((d/'preregister.json').read_text());j.update(method='trap',comparison='Same60ms endpoint,200ns maxstep,120s wall cap, model bytes/topology/tolerances unchanged. Test whether Gear-specific tiny steps explain previous timeout; no further blind reruns planned.')
 dump(d/'preregister.json',j)
 print(json.dumps(run(d,HERE/'evidence/native_reference_encoding_fix/metrics.json',binary=True),indent=2))
