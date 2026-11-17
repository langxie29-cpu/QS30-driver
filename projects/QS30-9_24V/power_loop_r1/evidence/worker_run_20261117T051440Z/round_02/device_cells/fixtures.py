"""device_cells (QS30-9 round_02) - part 2: fixture decks (v3, all debugged).

Deck conventions established by the ngspice-47 debug session whose failures are
preserved verbatim in raw/ (attempt_*, dbg_*):
  * a .control block with an explicit `run` is required;
  * the ST model has internal nodes 100/101/102 and `G1 0 100`, so top-level
    names 'd'/'g'/'s' collide -> all external nodes are renamed;
  * `.tran ... <tstart>` must be 0: with a non-zero start ngspice-47 evaluated
    the PWL breakpoints of the gate source as 0 V (Vgs stayed ~0 and the run
    was electrically meaningless) - reproduced, documented, avoided;
  * `uic` is required (without it the ST level-3 model fails at turn-on with
    'timestep too small');
  * 'IV' is a reserved ngspice function -> current-source names must differ
    (a plain IV made wrdata abort);
  * the vendor diode model is a .MODEL (not a subckt) -> it is used directly
    with a diode element D, not with an X instance;
  * PWL sources must not repeat a breakpoint time.
"""
import device_cells as dc

ST_HEAD = ("* ST model stp9nk50z.lib, byte-identical (STP9NK50Z stands in for STP7N65M2)\n"
           ".include stp9nk50z.lib\n")


def sim(step, end, extra=""):
    return (".options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15\n" + extra +
            f".tran {step:g} {end:g} 0 uic\n")


GATE = "Vp NVPP 0 PWL(0 0 1u 0 1.05u 6.5 25u 6.5 25.05u 0 200u 0)\n"


def st_f1(step, end, temp, extra=""):
    """F1 nonlinear switching: clamped inductive single pulse at Vbus = 170 V."""
    return ("* F1 nonlinear switching: clamped inductive pulse, STP9NK50Z model\n"
            "* Vbus 170 V, 150 uH, 25 us on-time, 6.5 V gate through 10 ohm, 1 mohm\n"
            + ST_HEAD + f".temp {temp}\n"
            "Vbus NVDDP 0 170\n"
            "XQ NVSWP NVGP NVSSP STP9NK50Z\n"
            "Rs NVSSP 0 1m\n"
            "L2 NVSWP 0 150u IC=0\n"
            + GATE +
            "Rg NVPP NVGP 10\n"
            "Rgs NVGP 0 10k\n"
            "Vsense NSSP2 NVSSP 0\n"
            "Rs2 NSSP2 0 1m\n"
            + sim(step, end, extra))


def st_f2():
    """F2 pins: ST declares PIN 1=Drain 2=Gate 3=Source.
    The subcircuit's level-3 core is instantiated with the model's OWN MOS
    parameters (single, documented extraction; the model file is untouched)."""
    return ("* F2 pins: STP9NK50Z pin map 1=D 2=G 3=S; VGS=10 V, VDS 0..5 V\n"
            ".temp 27\n"
            "VG NG 0 10\n"
            "VD ND 0 0\n"
            "MN ND NG NS NS STNCHN\n"
            ".model STNCHN NMOS (LEVEL=3 VTO=4.862 PHI=0.839 IS=0.1E-12 JS=0\n"
            "+ THETA=0.236 KP=7.026)\n"
            ".dc VD 0 5 0.01\n")


def st_tc(temp):
    return ("* TC probe: model self-consistency only (ID at VGS=10 V, VDS=1 V)\n"
            + ST_HEAD + f".temp {temp}\n"
            "VG NG 0 10\n"
            "XQ ND NG NSN STP9NK50Z\n"
            "VD ND 0 1\n"
            "VS NSN 0 0\n"
            ".op\n")


def d_f1(modname, mfile, step, end, temp, extra="", subckt=False):
    """F1 diode turn-off: 1 A forward into 100 uH, then 0 -> 195 V in 195 ns.

    The vendor .MODEL is used DIRECTLY as a diode model: in ngspice-47 a diode
    element did not resolve a model defined inside an .include'd file unless
    the model is also declared locally (empirically reproduced: with
    '.model US1GD D' absent the deck fails 'could not find a valid modelname').
    The bare '.model <name> D' after the include is the documented bridge.
    """
    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\n"
    return ("* F1 diode turn-off / reverse recovery\n"
            f".include {mfile}\n{bridge}.temp {temp}\n"
            "Vf VFP 0 10\n"
            "Rf VFP NVFP 1\n"
            "Lf NVFP NVAP 100u IC=1\n"
            f"{dev}\n"
            "Vr NVKP 0 PWL(0 0 2u 0 2.195u 195 8u 195 8.195u 0 12u 0)\n"
            "Vsense NVKP2 NVKP 0\n"
            "Rk NVKP2 0 1u\n"
            + sim(step, end, extra))


