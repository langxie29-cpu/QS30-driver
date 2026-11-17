* F1 v9 renamed nodes
.include stp9nk50z.lib
.temp 125
Vbus NVDDP 0 170
XQ NVSWP NVGP NVSSP STP9NK50Z
Rs NVSSP 0 1m
L2 NVSWP 0 150u IC=0
Vp NVPP 0 PWL(0 0 1u 0 1.05u 6.5 25u 6.5)
Rg NVPP NVGP 10
Rgs NVGP 0 10k
VV 0 NVSSP 0
.options reltol=1e-4
.tran 200n 200u 190u uic

.control
run
print i(Vbus) v(nvpp) v(nvswp)
.endc
.end
