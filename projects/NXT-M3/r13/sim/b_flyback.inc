* B: LM3488 nonisolated flyback; TI controller, reference-provided Infineon switch.
.include LM3488_TRANS.LIB
.include irfh7185pbf.spi
.include ES3J.lib
.include SMDJxxxCA.lib
R_PRI vin primary 25m
LPOWER primary drain {LMAG} ic=0
LSEC 0 secondary {LMAG*RATIO*RATIO} ic=0
K_XF LPOWER LSEC {COUPLING}
R_SEC secondary diode_a 1.5
D_HV diode_a hv ES3J
VQ drain sw 0
X_Q sw gate source irfh7185pbf
X_CLAMP source drain SMDJ70CA
R_SENSE source 0 {SHUNT}
C_SENSE source 0 10n
R_GATE drv gate 0.1
R_FA fa 0 {RFA}
R_FB1 hv fb 1.2Meg
R_FB2 fb 0 8674.0
C_COMP comp comp_r 22n
R_COMP comp_r 0 4.7k
X_CTL 0 comp drv fa fb source 0 vin LM3488_TRANS PARAMS: SS=0
