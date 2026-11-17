* TC probe: model self-consistency only (ID at VGS=10 V, VDS=1 V)
* ST model stp9nk50z.lib, byte-identical (STP9NK50Z stands in for STP7N65M2)
.include stp9nk50z.lib
.temp 150
VG NG 0 10
XQ ND NG NSN STP9NK50Z
VD ND 0 1
VS NSN 0 0
.op

.control
run
print i(VD)
.endc
.end
