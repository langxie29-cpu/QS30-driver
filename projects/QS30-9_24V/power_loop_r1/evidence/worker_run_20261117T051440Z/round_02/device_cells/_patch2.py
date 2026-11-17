from pathlib import Path

p = Path('fixtures.py')
s = p.read_text(encoding='utf-8')

old_lp_start = s.index('def l_pulse(')
old_lp_end = s.index('def l_dcr(')
new_lp = '''DUTY_ON = ("PWL(0 0 1.06u 0 1.08u 1 2.02u 1 2.04u 0 3.06u 0 3.08u 1 4.02u 1 4.04u 0 "
           "5.06u 0 5.08u 1 6.02u 1 6.04u 0 7.06u 0 7.08u 1 8.02u 1 8.04u 0 9.06u 0 "
           "9.08u 1 10.02u 1 10.04u 0 12u 0)\\n")


def l_pulse(step, end, saturating=False):
    """F3b boost switch node: Vin 24 V, D 60 %, fsw 500 kHz, 6 switch periods.

    The switch is a behavioural controlled R, not an XSPICE SW: an XSPICE SW
    with ROFF=100meg never conducted in this deck (V(gate)=1 V, V(d)=0 V,
    documented in raw/dbg_bst3), so the validated B-source form is used.
    """
    s = ("* F3b boost switch node 24 V -> D=0.60 @ 500 kHz, 6 periods\\n"
         ".temp 27\\n"
         "Vbus NVBP 0 24\\n"
         "Vsw NVSW 0 " + DUTY_ON +
         "Rsw NVDP 0 R=1m+99meg*(1-V(NVSW))\\n"
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
    if saturating:
        return s + sim(step, end)
    return s + sim(step, end)


'''
s = s[:old_lp_start] + new_lp + s[old_lp_end:]
p.write_text(s, encoding='utf-8')
print("patched")
