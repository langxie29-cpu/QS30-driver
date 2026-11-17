* F1 nonlinear switching: clamped inductive double pulse, STP9NK50Z model
* ST model stp9nk50z.lib byte-identical (STP9NK50Z; stands in for STP7N65M2)
.include stp9nk50z.lib
.temp 27
Vbus b 0 170
Lbus b d 1u
XQ d g s STP9NK50Z
Rs s 0 1m
L2 d2 0 150u
Ds d2 d DUF
* gate: 6.5 V source through 10 ohm (LT3757A INTVCC typ), 10 ohm pull-down
Vp p 0 PULSE(0 6.5 1u 100n 100n 25u 100u)
Rg p g 10
Rgs g 0 10k
.model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)
.options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15
.options itl4=500 maxord=2 gmin=1e-12 gminsteps=0 srcsteps=0
.tran 1e-07 6e-05 5e-05 uic

wrdata out.dat v(d) i(Lbus)
quit
