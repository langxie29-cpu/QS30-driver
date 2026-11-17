* F1 diode turn-off: 1 A forward into 10 uH, then 0 -> 195 V in 195 ns
.include ss14_vishay.models
.temp 27
Vf VFP 0 10
Rf NVFP VFP 10
Lf NVFP NVAP 10u IC=1m
X1 NVAP NVKP DCAND
Vr NVKP 0 PWL(0 0 10u 0 10.195u 195 50u 195 50.195u 0 100u 0)
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.tran 1e-08 0.0001 9.2e-05 uic

.control
run
wrdata out.dat i(Vf) v(NVAP,NVKP) v(NVKP)
.endc
.end
