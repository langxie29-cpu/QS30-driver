"""Run the real ngspice library shipped with KiCad; check bounded circuit results."""
import ctypes as ct
import math
import os
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
KICAD=Path(os.environ.get("KICAD_BIN",r"C:\Program Files\KiCad\10.0\bin"))
OUTPUT=HERE/"evidence"/"ngspice.log"

def main():
    with os.add_dll_directory(str(KICAD)):
        lib=ct.CDLL(str(KICAD/"ngspice.dll"))
    messages=[]
    logtype=ct.CFUNCTYPE(ct.c_int,ct.c_char_p,ct.c_int,ct.c_void_p)
    exittype=ct.CFUNCTYPE(ct.c_int,ct.c_int,ct.c_bool,ct.c_bool,ct.c_int,ct.c_void_p)
    @logtype
    def receive(value, _id, _unused):
        messages.append(value.decode("utf-8",errors="replace"))
        return 0
    @logtype
    def status(value, _id, _unused):
        return 0
    @exittype
    def on_exit(code, immediate, on_quit, _id, _unused):
        messages.append(f"ControlledExit: {code}, {immediate}, {on_quit}")
        return 0
    lib.ngSpice_Init.argtypes=[logtype,logtype,exittype,*([ct.c_void_p]*4)]
    lib.ngSpice_Command.argtypes=[ct.c_char_p]
    lib.ngSpice_Init(receive,status,on_exit,None,None,None,None)
    old_cwd=Path.cwd()
    try:
        os.chdir(HERE)
        commands=("version","source residual_energy.cir","run")
        exits=[lib.ngSpice_Command(command.encode("ascii")) for command in commands]
    finally:
        os.chdir(old_cwd)
    body="\n".join(messages)
    OUTPUT.write_text(f"Native library: {KICAD/'ngspice.dll'}\n"
        f"Commands: {commands}\nLibrary returns: {exits}\n\n"+body+"\n",encoding="utf-8")
    values={name:float(amount) for name,amount in re.findall(
        r"(?m)^(?:stdout\s+)?([a-z][a-z_0-9]+)\s*=\s*([-+0-9.eE]+)",body)}
    c, v, ra, bleeder=3.63e-6,195,19800,500960
    dual=bleeder/2
    qty={"dual_t60":dual*c*math.log(v/60),
         "single_t60":bleeder*c*math.log(v/60),
         "fault_q_peak_w":v*v/(4*ra),
         "fault_q_j":(c*v*v/2)*(dual/(dual+2*ra))*0.5,
         "isolated_feed_v":0.0}
    if any(exits):
        raise RuntimeError(f"ngspice command error; inspect {OUTPUT}")
    for key,val in qty.items():
        if key not in values or not math.isclose(values[key],val,rel_tol=.006,abs_tol=1e-8):
            raise RuntimeError(f"{key} expected {val:g}, measured {values.get(key)}")
    if not 4.5 < values.get("pwm_off_feed_v",0) < 5.5:
        raise RuntimeError("Expected nonzero feed-through at 5.5 V input with PWM held off")
    print("Matched six bounded ngspice measurements, including diode feed-through with PWM off.")

if __name__=="__main__":
    main()
