"""One pre-registered resource-control experiment, not an unlimited retry loop."""
import json
from candidate_diagnostic import HERE,build,run,dump
if __name__=='__main__':
 d=HERE/'evidence/candidate_diagnostic/nominal_24V_gear_resource600'
 build(d,24,2e-7,.06)
 j=json.loads((d/'preregister.json').read_text());j.update(timeout_s=600,
  hypothesis='Separate finite wall-time limit from solver failure: BOTH120s attempts show finite monotonic raw to19.75/21.79ms, not a fatal solver endpoint. Gear original deck unchanged, only wall budget differs.',
  resource_preregister='Exactly ONE additional600s run, same60ms stop, same200ns maxstep, same tolerances/models/topology. Original120s failures remain untouched. No additional model/scheduler calls. No further startup retries in this initial integration.',
  decision='Principal Codex accepts one resource-control experiment; estimated 60ms/19.75ms*120s~365s based on measured progress, not a success prediction.')
 dump(d/'preregister.json',j)
 print(json.dumps(run(d,HERE/'evidence/native_reference_encoding_fix/metrics.json',binary=True,timeout_s=600),indent=2))
