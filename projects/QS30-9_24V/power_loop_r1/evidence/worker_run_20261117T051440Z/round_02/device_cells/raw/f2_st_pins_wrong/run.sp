* F2 negative control: pin order deliberately WRONG (2=D 1=G 3=S)
* ST model stp9nk50z.lib, byte-identical (STP9NK50Z stands in for STP7N65M2)
.include stp9nk50z.lib
.temp 27
VG g 0 10
VS s 0 0
XQ g d s STP9NK50Z
VD d 0 0
.dc VD 0 5 0.01

.control
run
wrdata out.dat v(d) i(VD) 1.5@1
.endc
.end
