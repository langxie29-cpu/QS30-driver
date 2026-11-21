* Common input, output and load fixture. System eFuse/OVP/branch logic excluded.
* 4.30 V pin mode uses zero nominal series drop (1 micro-ohm numeric floor).
V_IN supply 0 PWL(0 0 100u 0 300u {VIN})
R_PATH supply vin {RPATH}
C_IN vin 0 100u ic=0
B_LV vin 0 I={PLV/max(v(vin),3)*(0.5+0.5*tanh(15*(v(vin)-3.1)))}
B_TUBES hv 0 I={IHV*min(1,max(0,(v(hv)-120)/15))}
R_BLEED1 hv 0 496k
R_BLEED2 hv 0 496k
R_OVP_EQ hv 0 2.0093Meg
R_RESID_EQ hv 0 1.8542Meg
V_CAP hv cb 0
R_ESR cb hvc 100m
C_HV hvc 0 {CEFF} ic=0
B_VDS vds 0 V={v(sw,source)}
B_VGS vgs 0 V={v(gate,source)}
B_PWR p_in 0 V={-v(supply)*i(V_IN)}
B_HV p_hv 0 V={v(hv)*(IHV*min(1,max(0,(v(hv)-120)/15))+2*v(hv)/496k+v(hv)/2.0093Meg+v(hv)/1.8542Meg+v(hv)/(RFB_SUM))}
B_SW p_sw 0 V={v(vds)*i(VQ)}
.save v(hv) v(hvc) v(vin) v(vds) v(vgs) v(fb) v(comp) v(p_in) v(p_hv) v(p_sw) i(LPOWER) i(VQ) i(V_CAP) i(V_IN)
