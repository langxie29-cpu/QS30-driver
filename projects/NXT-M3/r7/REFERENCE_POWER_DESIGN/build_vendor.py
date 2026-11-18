"""Build R7 vendor-comparator/driver and alternate-controller switching decks."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "UNIFIED_POWER_MODEL"))
from build import unified, BASE


def vendor_p1(vin, display, hold, pass_kind="ohmic", stop="60m", bias_loss=False, load_release=False):
    deck = unified(vin, display, hold, pass_kind, False, "350n")
    deck = deck.replace(".include models/ss14.lib", """.include models/ss14.lib
.include TPS3700_TRANS.LIB
.include UCC27511_TRANS.LIB""")
    deck = re.sub(r"Bpermit permit.*?Vpasssense", """\
Vbias vdd 0 PWL(0 0 .15m 3.3)
Bpermit permit 0 V=if(V(latch)>1.65,0,V(arm))
Vpasssense""", deck, flags=re.S)
    deck = deck.replace("max(0,V(aux)*I(Rg))", "max(0,V(aux)*I(Vauxmeter))")
    deck = deck.replace("Raux aux_source aux 1", "Raux aux_source aux_feed 1\nVauxmeter aux_feed aux 0")
    deck = re.sub(r"BauxPermit.*?SauxStop en 0 aux_permit 0 pass\n", "", deck, flags=re.S)
    deck = re.sub(
        r"Bdrv drv.*?\.model GFAST[^\n]+\n", """\
Xdriver pwm drv_fault 0 aux drive_hi drive_lo UCC27511_TRANS
Rg drive_hi gate 22
Roff drive_lo gate 10
""", deck, flags=re.S)
    deck = re.sub(r"\* Diagnostic ideal comparator.*?Rhold latch 0 10Gig\n", """\
* Vendor U6 and U5, proxy U7 latch and manual ARM/POR. U8 and TPS26600 timing omitted.
BdrvFault drv_fault 0 V=if(V(latch)>1.65,3.3,0)
Xcmp vdd aux_ok ov en pre_n 0 TPS3700_TRANS
Rpull vdd pre_n 10k
Bset set 0 V=if(V(reset)>.5,0,if(V(vdd)>2.7,if(V(pre_n)<.8,1,if(V(latch)>1.65,1,0)),1))
Sset vdd latch set 0 slatch
.model slatch SW(Ron=60 Roff=1T Vt=.5 Vh=.1)
Clatch latch 0 20p
Rhold latch 0 100T
Vreset arm_edge 0 PWL(0 0 1m 0 1.001m 1 1.03m 1 1.031m 0)
Breset reset 0 V=if(V(pre_n)>2,V(arm_edge),0)
Sreset latch 0 reset 0 slatch
""", deck, flags=re.S)
    deck = deck.replace("Sshdn en 0 latch 0 pass", "Sshdn en 0 latch 0 slatch")
    deck = deck.replace("0.060", stop)
    deck = deck.replace("I(Vpasssense) V(aux)", "I(Vpasssense) V(pre_n) V(aux)")
    if bias_loss:
        deck = deck.replace("Btmr aux_source 0 V=12*", "Vbiasavail biasavail 0 PWL(0 1 32m 1 32.01m 0)\nBtmr aux_source 0 V=12*V(biasavail)*")
        deck = deck.replace(".meas tran HV_AVG", ".meas tran aux_uv WHEN V(aux)=11 FALL=1\n.meas tran gate_last MAX V(gate,src) FROM 33m TO 34m\n.meas tran HV_AVG")
    if load_release:
        deck = deck.replace("20.05m 1)", "20.05m 1 47m 1 47.05m 0)")
        deck = deck.replace(".meas tran HV_AVG", ".meas tran release_peak MAX V(hv) FROM 47m TO 60m\n.meas tran HV_AVG")
    return deck


def write(path, content):
    path.write_text(content, encoding="ascii", newline="\n")


def p2(vin, display, hold, direct=False):
    deck = vendor_p1(vin, display, hold)
    deck = deck.replace("NXT-M3 R7 P1 substrate; vendor boost with external envelopes", "NXT-M3 R7 P2 TPS40210 12V DCM research with vendor controller")
    deck = deck.replace(".include models/controller.sub", ".include TPS40210_TRANS.LIB")
    deck = deck.replace("Rs src 0 0.13", "Rs src 0 0.16")
    deck = deck.replace("Rf3 fb 0 1.90k", "Rf3 fb 0 825")
    deck = re.sub(r"Cint intvcc.*?XU .*?LT3757A\n", """\
* DIS logic maps R6 AUX low and latched OVP into active-high TPS40210 DIS/EN.
Bdis dis 0 V=if(V(en)<1.22,3.3,0)
Ren1 in en 68k
Ren2 en 0 12k
Sshdn en 0 latch 0 slatch
Cbp bp 0 1u
Css ss 0 22n
Rcomp vc comp 10k
Ccomp comp fb 22n
Chf vc fb 220p
Rrt in rt 187k
Crt rt 0 1n
XU bp vc dis 0 fb pwm 0 sense rt ss in TPS40210_TRANS
""", deck, flags=re.S)
    if direct:
        deck = deck.replace("Xdriver pwm drv_fault 0 aux drive_hi drive_lo UCC27511_TRANS\nRg drive_hi gate 22\nRoff drive_lo gate 10",
                            "Rg pwm gate 22\nDoff gate off GFAST\nRoff off pwm 10\n.model GFAST D(Is=.1n Rs=1 N=1)")
        deck = deck.replace("max(0,V(aux)*I(Vauxmeter))", "0")
    return deck


if __name__ == "__main__":
    here = ROOT / "REFERENCE_POWER_DESIGN"
    for name, args, kwargs in [
        ("p1_vendor_nominal", (12,1,125), {}),
        ("p1_vendor_low_max", (10.8,1,110), {}),
        ("p1_vendor_high_off", (13.2,0,125), {}),
        ("p1_vendor_release", (12,1,125), {"load_release":True}),
        ("p1_vendor_bias_loss", (12,1,125), {"stop":"34m", "bias_loss":True}),
    ]:
        write(here / (name + ".cir"), vendor_p1(*args, **kwargs))
    here = ROOT / "ALTERNATIVE_LTSPICE"
    write(here / "p2_tps40210_low_max.cir", p2(10.8,1,110))
    write(here / "p2_tps40210_direct_low_max.cir", p2(10.8,1,110,True))
    write(here / "p2_tps40210_nominal.cir", p2(12,1,125))
