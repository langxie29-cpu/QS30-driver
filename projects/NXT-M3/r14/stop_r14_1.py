"""Run a 0–5 V logic-only fixture for the R14.1 interlock chain."""
import json
from pathlib import Path

import simulate_faults as spice

OUT = Path(__file__).resolve().parent / "evidence/r14_1/proxy"
CASES = ("open_reclose_held_arm", "reset_and_residual", "other_fault", "nc_bridge", "u11_stuck")


def fixture(case):
    # A physical button is held from 20 to 90 ms while the stop loop opens and recloses.
    stop = "0 3.3 0.039999 3.3 0.04 0 0.064999 0 0.065 3.3"
    reset = "0 3.3"
    residual = "0 3.3"
    fault = "0 0"
    if case == "nc_bridge":
        stop = "0 3.3"
    if case == "reset_and_residual":
        stop = "0 3.3"
        reset = "0 3.3 0.039999 3.3 0.04 0 0.064999 0 0.065 3.3"
        residual = "0 3.3 0.039999 3.3 0.04 0 0.139999 0 0.14 3.3"
    if case == "other_fault":
        stop = "0 3.3"
        fault = "0 0 0.039999 0 0.04 3.3 0.064999 3.3 0.065 0"
    return f"""R14.1 low-voltage functional interlock proxy, {case}
VDD vdd 0 3.3
VSUP in 0 5
VMCU mcu_en 0 PWL({reset})
VLOOP contact 0 PWL({stop})
VFAULT ovp_ocp_wdo 0 PWL({fault})
VRES res_ok 0 PWL({residual})
VARM strobe 0 PWL(0 0 0.019999 0 0.02 3.3 0.089999 3.3 0.09 0
+ 0.109999 0 0.11 3.3 0.124999 3.3 0.125 0 0.159999 0 0.16 3.3 0.179999 3.3 0.18 0)
SNC loop 0 contact 0 SW_CTL
R509 loop stop_gate 220
R510 vdd stop_gate 3300
C64 stop_gate 0 1n
BDRIVE q35_drive 0 V=(v(stop_gate)>1.6 ? 3.3 : 0)
SQ35 fault_n 0 q35_drive 0 SW_CTL
SOTHER fault_n 0 ovp_ocp_wdo 0 SW_CTL
R27 vdd fault_n 10k
BU9 latch_clr_n 0 V=(v(fault_n)>2 && v(mcu_en)>2 ? 3.3 : 0)
BCLEAR clear 0 V=(v(latch_clr_n)<1 ? 3.3 : 0)
SCLEAR armed 0 clear 0 SW_CTL
CEDGE strobe edge 10n
REDGE edge 0 10k
BDATA sample_data 0 V=(v(res_ok)>2 && v(latch_clr_n)>2 ? 3.3 : 0)
SCLK sample_data armed edge 0 SW_CLK
CQ armed 0 1n
RQ armed 0 1T
R26 ready_latch 0 47k
BREPL ready_latch 0 V=(v(armed)>2 ? 3.3 : 0)
S11 in feed {"in" if case == "u11_stuck" else "ready_latch"} 0 SW_EF
C28 feed 0 22u
R45 feed 0 10k
RDUMMY feed 0 1k
VBIAS bias_ok 0 3.3
VHV_READY hv_ready 0 3.3
VDIGITS digits_req 0 3.3
BU15 pwm_permit 0 V=(v(ready_latch)>2 && v(bias_ok)>2 ? 3.3 : 0)
BU19 drive_ok 0 V=(v(pwm_permit)>2 && v(hv_ready)>2 ? 3.3 : 0)
BU10 oe_sink 0 V=(v(drive_ok)>2 && v(digits_req)>2 ? 3.3 : 0)
SQ31 hc_oe_n 0 oe_sink 0 SW_CTL
R24 vdd hc_oe_n 10k
.model SW_CTL SW(Ron=1 Roff=1T Vt=1.2 Vh=.02)
.model SW_CLK SW(Ron=100 Roff=1T Vt=1.3 Vh=.04)
.model SW_EF SW(Ron=.028 Roff=1T Vt=1.2 Vh=.02)
.tran 50u .24 0 50u
.save v(contact) v(strobe) v(stop_gate) v(fault_n) v(latch_clr_n) v(mcu_en)
+ v(res_ok) v(armed) v(ready_latch) v(pwm_permit) v(drive_ok) v(oe_sink) v(hc_oe_n) v(feed)
.end
"""


def measure(case, rows):
    times = (.030,.045,.070,.105,.120,.150,.170,.235)
    stages = {str(t):min(rows,key=lambda r:abs(r["time"]-t)) for t in times}
    assert stages["0.03"]["v(armed)"]>2 and stages["0.03"]["v(hc_oe_n)"]<.2
    assert stages["0.07"]["v(strobe)"]>2
    if case == "nc_bridge":
        assert stages["0.045"]["v(armed)"]>2 and stages["0.07"]["v(hc_oe_n)"]<.2
    else:
        for t in ("0.045","0.07","0.105"):
            assert stages[t]["v(armed)"]<.2 and stages[t]["v(hc_oe_n)"]>2,(case,t)
        assert stages["0.045"]["v(latch_clr_n)"]<.2
        assert stages["0.07"]["v(latch_clr_n)"]>2
        assert (stages["0.105"]["v(feed)"]>4.5)==(case=="u11_stuck")
        if case=="reset_and_residual":
            assert stages["0.12"]["v(armed)"]<.2 and stages["0.15"]["v(armed)"]<.2
        else:
            assert stages["0.12"]["v(armed)"]>2
    assert stages["0.17"]["v(armed)"]>2 and stages["0.17"]["v(hc_oe_n)"]<.2
    return {"assertions":"satisfied by low-voltage behavioral fixture","v_at_s":stages}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    spice.OUT=OUT
    measurements = {name:measure(name,spice.run_case(name,fixture(name))) for name in CASES}
    (OUT/"measurements.json").write_text(json.dumps(measurements,indent=2)+"\n",encoding="utf-8")
    print(f"{len(measurements)} low-voltage fixtures met assertions")


if __name__=="__main__":
    main()
