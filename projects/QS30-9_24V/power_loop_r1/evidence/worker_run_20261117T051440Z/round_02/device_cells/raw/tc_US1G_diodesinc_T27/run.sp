* TC probe: Vf at 1 A vs TEMP (model self-consistency)
.include us1g_diodesinc.models
.model DI_US1G D
.temp 27
Vf VFP 0 2
Rf VFP NVAP 1
D1 NVAP 0 DI_US1G
.op

.control
run
print v(NVAP)
.endc
.end
