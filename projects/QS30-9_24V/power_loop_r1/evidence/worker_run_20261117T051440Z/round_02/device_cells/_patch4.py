from pathlib import Path

p = Path('fixtures.py')
s = p.read_text(encoding='utf-8')
start = s.index('DUTY = "PWL(')
end = s.index('def l_dcr(')
new = '''DUTY_ON = ("PWL(0 0 1.06u 0 1.08u 1 2.02u 1 2.04u 0 3.06u 0 3.08u 1 4.02u 1 4.04u 0 "
           "5.06u 0 5.08u 1 6.02u 1 6.04u 0 7.06u 0 7.08u 1 8.02u 1 8.04u 0 9.06u 0 "
           "9.08u 1 10.02u 1 10.04u 0 12u 0)\\n")


def l_pulse(step, end, saturating=False):
    """F3b boost switch node: Vin 24 V, D 60 %, fsw 500 kHz (switch high = ON).

    Two switch realisations are used so the fixture itself can be checked:
      'sw'  : XSPICE S with RON=1e-3, open state 1e12 (node never floated)
      'nmos': level-1 MOS switch driven from the same gate node
    An earlier XSPICE S with ROFF=100meg never conducted here (V(gate)=1 V,
    V(d)=0 V) - preserved in raw/dbg_bst3 and raw/dbg_bst5_lin.
    """
    s = ("* F3b boost switch node 24 V -> D=0.60 @ 500 kHz, 6 periods\\n"
         ".temp 27\\n"
         "Vbus NVBP 0 24\\n"
         "Vsw NVSW 0 " + DUTY_ON +
         "Ssw NVDP 0 NVSW 0 SWM\\n"
         ".model SWM SW(VT=0.5 RON=1e-3 ROFF=1e12)\\n"
         "Vds 0 NVDP 0\\n")
    if saturating:
        s += ("Bfl NSAT 0 V=Lslot*x/(1+(abs(i(L1))/x)**2)\\n"
              "L1 NVBP NSAT 1m IC=0\\n"
              ".param Lslot=150u x=9.7\\n")
    else:
        s += "Rl NVBP NVL 0.038\\nL1 NVL NVDP 150u IC=0\\n"
    s += ("D1 NVDP NVOP DUF\\n"
          ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\\n"
          "Co NVOP 0 47u\\n"
          "Rld NVOP 0 3k\\n")
    return s + sim(step, end)


def l_pulse_mos(step, end):
    """F3b cross-check: same boost cell with a level-1 MOS as the switch."""
    return ("* F3b cross-check: level-1 NMOS switch, same duty/period\\n"
            ".temp 27\\n"
            "Vbus NVBP 0 24\\n"
            "Vsw NVSW 0 " + DUTY_ON +
            "Msw NVDP NVSW 0 0 MSW\\n"
            ".model MSW NMOS(LEVEL=1 VTO=1 KP=20 W=1 L=1u)\\n"
            "Vds 0 NVDP 0\\n"
            "Rl NVBP NVL 0.038\\n"
            "L1 NVL NVDP 150u IC=0\\n"
            "D1 NVDP NVOP DUF\\n"
            ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\\n"
            "Co NVOP 0 47u\\n"
            "Rld NVOP 0 3k\\n"
            + sim(step, end))


'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding='utf-8')
print('ok')
