* topo
.include stp9nk50z.lib
VG an_g 0 10
VDD an_d 0 5
VV 0 s 0
XQ an_d an_g s STP9NK50Z
.op

.control
run
op
showmod
print i(VDD)
.endc
.end
