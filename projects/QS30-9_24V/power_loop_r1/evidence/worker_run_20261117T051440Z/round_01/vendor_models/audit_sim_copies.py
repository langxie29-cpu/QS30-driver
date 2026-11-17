"""Audit helper: prove that the historical sim vendor.lib copies are either
byte-identical to the registered originals or explicitly altered.

No vendor file is written by this script. Output: sim_copy_audit.json
"""
import hashlib
import json
from pathlib import Path

PROSP = Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V")
OUT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ORIGINALS = {
    "UCC28C43 unencrypted (ab3cd5bb)": sha(
        PROSP / "sources/sprint06/UCCx8C43_unencrypted/unpacked/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib"
    ),
    "STP9NK50Z (6ad61988)": sha(PROSP / "sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib"),
    "SiHP8N50D PS RevB (70965ff7)": sha(
        PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB"
    ),
    "Vishay US1G model (f8669a85)": sha(PROSP / "sources/sprint06b/Vishay_US1G/us1g.txt"),
    "UCC27511 unencrypted (bf3e1b75?)": sha(
        PROSP / "sources/sprint06/UCC27511_unencrypted/unpacked/UCC27511_TRANS.LIB"
    ),
    "SiHP8N50D PS_RC RevB (1980c0ed)": sha(
        PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_RC_Rev_B.lib"
    ),
}
rev = {v: k for k, v in ORIGINALS.items()}

rows = []
for p in sorted((PROSP / "sim").glob("*/*/*.lib")):
    h = sha(p)
    rows.append(
        {
            "path": str(p).replace("\\", "/"),
            "sha256": h,
            "matches": rev.get(h, "NO_MATCH_REGISTERED_ORIGINAL"),
        }
    )

unmatched = [r for r in rows if r["matches"] == "NO_MATCH_REGISTERED_ORIGINAL"]
res = {
    "originals": ORIGINALS,
    "copies": rows,
    "copies_total": len(rows),
    "copies_matching_original": len(rows) - len(unmatched),
    "copies_not_matching_any_registered_original": unmatched,
    "note": "Copies that do not match are evidence that a sim-time vendor.lib/st.lib was "
            "edited relative to the registered original; such runs are NOT native model replay.",
}
(OUT / "sim_copy_audit.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "copies"}, indent=1)[:3000])
