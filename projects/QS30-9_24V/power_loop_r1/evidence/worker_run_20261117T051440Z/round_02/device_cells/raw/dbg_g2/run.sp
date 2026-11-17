* g probe
.include stp9nk50z.lib
.temp 27
Vbus NVDDP 0 170
XQ NVSWP NVGP NVSSP STP9NK50Z
Rs NVSSP 0 1m
L2 NVSWP 0 150u IC=0
Vp NVPP 0 PULSE(0 6.5 1u 100n 100n 25u 100u)
Rg NVPP NVGP 10
Rgs NVGP 0 10k
VV 0 NVSSP 0
.options reltol=1e-4
.tran 100n 60u 0 uic

.control
run
wrdata out.dat v(NVGP) v(NVSWP) i(VV)
.endc
.end
