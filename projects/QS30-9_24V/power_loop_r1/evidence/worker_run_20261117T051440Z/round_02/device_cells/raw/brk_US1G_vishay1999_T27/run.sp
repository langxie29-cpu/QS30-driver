* reverse window -250 V .. 0 V
.include us1g_vishay1999.models
.model US1GD D
.temp 27
VA NVAP 0 0
D1 NVAP NVKP US1GD
VK NVKP 0 0
.dc VA -250 0 0.5

.control
run
wrdata out.dat i(VA)
.endc
.end
