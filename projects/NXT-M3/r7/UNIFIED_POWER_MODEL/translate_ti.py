"""Lexical PSpice-to-LTspice translation. Preserve equations, constants, topology and pins."""
from pathlib import Path
import os
import re

TEMP = Path(os.environ["TEMP"]) / "nxt-r7-vendor"
CLAIMS = {
    "sbvm552b/TPS3700_TRANS.LIB": "tps3700",
    "slum488/UCC27511_TRANS.LIB": "ucc27511",
    "slum712/TPS40210_TRANS.LIB": "tps40210",
    "slum521/ucc28c43_trans_unencrypted.lib": "ucc28c43",
}
KEEP = {"TPS3700_TRANS", "UCC27511_TRANS", "TPS40210_TRANS", "UCC28C43_START", "UCC28C43_STEADY"}


def translate(path, prefix):
    data = path.read_bytes().replace(b"\xef\xbb\xbf", b"").decode("latin-1")
    markup = re.findall(r"(?im)^\.subckt\s+(\S+)", data)
    for original in sorted(set(markup)-KEEP, key=len, reverse=True):
        data = re.sub(rf"(?i)(?<![\w]){re.escape(original)}(?![\w])", f"{prefix}_{original}", data)
    lines = []
    for line in data.splitlines():
        if line.startswith("+") and lines and not lines[-1].startswith("*"):
            lines[-1] += " " + line[1:].strip()
        else:
            lines.append(line)
    out = []
    for line in lines:
        if prefix=="ucc28c43" and line.upper().startswith("EMY19 "):
            # Preserve the sensed voltage-source branch name at exactly unity gain.
            line = "EMY19 191 GND 19 GND 1"
        if prefix=="tps40210":
            line = line.replace("V(VDD),8} )", "V(VDD),8) }").replace("V(VDD),8})", "V(VDD),8)}")
        value = re.fullmatch(r"([EG])(\S*)\s+(\S+)\s+(\S+)\s+VALUE\s*=?\s*(\{.+\})\s*", line, re.I)
        if value:
            device, label, pos, neg, expression = value.groups()
            expression = expression.strip()[1:-1].strip()
            # Double braces wrap a complete runtime expression in the PSpice library.
            if expression.startswith("{") and expression.endswith("}"):
                expression = expression[1:-1].strip()
            expression = re.sub(r"(V\([^()]+\))\s*\*\*\s*([23])\b",
                                lambda m: "("+"*".join([m[1]]*int(m[2]))+")", expression, flags=re.I)
            expression = re.sub(r"(?i)\bIF\s+\(", "IF(", expression)
            drive = "V" if device.upper()=="E" else "I"
            line = f"B{label} {pos} {neg} {drive}={expression}"
        if prefix=="ucc27511":
            # One literal opening parenthesis is missing in TI's table at the 6 V knot.
            line = line.replace("(5,52m)6,58m)", "(5,52m)(6,58m)")
        out.append(line)
    return "\n".join(out)+"\n"


if __name__ == "__main__":
    destination = TEMP / "lt"
    destination.mkdir(exist_ok=True)
    for relative, prefix in CLAIMS.items():
        source = TEMP / relative
        normalized = translate(source, prefix)
        (destination/source.name).write_text(normalized, encoding="latin-1", newline="\n")
