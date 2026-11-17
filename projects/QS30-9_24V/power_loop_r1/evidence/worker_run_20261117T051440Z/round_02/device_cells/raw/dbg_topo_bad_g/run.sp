* topo
.include stp9nk50z.lib
VG g 0 10
VDD an_d 0 5
VV 0 an_s 0
XQ an_d g an_s STP9NK50Z
.op

.control
run
op
showmod
print i(VDD)
.endc
.end
