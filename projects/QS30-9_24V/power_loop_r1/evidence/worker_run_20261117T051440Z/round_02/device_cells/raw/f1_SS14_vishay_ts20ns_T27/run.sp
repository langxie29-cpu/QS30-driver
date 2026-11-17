* F1 diode turn-off / reverse recovery
.include ss14_vishay.models
.model DSS14 D
.temp 27
Vf VFP 0 10
Rf VFP NVFP 1
Lf NVFP NVAP 100u IC=1
D1 NVAP NVKP DSS14
Vr NVKP 0 PWL(0 0 2u 0 2.195u 195 8u 195 8.195u 0 12u 0)
Vsense NVKP2 NVKP 0
Rk NVKP2 0 1u
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.tran 2e-08 8e-06 0 uic

.control
run
wrdata out.dat i(Vf) v(NVAP,NVKP) v(NVKP)
.endc
.end
