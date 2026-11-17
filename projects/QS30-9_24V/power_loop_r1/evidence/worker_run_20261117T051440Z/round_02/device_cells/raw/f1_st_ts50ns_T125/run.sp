* F1 nonlinear switching: clamped inductive pulse, STP9NK50Z model
* Vbus 170 V, 150 uH, 25 us on-time, 6.5 V gate through 10 ohm, 1 mohm
* ST model stp9nk50z.lib, byte-identical (STP9NK50Z stands in for STP7N65M2)
.include stp9nk50z.lib
.temp 125
Vbus NVDDP 0 170
XQ NVSWP NVGP NVSSP STP9NK50Z
Rs NVSSP 0 1m
L2 NVSWP 0 150u IC=0
Vp NVPP 0 PWL(0 0 1u 0 1.05u 6.5 25u 6.5 25.05u 0 200u 0)
Rg NVPP NVGP 10
Rgs NVGP 0 10k
Vsense NSSP2 NVSSP 0
Rs2 NSSP2 0 1m
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.tran 5e-08 6e-05 0 uic

.control
run
wrdata out.dat v(NVSWP) i(Vsense) v(NVGP) v(NVDDP)
.endc
.end
