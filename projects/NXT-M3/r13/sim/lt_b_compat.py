"""Record a syntax-only LTspice compatibility trial for the pinned LM3488 library."""
from pathlib import Path
import hashlib
import json
import re

import lt_replay_expr as replay

ORIGINAL_RUN = replay.run


def normalize(data):
    text = data.decode("latin1")
    text = re.sub(r"(?m)\r?\n\+\s*", " ", text)
    behavior = re.compile(r"(?mi)^([eg]\S*)(\s+\S+\s+\S+)\s+value\s*=?\s*\{([^\n]+)\}\s*$")
    def convert(m):
        name,nodes,expression = m.groups()
        quantity = "V" if name[0].lower() == "e" else "I"
        expression = re.sub(r"\{\{([^{}]+)\}\}",r"{\1}",expression)
        return f"B_{name}{nodes} {quantity}={expression}"
    text, changed_sources = behavior.subn(convert,text)
    text, changed_pulses = re.subn(r"(?mi)\bPULSE\s+0\s+(0|0\.1)\s+0\s*$",
                                    r"PULSE(0 \1 0 1n 1n 1 2)",text)
    return text.encode("latin1"),{"behavioral_sources":changed_sources,"pulse_fields":changed_pulses}


def copy(model, output):
    model,output = Path(model),Path(output)
    if model.name != "LM3488_TRANS.LIB":
        return mirror(model,output)
    pristine = model.read_bytes()
    compat,changes = normalize(pristine)
    output.write_bytes(compat)
    hashes = {name:hashlib.sha256(value).hexdigest() for name,value in
              (("original_sha256",pristine),("compat_sha256",compat))}
    (output.parent/"compatibility.json").write_text(json.dumps(hashes | changes,indent=2)+"\n")


if __name__ == "__main__":
    mirror = replay.shutil.copyfile
    replay.shutil.copyfile = copy
    replay.OUTPUT = replay.ROOT/".local/lt_b_compat"
    replay.OUTPUT.mkdir()
    for key in ("b_ref_approx","b_low_trap_vref126"):
        ORIGINAL_RUN((key,replay.SELECTION[key]))
