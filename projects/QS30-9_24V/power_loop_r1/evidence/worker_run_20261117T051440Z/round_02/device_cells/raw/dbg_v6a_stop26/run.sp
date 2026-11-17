* B F1 v6
.include stp9nk50z.lib
.temp 27
Vbus b 0 170
XQ d g s STP9NK50Z
Rs s 0 1m
L2 d 0 150u IC=0
Rg p g 10
Rgs g 0 10k
VV 0 s 0
.options reltol=1e-4
Vp p 0 PWL(0 0 1u 0 1.05u 6.5 25u 6.5)
.tran 50n 26u 0 uic

.control
run
wrdata out.dat v(d) i(VV) v(g)
.endc
.end
