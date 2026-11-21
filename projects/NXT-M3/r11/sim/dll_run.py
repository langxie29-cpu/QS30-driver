"""Execute one ngspice DLL fixture in a separate process."""
import ctypes as ct
import os
from pathlib import Path
import sys

KICAD = Path(os.environ.get("KICAD_BIN", r"C:\Program Files\KiCad\10.0\bin"))
target = Path(sys.argv[1]).resolve()
os.chdir(target.parent)
with os.add_dll_directory(str(KICAD)):
    lib = ct.CDLL(str(KICAD / "ngspice.dll"))
callback = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_int, ct.c_void_p)
exit_callback = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.c_bool, ct.c_bool, ct.c_int, ct.c_void_p)
errors = []


@callback
def receive(value, identifier, unused):
    line = value.decode("utf-8", "replace")
    print(line, flush=True)
    if any(word in line.lower() for word in ("error:", "timestep too small", "simulation(s) aborted")):
        errors.append(line)
    return 0


@exit_callback
def on_exit(code, immediate, quit_requested, identifier, unused):
    print(f"ControlledExit={code}", flush=True)
    if code:
        errors.append(str(code))
    return 0


lib.ngSpice_Init.argtypes = [callback, callback, exit_callback, *([ct.c_void_p] * 4)]
lib.ngSpice_Command.argtypes = [ct.c_char_p]
lib.ngSpice_Init(receive, callback(), on_exit, None, None, None, None)
model_dir = KICAD.parent / "lib/ngspice"
os.chdir(model_dir)
short = ct.create_unicode_buffer(32768)
ct.windll.kernel32.GetShortPathNameW(str(model_dir), short, len(short))
cm_path = Path(short.value or str(model_dir))
model_search = os.add_dll_directory(str(model_dir))
models = tuple(f"codemodel {(cm_path / file.name).as_posix()}" for file in sorted(model_dir.glob("*.cm")))
commands = ("version", *models, "set ngbehavior=ps", f"source {target.name}", "run",
            "set filetype=binary", "write waveform.raw")
for command in commands:
    if command.startswith("source "):
        os.chdir(target.parent)
    result = lib.ngSpice_Command(command.encode("ascii"))
    print(f"ngspice> {command} [return {result}]", flush=True)
    if result or errors:
        sys.exit(2)




