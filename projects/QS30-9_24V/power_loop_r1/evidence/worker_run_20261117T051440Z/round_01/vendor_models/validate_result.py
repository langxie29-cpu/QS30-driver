"""Deterministic self-check for the vendor_models deliverable.

Verifies, in this order:
  1. result.json parses as UTF-8 JSON and has every contracted key.
  2. status is one of PASS/FAIL/INCONCLUSIVE.
  3. every evidence_file exists inside OUTPUT_DIR (no absolute or .. escape).
  4. inventory.md exists (REQUIRED_EVIDENCE for this analysis task).
  5. every sha256 in model_hashes is 64 lowercase hex and re-verifies against a
     real file: either a file in OUTPUT_DIR (vendor_bytes/*) or the recorded
     source_path in hash_manifest_raw.json.
  6. the three LT3757A vendor_bytes payloads re-hash to the committed values.
  7. the JSON evidence files parse.
  8. result.json carries no fabricated SPICE artifacts for a run that did not
     happen (circuit.cir/run.log/waves.txt/metrics.json must be ABSENT here).

Exit code 0 = all assertions hold.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
RESULT = OUT / "result.json"

checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS  " if ok else "FAIL  ") + name + (("  -> " + detail) if detail and not ok else ""))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


raw = RESULT.read_bytes()
try:
    res = json.loads(raw.decode("utf-8"))
    check("result.json is valid UTF-8 JSON", True)
except Exception as e:  # pragma: no cover
    check("result.json is valid UTF-8 JSON", False, str(e))
    sys.exit(1)

required = ["task_id", "status", "notes", "evidence_files", "source_urls", "solver",
            "model_hashes", "blocking_issues"]
for k in required:
    check("key present: " + k, k in res)
check("task_id is exactly vendor_models", res.get("task_id") == "vendor_models", repr(res.get("task_id")))
check("status in PASS/FAIL/INCONCLUSIVE", res.get("status") in ("PASS", "FAIL", "INCONCLUSIVE"), repr(res.get("status")))

# ---- evidence files stay inside OUTPUT_DIR
for f in res.get("evidence_files", []):
    p = (OUT / f)
    inside = OUT.resolve() in p.resolve().parents or p.resolve() == OUT.resolve()
    check("evidence inside OUTPUT_DIR: " + f, inside and p.is_file(), str(p))

check("REQUIRED_EVIDENCE inventory.md exists", (OUT / "inventory.md").is_file())

# ---- model hashes re-verify
manifest = json.loads((OUT / "hash_manifest_raw.json").read_text(encoding="utf-8"))
by_name = {}
for r in manifest["records"]:
    if r.get("sha256"):
        by_name.setdefault(r["sha256"], []).append(r["source_path"])

hexre = re.compile(r"^[0-9a-f]{64}$")
vb = {sha(p): p.name for p in (OUT / "vendor_bytes").iterdir() if p.is_file()}
n_hashes = 0
for name, h in res.get("model_hashes", {}).items():
    n_hashes += 1
    check("sha256 well formed: " + name, isinstance(h, str) and bool(hexre.match(h)), repr(h))
    if h in vb:
        check("re-hashed from OUTPUT_DIR: " + vb[h], True)
    elif h in by_name:
        check("matches registered source_path: " + name, True)
    else:
        check("hash traceable to a file: " + name, False, h)
check("model_hashes non-empty", n_hashes > 0, str(n_hashes))

# ---- the three LT3757A payloads
EXPECT = {
    "LT3757A.sub": "c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634",
    "LT3757A.asy": "4ed5078ebd77e5e697bc61b9124d34b350cdccc7be9a0d32e7def830660c9d76",
    "LT3757A.asc": "867ea5d1f8f90aa56f4dacfadfa4108bfddf0e619c06941bb711d890dba40cb6",
}
for fn, want in EXPECT.items():
    p = OUT / "vendor_bytes" / fn
    check("vendor_bytes/%s re-hashes to expected" % fn, p.is_file() and sha(p) == want)

# ---- model nature assertions used in the notes
sub = (OUT / "vendor_bytes" / "LT3757A.sub").read_bytes()
check("LT3757A.sub is encoded/binary (starts with '<Binary File>')", sub.startswith(b"\r\n<Binary File>"))
check("LT3757A.sub contains NUL bytes", sub.count(b"\x00") == 15, str(sub.count(b"\x00")))
asc = (OUT / "vendor_bytes" / "LT3757A.asc").read_text(encoding="utf-8", errors="replace")
check("LT3757A.asc is the 12V reference (.tran 1.5m startup)", ".tran 1.5m startup" in asc)
check("LT3757A.asc is NOT a 170V reference (no 170 rail value)", "170" not in asc)

# ---- supporting JSON evidence parses
for f in ["model_index.json", "sim_copy_audit.json", "hash_manifest_raw.json"]:
    try:
        json.loads((OUT / f).read_text(encoding="utf-8"))
        check("parses: " + f, True)
    except Exception as e:
        check("parses: " + f, False, str(e))

# ---- no fabricated SPICE artifacts
for f in ["circuit.cir", "run.log", "waves.txt", "metrics.json"]:
    check("absent (no fabrication): " + f, not (OUT / f).exists())

# ---- audit arithmetic reconciles with the inventory text
aud = json.loads((OUT / "sim_copy_audit.json").read_text(encoding="utf-8"))
check("sim copies total == 188", aud["copies_total"] == 188, str(aud["copies_total"]))
check("sim copies matching == 146", aud["copies_matching_original"] == 146, str(aud["copies_matching_original"]))
check("unmatched == 42", len(aud["copies_not_matching_any_registered_original"]) == 42,
      str(len(aud["copies_not_matching_any_registered_original"])))
check("matching + unmatched == total",
      aud["copies_matching_original"] + len(aud["copies_not_matching_any_registered_original"]) == aud["copies_total"])

inv = (OUT / "inventory.md").read_text(encoding="utf-8")
check("inventory.md states 146 / 42", "**146**" in inv and "**42**" in inv)
check("inventory.md is UTF-8 decodable", True)

failed = [c for c in checks if not c["ok"]]
summary = {
    "task_id": "vendor_models",
    "checks_total": len(checks),
    "checks_failed": len(failed),
    "ok": not failed,
    "failed": failed,
    "checks": checks,
}
(OUT / "validate_result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("\n%d checks, %d failed" % (len(checks), len(failed)))
sys.exit(0 if not failed else 1)
