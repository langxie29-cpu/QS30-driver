"""Derived, clearly-labelled index of model metadata.

This script does NOT modify any vendor file. It reads the registered vendor
artifacts and writes a compact JSON index used by inventory.md so the reader
can audit the provenance claims (headers, simulators, limitations, pin order,
token counts) that appear in inventory.md.

Outputs (all inside OUTPUT_DIR):
  model_index.json     - machine readable inventory
  model_registration.json - exact origin/license/version/solver per artifact
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path

HIST = Path(r"D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V")
PROSP = Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V")
OUT = Path(__file__).resolve().parent
VB = OUT / "vendor_bytes"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ascii_lines(p, n=60, enc="latin-1"):
    raw = Path(p).read_bytes()
    txt = raw.decode(enc, "replace")
    out = []
    for line in txt.splitlines()[:n]:
        out.append(re.sub(r"[^\x20-\x7e]", ".", line.rstrip()))
    return out


def counts(p):
    b = Path(p).read_bytes()
    return {
        "bytes": len(b),
        "crlf": b.count(b"\r\n"),
        "lf": b.count(b"\n"),
        "nul": b.count(b"\x00"),
        "non_ascii": sum(1 for x in b if x > 127),
        "encrypted_marker": bool(re.search(rb"(?i)encrypt", b)),
    }


# ------------------------------------------------------------------ artifacts
UCC_UNENC = PROSP / "sources/sprint06/UCCx8C43_unencrypted/unpacked/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib"
UCC_2008 = PROSP / "sources/sprint06/UCC28C43_pspice/unpacked/UCC28C43_PSPICE_07NOV2008/UCC28C43_PSPICE_TRANS/ucc28c43.lib"
UCC_TINA = PROSP / "sources/sprint06/UCC28C43_startup/unpacked/UCC28C43_TINA_TRANS/UCC28C43_START.LIB"
SIHP = PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB"
SIHP_RC = PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_RC_Rev_B.lib"
STP9 = PROSP / "sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib"
US1G = PROSP / "sources/sprint06b/Vishay_US1G/us1g.txt"
DIODES_US1G = PROSP / "sources/sprint06b/Diodes_US1G/Diodes_US1G.txt"
SS14 = HIST / "sources/sprint06c/SS14/original.lib"

ms = {}


def add(key, path, **kw):
    p = Path(path)
    if not p.exists():
        ms[key] = {"present": False, "path": str(p)}
        return
    d = {"present": True, "path": str(p).replace("\\", "/"), "sha256": sha(p)}
    d.update(counts(p))
    d.update(kw)
    ms[key] = d


add("LT3757A.sub", VB / "LT3757A.sub", enc="latin-1")
ms["LT3757A.sub"]["header_lines"] = ascii_lines(VB / "LT3757A.sub", 6)
add("LT3757A.asy", VB / "LT3757A.asy", enc="ascii")
add("LT3757A.asc", VB / "LT3757A.asc", enc="utf-8")
add("ucc28c43.lib (2008 PSpice, encrypted)", UCC_2008)
add("ucc28c43_trans_unencrypted.lib", UCC_UNENC)
add("UCC28C43_START.LIB (TINA)", UCC_TINA)
add("SiHP8N50D_PS_Rev_B.LIB", SIHP)
add("SiHP8N50D_PS_RC_Rev_B.lib", SIHP_RC)
add("stp9nk50z.lib", STP9)
add("us1g.txt (Vishay)", US1G)
add("Diodes_US1G.txt", DIODES_US1G)
add("SS14 original.lib (historical)", SS14)

# ------------------------------------------------------- parsed characteristics
index = {"models": ms, "parsed": {}}


def subckt_tokens(p):
    if not Path(p).exists():
        return None
    t = Path(p).read_text(encoding="latin-1", errors="replace")
    m = re.search(r"(?i)^\s*\.SUBCKT\s+(\S+)\s+(.*)$", t, re.M)
    if not m:
        return None
    return {"name": m.group(1), "pins": m.group(2).split()}


index["parsed"]["LT3757A_subckt"] = subckt_tokens(VB / "LT3757A.sub")
index["parsed"]["LT3757A_is_binary"] = (VB / "LT3757A.sub").read_bytes().startswith(b"\r\n<Binary File>")
index["parsed"]["UCC28C43_unencrypted_subckt"] = subckt_tokens(UCC_UNENC)
index["parsed"]["UCC28C43_2008_encrypted_subckt_header"] = (
    subckt_tokens(UCC_2008) or {}
) if UCC_2008.exists() else None
# the 2008 file exposes the .SUBCKT header in clear text even though the body
# is CDN-encrypted: record both
if UCC_2008.exists():
    txt = UCC_2008.read_text(encoding="latin-1", errors="replace")
    index["parsed"]["UCC28C43_2008_sections"] = [
        re.sub(r"[^\x20-\x7e]", ".", l.strip())
        for l in txt.splitlines()
        if re.match(r"(?i)^\s*\.(subckt|ends)", l.strip())
    ]
    index["parsed"]["UCC28C43_2008_cdn_encrypt_blocks"] = txt.count("$CDNENCSTART")
index["parsed"]["SiHP8N50D_subckt"] = subckt_tokens(SIHP)
index["parsed"]["STP9NK50Z_subckt"] = subckt_tokens(STP9)

# TINA library: binary/encrypted container?
if UCC_TINA.exists():
    b = UCC_TINA.read_bytes()
    index["parsed"]["UCC28C43_TINA_LIB"] = {
        "starts_with": re.sub(r"[^\x20-\x7e]", ".", b[:30].decode("latin-1")),
        "printable_fraction": round(
            sum(1 for x in b if 32 <= x < 127) / max(1, len(b)), 4
        ),
        "has_subckt_text": b".subckt" in b.lower(),
    }

# ------------------------------------- tokens unsupported by strict LTspice
# The unencrypted TI library uses PSpice-only constructs. LTspice has no
# native form for 'E ... VALUE = { }' / 'G ... VALUE = { }' behavioural sources;
# they have to be transliterated to B-sources. That transliteration is an
# EDIT of the vendor model, not native replay. Record the count so the claim
# can be audited rather than asserted.
if UCC_UNENC.exists():
    txt = UCC_UNENC.read_text(encoding="latin-1", errors="replace")
    pat_e_value = re.findall(r"(?im)^\s*E\S+\s+\S+\s+\S+\s+VALUE\s*=", txt)
    pat_g_value = re.findall(r"(?im)^\s*G\S+\s+\S+\s+\S+\s+VALUE\s*=", txt)
    pat_poly = re.findall(r"(?im)^\s*[EG]\S+\s+POLY", txt)
    pat_tbl = re.findall(r"(?i)TABLE\s*\{", txt)
    index["parsed"]["UCC28C43_pspice_only_constructs"] = {
        "E_..._VALUE_lines": len(pat_e_value),
        "G_..._VALUE_lines": len(pat_g_value),
        "E_or_G_POLY_lines": len(pat_poly),
        "TABLE_brace_expr": len(pat_tbl),
        "lines": ascii_lines(UCC_UNENC, 2000)[0:0],
    }

# ---------------------------------------------------------- license extracts
lic = HIST / "toolchain/ltspice26/extracted/License.txt"
lic_txt = lic.read_text(encoding="latin-1", errors="replace")
index["parsed"]["ADI_license"] = {
    "file_sha256": sha(lic),
    "agreement_id": lic_txt.splitlines()[1].strip() if lic_txt else None,
    "uses": [l[:240] for l in lic_txt.splitlines() if "to internally use and copy" in l or "Excluded License" in l.split(" ")[:0]],
    "restriction_excerpt": next(
        (l[:400] for l in lic_txt.splitlines() if "shall not modify, reverse engineer" in l), None
    ),
    "no_redistribution_excerpt": next(
        (l[:200] for l in lic_txt.splitlines() if "may not distribute the PC Software" in l), None
    ),
}

# TI / Vishay / ST / Coilcraft license extracts from their own model/doc headers
index["parsed"]["TI_model_disclaimer"] = ascii_lines(UCC_UNENC, 26)[2:9]
index["parsed"]["TI_model_updates_block"] = ascii_lines(UCC_UNENC, 42)[23:42]
index["parsed"]["Vishay_model_header"] = ascii_lines(SIHP, 12)[:12]
index["parsed"]["ST_model_header"] = ascii_lines(STP9, 22)
index["parsed"]["Vishay_US1G_header"] = ascii_lines(US1G, 12)
index["parsed"]["Diodes_US1G_disclaimer"] = ascii_lines(DIODES_US1G, 20)[:14]

(OUT / "model_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
print("wrote model_index.json")
for k, v in ms.items():
    print(f"{k:44s} present={v.get('present')} sha={str(v.get('sha256'))[:16]} enc={v.get('encrypted_marker')}")
print("LT3757A subckt:", index["parsed"]["LT3757A_subckt"], "binary:", index["parsed"]["LT3757A_is_binary"])
print("UCC subckt:", index["parsed"]["UCC28C43_unencrypted_subckt"])
print("CDN blocks:", index["parsed"].get("UCC28C43_2008_cdn_encrypt_blocks"))
print("TINA:", index["parsed"].get("UCC28C43_TINA_LIB"))
