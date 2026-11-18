"""Generate native decks from the frozen circuit; no edits to manufacturer models."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
R6 = HERE.parents[1] / "r6/LTSPICE_MODEL/runs/p1c_full/boost.cir"
BASE = R6.read_text(encoding="ascii")

MEAS = """\
.meas tran i_pass_pk MAX I(Vpasssense)
.meas tran i_pass_avg AVG I(Vpasssense) FROM 50m TO 58m
.meas tran vin_min MIN V(in) FROM 50m TO 58m
.meas tran p_dc AVG V(raw)*-I(VINPUT) FROM 50m TO 58m
.meas tran aux_min MIN V(aux) FROM 50m TO 58m
.meas tran tube1_avg AVG I(Rtube1a) FROM 50m TO 58m
.meas tran i_gate_peak MAX I(Rg)
.meas tran tmr_i_pk MAX I(BtmrLoad)
"""
TUBES = """\
* QS30-1 screen with branch-level ignition and extinction hysteresis.
* Sustaining V derives from 20k and specified current at 170V. Dynamic resistance 100R assumed.
.model TUBE SW(Ron=100 Roff=1T Vt=125 Vh=25)
Vdisplay display 0 PWL(0 0 20m 0 20.05m {enable})
Vhold sustain 0 {hold}
Rtube1a hv a1m 10k
Rtube1b a1m a1 10k
Rtube2a hv a2m 10k
Rtube2b a2m a2 10k
Rtube3a hv a3m 10k
Rtube3b a3m a3 10k
Bign1 ign1 0 V=if(V(display)>.5,V(a1),0)
Bign2 ign2 0 V=if(V(display)>.5,V(a2),0)
Bign3 ign3 0 V=if(V(display)>.5,V(a3),0)
Sgas1 a1 sustain ign1 0 TUBE
Sgas2 a2 sustain ign2 0 TUBE
Sgas3 a3 sustain ign3 0 TUBE
RADC1 hv adc_mid 100k
RADC2 adc_mid adc_pre 100k
RADC3 adc_pre 0 2.49k
RADC4 adc_pre adc 10k
CADC adc 0 10n
"""
FRONT = """\
* Input wiring, eFuse envelope, ARM stimulus and regulated AUX current bookkeeping.
* MODE timer, thermal behavior, POR distribution and reverse blocking are not modeled.
Varm arm 0 PWL(0 0 1m 0 1.05m 1)
Rcable raw board .10
C1 board 0 1u Rser=.05
Bpermit permit 0 V=if(V(latch)>.5,0,V(arm))
Vpasssense board fuse_in 0
{pass_element}
CIN in 0 1u Rser=.05
Rin in 0 100k
* Split the 0.45W low-voltage input planning budget into 0.22W upstream and
* 0.23W protected (12V bias incl. driver). Smooth near power-off to avoid singularities.
Bpre board 0 I=.22*V(board)/(V(board)*V(board)+16)
BtmrLoad in 0 I=(.23/.8+max(0,V(aux)*I(Rg)))*V(in)/(V(in)*V(in)+16)
Btmr aux_source 0 V=12*limit((V(in)-8.9)/.5,0,1)
Raux aux_source aux 1
Caux aux 0 4.7u
CauxLocal aux 0 .3u
RauxSenseA aux aux_ok 265k
RauxSenseB aux_ok 0 10k
BauxPermit aux_permit 0 V=if(V(aux_ok)<.4,1,0)
SauxStop en 0 aux_permit 0 pass
"""
PASS = {
    "ohmic": "Spass fuse_in in permit 0 pass\n.model pass SW(Ron=.15 Roff=100Meg Vt=.5 Vh=.1)",
    "clip": """Blim fuse_in in I=if(V(permit)>.5,max(0,min(V(fuse_in,in)/.15,ILIM)),0)
.model pass SW(Ron=.15 Roff=100Meg Vt=.5 Vh=.1)
.param ILIM=.6""",
}


def unified(vin, display, hold, pass_kind, gear, step):
    deck = BASE.replace("NXT-M3 P1 - Native LT3757A / ST vendor devices; bounded model",
                        "NXT-M3 R7 P1 substrate; vendor boost with external envelopes")
    deck = deck.replace("PWL(0 0 100u 12)", f"PWL(0 0 100u {vin})")
    deck = re.sub(r"Bpermit permit.*?Rin in 0 100k\n", FRONT.format(pass_element=PASS[pass_kind]), deck, flags=re.S)
    deck = re.sub(r"Vload ctl.*?V\(ctl\)/28900\n", TUBES.format(enable=display, hold=hold), deck, flags=re.S)
    deck = deck.replace("limit(8*(V(pwm)-1.8),0,12)", "limit(8*(V(pwm)-1.8),0,V(aux))")
    deck = deck.replace("Cout vcstore 0 5u", "Cout vcstore 0 5u Lser=19n").replace(
        ".ic V(hv)=0 V(vcstore)=0", ".ic V(hv)=0 V(vcstore)=0")
    deck = deck.replace("0.058", "0.060").replace("0.049", "0.050").replace("0.057", "0.058")
    deck = deck.replace("350n uic", f"{step} uic")
    deck = deck.replace("I(VINPUT)\n.meas", "I(VINPUT) I(Vpasssense) V(aux) V(adc) I(Rtube1a) V(a1) V(a2) V(a3)\n.meas", 1)
    if gear:
        deck = deck.replace("method=trap", "method=gear")
    return deck.replace(".end\n", MEAS + ".end\n")


def write(name, deck):
    (HERE / name).write_text(deck, encoding="ascii", newline="\n")


def build():
    write("r6_gear.cir", BASE.replace("method=trap", "method=gear"))
    write("r6_sparse.cir", BASE.replace(
        ".save V(raw) V(in) V(hv) V(sw) V(gate) V(src) V(sense) V(pwm) V(vc) V(en) V(latch) I(Lpower) I(Drec) I(Cout) I(VINPUT)",
        ".save V(hv) I(Lpower) I(VINPUT)"))
    for name, values in {
        "nominal": (12, 1, 125, "ohmic", True, "350n"),
        "low_max": (10.8, 1, 110, "ohmic", True, "350n"),
        "high_off": (13.2, 0, 125, "ohmic", True, "350n"),
        "low_clip": (10.8, 1, 110, "clip", True, "350n"),
        "nominal_halfstep": (12, 1, 125, "ohmic", True, "175n"),
    }.items():
        write(name + ".cir", unified(*values))


if __name__ == "__main__":
    build()
