* A pins via nmos() core
.temp 27
VG g 0 10
VS s 0 0
VD d 0 0
MN d g s s MM
.model MM NMOS (LEVEL=3 VTO=4.862 PHI=0.839 IS=0.1E-12 JS=0 THETA=0.236 KP=7.026)
.dc VD 0 5 0.01

.control
run
wrdata out.dat v(d) i(VD)
.endc
.end
