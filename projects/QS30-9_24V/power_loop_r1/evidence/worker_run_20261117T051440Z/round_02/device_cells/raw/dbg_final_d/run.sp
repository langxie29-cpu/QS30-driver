* F1 diode turn-off / reverse recovery
.include us1g_vishay1999.models
.temp 27
Vf VFP 0 10
Rf VFP NVFP 1
Lf NVFP NVAP 100u IC=1
D1 NVAP NVKP US1GD
Vr NVKP 0 PWL(0 0 2u 0 2.195u 195 8u 195 8.195u 0 12u 0)
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.tran 5e-09 1.2e-05 0 uic

.control
run
wrdata out.dat i(Vf) v(NVKP) v(NVAP,NVKP)
.endc
.end
