"""vendor_models (QS30-9, model_registrar).

Read-only extraction of exact vendor bytes into OUTPUT_DIR plus SHA-256
registration of every inventoried vendor artifact.

Rules honoured here:
  * Original bytes are NEVER rewritten: only
    zipfile.read() -> write (identical payload) is performed.
  * Nothing outside OUTPUT_DIR is written.
  * Historical workspace D:/PROJECTS/dsharness/QS30-1/... is read-only.
"""
import hashlib
import json
import os
import zipfile
from pathlib import Path

HIST = Path(r"D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V")
PROSP = Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V")
OUT = Path(__file__).resolve().parent
EXTR = OUT / "vendor_bytes"
EXTR.mkdir(parents=True, exist_ok=True)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


records = []


def rec(kind, name, src, payload_sha, size, **extra):
    r = {
        "kind": kind,
        "name": name,
        "source_path": str(src).replace("\\", "/"),
        "sha256": payload_sha,
        "bytes": size,
    }
    r.update(extra)
    records.append(r)
    return r


# ---------------------------------------------------------------- LTspice dist
LT = HIST / "toolchain" / "ltspice26"
LTX = LT / "extracted"
for f, label in [
    (LT / "LTspice64.msi", "LTspice64.msi (ADI signed distribution installer)"),
    (LT / "source.json", "toolchain/ltspice26/source.json"),
    (LTX / "lib.zip", "LTspice lib.zip (ADI signed distribution)"),
    (LTX / "examples.zip", "LTspice examples.zip (ADI signed distribution)"),
    (LTX / "License.txt", "LTspice License.txt"),
    (LTX / "License.pdf", "LTspice License.pdf"),
    (LTX / "LTspice.exe", "LTspice.exe v24.0.12.0"),
    (LTX / "LTspiceChangeLog.txt", "LTspiceChangeLog.txt"),
    (LTX / "LTspice.json", "LTspice.json (updater metadata)"),
]:
    rec("ltspice_distribution", label, f, sha256_file(f), f.stat().st_size)

# ------------------------------------------------- extract exact LT3757A bytes
TARGETS = [
    ("lib.zip", "lib/sub/LT3757A.sub", "LT3757A.sub"),
    ("lib.zip", "lib/sym/PowerProducts/LT3757A.asy", "LT3757A.asy"),
    ("examples.zip", "examples/Applications/LT3757A.asc", "LT3757A.asc"),
]
extracted = []
for zname, member, outname in TARGETS:
    zp = LTX / zname
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        if member not in names:
            print("MISSING MEMBER", member, "in", zname)
            continue
        info = z.getinfo(member)
        payload = z.read(member)
        dst = EXTR / outname
        dst.write_bytes(payload)
        back = dst.read_bytes()
        assert back == payload, "round-trip mismatch"
        assert sha256_bytes(back) == sha256_bytes(payload)
        extracted.append(
            {
                "archive": zname,
                "archive_sha256": sha256_file(zp),
                "member": member,
                "out_file": "vendor_bytes/" + outname,
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
                "zip_crc32": format(info.CRC, "08x"),
                "zip_date_time": "%04d-%02d-%02dT%02d:%02d:%02d" % info.date_time,
                "rewritten": False,
                "roundtrip_identical": True,
            }
        )
        rec("lt3757a_native", "LT3757A " + member, zp, sha256_bytes(payload), len(payload),
            archive_member=member)

# --------------------------------------------- historical bundled LT3757A copy
for f, nm in [
    (HIST / "sources/sprint06c/LT3757A_bundled/LT3757A.sub", "LT3757A.sub (historical bundled copy)"),
    (HIST / "sources/sprint06c/LT3757A_bundled/LT3757A.asy", "LT3757A.asy (historical bundled copy)"),
    (HIST / "sources/sprint06c/LT3757A_bundled/source.json", "LT3757A_bundled/source.json"),
    (HIST / "sources/sprint06c/LT3757A_datasheet_retry/original.pdf", "LT3757-3757A datasheet PDF (ADI)"),
    (HIST / "sources/sprint06c/LT3757A_datasheet_retry/source.json", "LT3757A_datasheet_retry/source.json"),
    (HIST / "sources/sprint06c/manifest_controller_additions.json", "manifest_controller_additions.json"),
]:
    rec("lt3757a_historical", nm, f, sha256_file(f), f.stat().st_size)

