from pathlib import Path

p = Path('fixtures.py')
s = p.read_text(encoding='utf-8')

# 1. ladder source names (I1..I9 collide with ngspice current vectors)
s = s.replace('f"I{i} 0 NLI{i} PWL', 'f"ILC{i} 0 NLI{i} PWL')

# 2. boost switch: replace the non-conducting XSPICE SW by a behavioural R pair
old = '         "Rsw NVDP 0 R=1m+99meg*(1-V(NVSW))\\n"'
new = ('         "Rsw NVDP 0 1m\\n"\n'
       '         "Ssw NVDP 0 NVSW 0 SWM\\n"\n'
       '         ".model SWM SW(VT=0.5 RON=1u ROFF=1g)\\n"')
assert old in s, "switch line not found"
s = s.replace(old, new)
s = s.replace('''    The switch is a behavioural controlled R, not an XSPICE SW: an XSPICE SW
    with ROFF=100meg never conducted in this deck (V(gate)=1 V, V(d)=0 V,
    documented in raw/dbg_bst3), so the validated B-source form is used.
    """: ''', '''    The switch is an XSPICE SW with an RON that is small compared with the
    38 mohm DCR, bypassed by a fixed 1 mohm so the node is never floated; the
    earlier form (RON=1m ROFF=100meg) never conducted in this deck
    (V(gate)=1 V, V(d)=0 V, preserved in raw/dbg_bst3).
    """: ''')
p.write_text(s, encoding='utf-8')
print("ok")
