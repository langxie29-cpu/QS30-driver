* F1 v8 renamed nodes
.include stp9nk50z.lib
.temp 125
Vbus VDD 0 170
XQ VSW VG VSS STP9NK50Z
Rs VSS 0 1m
L2 VSW 0 150u IC=0
Vp VP 0 PWL(0 0 1u 0 1.05u 6.5 25u 6.5 25.05u 0 200u 0)
Rg VP VG 10
Rgs VG 0 10k
VV 0 VSS 0
.options reltol=1e-4
.tran 200n 200u 190u uic

.control
run
wrdata out.dat v(VSW) i(VV) v(VG)
.endc
.end