# ------------------------------------------------------------- UCC28C43 family
TI = [
    (PROSP / "sources/sprint06/UCC28C43_pspice/UCC28C43_pspice.zip", "UCC28C43 PSpice zip (slum033)"),
    (PROSP / "sources/sprint06/UCC28C43_pspice/unpacked/UCC28C43_PSPICE_07NOV2008/UCC28C43_PSPICE_TRANS/ucc28c43.lib", "ucc28c43.lib"),
    (PROSP / "sources/sprint06/UCC28C43_startup/UCC28C43_startup.zip", "UCC28C43 TINA zip (slum178)"),
    (PROSP / "sources/sprint06/UCC28C43_startup/unpacked/UCC28C43_TINA_TRANS/UCC28C43_START.LIB", "UCC28C43_START.LIB (TINA)"),
    (PROSP / "sources/sprint06/UCCx8C43_unencrypted/UCCx8C43_unencrypted.zip", "UCCx8C43 unencrypted PSpice zip"),
    (PROSP / "sources/sprint06/UCCx8C43_unencrypted/unpacked/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib", "ucc28c43_trans_unencrypted.lib"),
    (PROSP / "sources/sprint06/manifest.json", "sources/sprint06/manifest.json"),
    (PROSP / "sources/sprint06/UCC27511_unencrypted/UCC27511_unencrypted.zip", "UCC27511 unencrypted zip (TI)"),
    (PROSP / "sources/sprint06/UCC27511_unencrypted/unpacked/UCC27511_TRANS.LIB", "UCC27511_TRANS.LIB (TI, line 57 syntactically broken)"),
    (PROSP / "safety_r1/sources/UCC27511DBVR.pdf", "UCC27511 datasheet PDF (safety_r1)"),
    (PROSP / "sources/UCC28C43.pdf", "UCC28C43 datasheet PDF"),
    (PROSP / "sources/UCC28C43.txt", "UCC28C43 datasheet text"),
    (PROSP / "safety_r1/sources/UCC28C43DR.pdf", "UCC28C43DR datasheet PDF (safety_r1)"),
    (HIST / "sources/sprint06/UCC28C43_pspice/UCC28C43_pspice.zip", "UCC28C43 PSpice zip (historical copy)"),
    (HIST / "sources/sprint06/UCCx8C43_unencrypted/UCCx8C43_unencrypted.zip", "UCCx8C43 unencrypted zip (historical copy)"),
    (HIST / "sources/sprint06/UCC28C43_startup/UCC28C43_startup.zip", "UCC28C43 TINA zip (historical copy)"),
]
for f, nm in TI:
    if f.exists():
        rec("ucc28c43", nm, f, sha256_file(f), f.stat().st_size)
    else:
        rec("ucc28c43", nm, f, None, None, missing=True)

