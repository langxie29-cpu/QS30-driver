from pathlib import Path

p = Path('fixtures.py')
s = p.read_text(encoding='utf-8')

pairs = [
('''def d_f1(modname, mfile, step, end, temp, extra=""):''',
 '''def d_f1(modname, mfile, step, end, temp, extra="", subckt=False):'''),
('''    return ("* F1 diode turn-off / reverse recovery\\n"
            f".include {mfile}\\n.model {modname} D\\n.temp {temp}\\n"
            "Vf VFP 0 10\\n"
            "Rf VFP NVFP 1\\n"
            "Lf NVFP NVAP 100u IC=1\\n"
            f"D1 NVAP NVKP {modname}\\n"''',
 '''    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\\n"
    return ("* F1 diode turn-off / reverse recovery\\n"
            f".include {mfile}\\n{bridge}.temp {temp}\\n"
            "Vf VFP 0 10\\n"
            "Rf VFP NVFP 1\\n"
            "Lf NVFP NVAP 100u IC=1\\n"
            f"{dev}\\n"'''),
('''def d_f2(modname, mfile):
    return ("* F2 pins: 2-terminal device (A K); forward sweep 0..1.2 V\\n"
            f".include {mfile}\\n.model {modname} D\\n.temp 27\\n"
            "VA NVAP 0 0\\n"
            f"D1 NVAP NVKP {modname}\\n"''',
 '''def d_f2(modname, mfile, subckt=False):
    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\\n"
    return ("* F2 pins: 2-terminal device (A K); forward sweep 0..1.2 V\\n"
            f".include {mfile}\\n{bridge}.temp 27\\n"
            "VA NVAP 0 0\\n"
            f"{dev}\\n"'''),
('''def d_brk(modname, mfile, temp):
    return ("* reverse window -250 V .. 0 V\\n"
            f".include {mfile}\\n.model {modname} D\\n.temp {temp}\\n"
            "VA NVAP 0 0\\n"
            f"D1 NVAP NVKP {modname}\\n"''',
 '''def d_brk(modname, mfile, temp, subckt=False):
    dev = f"X1 NVAP NVKP {modname}" if subckt else f"D1 NVAP NVKP {modname}"
    bridge = "" if subckt else f".model {modname} D\\n"
    return ("* reverse window -250 V .. 0 V\\n"
            f".include {mfile}\\n{bridge}.temp {temp}\\n"
            "VA NVAP 0 0\\n"
            f"{dev}\\n"'''),
('''def d_tc(modname, mfile, temp):
    return ("* TC probe: Vf at 1 A vs TEMP (model self-consistency)\\n"
            f".include {mfile}\\n.model {modname} D\\n.temp {temp}\\n"
            "Vf VFP 0 2\\n"
            "Rf VFP NVAP 1\\n"
            f"D1 NVAP 0 {modname}\\n"''',
 '''def d_tc(modname, mfile, temp, subckt=False):
    dev = f"X1 NVAP 0 {modname}" if subckt else f"D1 NVAP 0 {modname}"
    bridge = "" if subckt else f".model {modname} D\\n"
    return ("* TC probe: Vf at 1 A vs TEMP (model self-consistency)\\n"
            f".include {mfile}\\n{bridge}.temp {temp}\\n"
            "Vf VFP 0 2\\n"
            "Rf VFP NVAP 1\\n"
            f"{dev}\\n"'''),
]
for a, b in pairs:
    assert a in s, a[:60]
    s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print("ok", s.count("subckt"))
