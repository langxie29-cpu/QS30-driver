* TC probe: Vf at 1 A vs TEMP (model self-consistency)
.include ss14_vishay.models
.model DSS14 D
.temp 27
Vf VFP 0 2
Rf VFP NVAP 1
D1 NVAP 0 DSS14
.op

.control
run
print v(NVAP)
.endc
.end