# ----------------------------------------------------------------- MOS / diode
DEV = [
    (PROSP / "sources/sprint06c/SiHP8N50D_model/original.zip", "SiHP8N50D vendor model zip"),
    (PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_Rev_B.LIB", "SiHP8N50D_PS_Rev_B.LIB"),
    (PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_PS_RC_Rev_B.lib", "SiHP8N50D_PS_RC_Rev_B.lib (Coss/thermal)"),
    (PROSP / "sources/sprint06c/SiHP8N50D_model/unpacked/SiHP8N50D_HS_Rev_B.TXT", "SiHP8N50D_HS_Rev_B.TXT (switching loss)"),
    (PROSP / "sources/sprint06c/SiHP8N50D_modelguide/original.pdf", "SiHP8N50D model guide PDF"),
    (PROSP / "sources/sprint06c/SiHP8N50D_datasheet/original.pdf", "SiHP8N50D datasheet PDF"),
    (PROSP / "sources/sprint06c/manifest_vishay.json", "manifest_vishay.json"),
    (PROSP / "sources/sprint06b/ST_model_cn/ST_model_cn.zip", "STP9NK50Z model zip (ST model_cn)"),
    (PROSP / "sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib", "stp9nk50z.lib"),
    (PROSP / "sources/sprint06b/ST_model_cn/../manifest.json", "sources/sprint06b/manifest.json"),
    (PROSP / "sources/sprint06c/STP7N65M2_datasheet/original.pdf", "STP7N65M2 datasheet PDF"),
    (PROSP / "sources/sprint06c/STP7N65M2_model_url1/source.json", "STP7N65M2 model source.json (url1)"),
    (PROSP / "sources/sprint06c/STP7N65M2_model_url2/source.json", "STP7N65M2 model source.json (url2)"),
    (PROSP / "sources/sprint06c/manifest.json", "sources/sprint06c/manifest.json"),
    (PROSP / "sources/sprint06c/IPP60R360P7_datasheet/original.pdf", "IPP60R360P7 datasheet PDF (Infineon)"),
    (PROSP / "sources/sprint06c/Infineon_product.html", "Infineon_product.html (0 bytes)"),
    (PROSP / "sources/sprint06c/SiHP8N50D_datasheet/source.json", "SiHP8N50D_datasheet/source.json"),
    (PROSP / "sources/sprint06c/SiHP8N50D_model/source.json", "SiHP8N50D_model/source.json"),
    (PROSP / "sources/sprint06c/SiHP8N50D_thermal/original.pdf", "SiHP8N50D thermal RC PDF"),
    (PROSP / "sources/sprint06c/SiHP8N50D_thermal/source.json", "SiHP8N50D_thermal/source.json"),
    (HIST / "sources/sprint06c/SS14/original.lib", "SS14 vendor lib (historical)"),
    (HIST / "sources/sprint06c/SS14/source.json", "SS14 source.json (historical)"),
    (PROSP / "sources/sprint06b/Vishay_US1G/source.json", "Vishay US1G source.json"),
    (PROSP / "sources/sprint06b/Vishay_US1G/us1g.txt", "us1g.txt (Vishay US1 design page text)"),
    (PROSP / "sources/sprint06b/Diodes_US1G/Diodes_US1G.txt", "Diodes_US1G.txt"),
    (PROSP / "sources/sprint06b/manifest.json", "sources/sprint06b/manifest.json"),
    (PROSP / "sources/sprint06b/interface_sources.json", "sources/sprint06b/interface_sources.json"),
    (PROSP / "sources/US1.pdf", "US1 datasheet PDF (Vishay)"),
    (PROSP / "sources/sprint06c/manifest_controller_additions.json", "sprint06c controller additions (historical only)"),
]
for f, nm in DEV:
    p = Path(os.path.normpath(f))
    if p.exists():
        rec("device", nm, p, sha256_file(p), p.stat().st_size)
    else:
        rec("device", nm, p, None, None, missing=True)

# -------------------------------------------------------------- inductors
IND = [
    (PROSP / "sources/MSS1260.pdf", "Coilcraft MSS1260 series PDF"),
    (PROSP / "sources/MSS1260.txt", "Coilcraft MSS1260 text"),
    (PROSP / "sources/MSS1583.pdf", "Coilcraft MSS1583 series PDF"),
    (PROSP / "sources/MSS1583.txt", "Coilcraft MSS1583 text"),
    (PROSP / "sources/sprint06/MSS1583/MSS1583.pdf", "MSS1583 PDF (sprint06 copy)"),
    (PROSP / "sources/sprint06b/MSS1583_current/original.pdf", "MSS1583 PDF (sprint06b current copy)"),
    (PROSP / "sources/sprint06b/MSS1583_current/source.json", "MSS1583_current/source.json"),
    (PROSP / "sources/manifest.json", "sources/manifest.json"),
    (PROSP / "sources/sprint06b/interface_sources.json", "sources/sprint06b/interface_sources.json"),
]
for f, nm in IND:
    p = Path(os.path.normpath(f))
    if p.exists():
        rec("inductor", nm, p, sha256_file(p), p.stat().st_size)
    else:
        rec("inductor", nm, p, None, None, missing=True)

# -------------------------------------------------- simulators / ngspice tools
SIM = [
    (Path(r"D:/PROJECTS/dsharness/QS30-1/tools/ngspice47/Spice64/bin/ngspice_con.exe"), "ngspice_con.exe"),
]
for f, nm in SIM:
    if f.exists():
        rec("simulator", nm, f, sha256_file(f), f.stat().st_size)
    else:
        rec("simulator", nm, f, None, None, missing=True)

# ------------------------------------------------------------- duplicate check
# show whether the sim-time vendor.lib copies still equal the original bytes
dupes = []
for d in sorted((PROSP / "sim").glob("*/*")):
    if not d.is_dir():
        continue
    for libname in ("vendor.lib", "st.lib"):
        p = d / libname
        if p.exists():
            dupes.append(
                {
                    "path": str(p).replace("\\", "/"),
                    "sha256": sha256_file(p),
                }
            )

manifest = {
    "task_id": "vendor_models",
    "generated_by": "extract_and_hash.py",
    "extraction_note": "vendor_bytes/* contain byte-identical payloads read out of the "
                       "signed ADI distribution archives with Python zipfile; "
                       "no model text was edited, re-encoded or reformatted.",
    "lt3757a_extracted": extracted,
    "records": records,
    "historical_sim_vendor_lib_copies": dupes,
}
(OUT / "hash_manifest_raw.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("records:", len(records))
for e in extracted:
    print(e["member"], e["sha256"], e["bytes"])
print("missing:", [r["name"] for r in records if r.get("missing")])
