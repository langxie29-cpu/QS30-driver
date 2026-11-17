* probe
.include us1g_vishay1999.models
.model US1GD D
.temp 27
Vf VFP 0 PWL(0 0 0.5u 0 0.6u 10 6u 10)
Rf VFP NVFP 1
Lf NVFP NVAP 100u IC=1
D1 NVAP NVKP US1GD
Vr NVKP 0 0
.options reltol=1e-4
.tran 2e-9 6e-6 0 uic

.control
run
wrdata out.dat i(Vf) v(NVAP,NVKP) v(NVKP)
.endc
.end