def d_f2(modname, mfile, subckt=False):
    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\n"
    return ("* F2 pins: 2-terminal device (A K); forward sweep 0..1.2 V\n"
            f".include {mfile}\n{bridge}.temp 27\n"
            "VA NVAP 0 0\n"
            f"{dev}\n"
            "VK NVKP 0 0\n"
            ".dc VA 0 1.2 0.005\n")


def d_brk(modname, mfile, temp, subckt=False):
    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\n"
    return ("* reverse window -250 V .. 0 V\n"
            f".include {mfile}\n{bridge}.temp {temp}\n"
            "VA NVAP 0 0\n"
            f"{dev}\n"
            "VK NVKP 0 0\n"
            ".dc VA -250 0 0.5\n")


def d_tc(modname, mfile, temp, subckt=False):
    dev = f"X1 NVAP 0 {modname}" if subckt else f"D1 NVAP 0 {modname}"
    bridge = "" if subckt else f".model {modname} D\n"
    return ("* TC probe: Vf at 1 A vs TEMP (model self-consistency)\n"
            f".include {mfile}\n{bridge}.temp {temp}\n"
            "Vf VFP 0 2\n"
            "Rf VFP NVAP 1\n"
            f"{dev}\n"
            ".op\n")


def l_ladder(step, end):
    s = ("* F3a L(I) ladder: 9 forced-current branches, 0..8 A through 150 uH\n"
         "* DCR as a series resistor (ngspice-47 L has no Rser parameter)\n"
         ".temp 27\n")
    for i in range(1, 10):
        s += (f"ILC{i} 0 NLI{i} PWL(0 0 1u {(i - 1) * 1.0} 401u {i * 1.0})\n"
              f"R{i} NLI{i} NLV{i} 0.038\n"
              f"L{i} NLV{i} 0 150u\n")
    return s + sim(step, end)


DUTY_ON = ("PWL(0 0 1.06u 0 1.08u 1 2.02u 1 2.04u 0 3.06u 0 3.08u 1 4.02u 1 4.04u 0 "
           "5.06u 0 5.08u 1 6.02u 1 6.04u 0 7.06u 0 7.08u 1 8.02u 1 8.04u 0 9.06u 0 "
           "9.08u 1 10.02u 1 10.04u 0 12u 0)\n")


def l_pulse(step, end, saturating=False):
    """F3b boost switch node: Vin 24 V, D 60 %, fsw 500 kHz (switch high = ON).

    Two switch realisations are used so the fixture itself can be checked:
      'sw'  : XSPICE S with RON=1e-3, open state 1e12 (node never floated)
      'nmos': level-1 MOS switch driven from the same gate node
    An earlier XSPICE S with ROFF=100meg never conducted here (V(gate)=1 V,
    V(d)=0 V) - preserved in raw/dbg_bst3 and raw/dbg_bst5_lin.
    """
    s = ("* F3b boost switch node 24 V -> D=0.60 @ 500 kHz, 6 periods\n"
         ".temp 27\n"
         "Vbus NVBP 0 24\n"
         "Vsw NVSW 0 " + DUTY_ON +
         "Ssw NVDP 0 NVSW 0 SWM\n"
         ".model SWM SW(VT=0.5 RON=1e-3 ROFF=1e12)\n"
         "Vds 0 NVDP 0\n")
    if saturating:
        s += ("Bfl NSAT 0 V=Lslot*x/(1+(abs(i(L1))/x)**2)\n"
              "L1 NVBP NSAT 1m IC=0\n"
              ".param Lslot=150u x=9.7\n")
    else:
        s += "Rl NVBP NVL 0.038\nL1 NVL NVDP 150u IC=0\n"
    s += ("D1 NVDP NVOP DUF\n"
          ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\n"
          "Co NVOP 0 47u\n"
          "Rld NVOP 0 3k\n")
    return s + sim(step, end)


def l_pulse_mos(step, end):
    """F3b cross-check: same boost cell with a level-1 MOS as the switch."""
    return ("* F3b cross-check: level-1 NMOS switch, same duty/period\n"
            ".temp 27\n"
            "Vbus NVBP 0 24\n"
            "Vsw NVSW 0 " + DUTY_ON +
            "Msw NVDP NVSW 0 0 MSW\n"
            ".model MSW NMOS(LEVEL=1 VTO=1 KP=20 W=1 L=1u)\n"
            "Vds 0 NVDP 0\n"
            "Rl NVBP NVL 0.038\n"
            "L1 NVL NVDP 150u IC=0\n"
            "D1 NVDP NVOP DUF\n"
            ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\n"
            "Co NVOP 0 47u\n"
            "Rld NVOP 0 3k\n"
            + sim(step, end))


def l_dcr(step, end):
    """F3c DCR screen: the same 150 uH at the datacard typ (0.033) and max (0.038)."""
    s = ("* F3c DCR screen: conduction loss of the inductor at 3.4 A rms\n"
         ".temp 27\nVd NVAP 0 0\n")
    for tag, r in (("typ033", 0.033), ("max038", 0.038)):
        s += f"I{tag} 0 N{t}_{tag} 3.4\nR{t}_{tag} N{t}_{tag} N{r}_{tag} {r}\n"
    return s
