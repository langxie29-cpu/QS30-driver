"""Provenance scan of the READ-ONLY historical workspace (QS30-1).

Labels every file under projects/QS30-9_24V (docs, design, sim, sources,
safety_r1) as COMMITTED_CLEAN / TRACKED_MODIFIED / UNTRACKED / TRACKED_DELETED
against the historical repo's own git index, and records sha256 of actual bytes.
Read-only: nothing is written into the historical workspace.
"""
import hashlib
import json
import os

HROOT = r"D:/PROJECTS/dsharness/QS30-1"
RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"
OUT = os.path.join(RUN, "provenance_scan_historical.json")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_sha(p):
    h = hashlib.sha1()
    data = open(p, "rb").read()
    h.update(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def main():
    with open(os.path.join(RUN, "index_entries_historical.json"), encoding="utf-8") as f:
        idx = {e["path"]: e for e in json.load(f)["entries"]}
    base = os.path.join(HROOT, "projects", "QS30-9_24V").replace("\\", "/")
    recs = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, HROOT).replace("\\", "/")
            ent = idx.get(rel)
            try:
                act = git_blob_sha(fp)
                sh = sha256_file(fp)
                sz = os.path.getsize(fp)
            except OSError as exc:
                recs.append({"path": rel, "state": "UNREADABLE", "error": str(exc)[:160]})
                continue
            rec = {"path": rel, "sha256": sh, "size": sz}
            if ent is None:
                rec["state"] = "UNTRACKED"
            elif ent["blob"] == act:
                rec["state"] = "COMMITTED_CLEAN"
                rec["blob"] = ent["blob"]
            else:
                rec["state"] = "TRACKED_MODIFIED"
                rec["blob_index"] = ent["blob"]
            recs.append(rec)
    seen = {r["path"] for r in recs}
    for p, e in idx.items():
        if p.startswith("projects/QS30-9_24V/") and p not in seen:
            recs.append({"path": p, "state": "TRACKED_DELETED", "blob": e["blob"]})
    summ = {}
    for r in recs:
        summ[r["state"]] = summ.get(r["state"], 0) + 1
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"summary": summ, "files": recs}, f, indent=1)
    lines = ["HISTORICAL projects/QS30-9_24V summary: %s" % json.dumps(summ), ""]
    lines.append("== S06C/D/E/F + safety_r1 artefacts, NOT committed-clean ==")
    keys = ("sprint06c", "sprint06d", "sprint06e", "sprint06f", "S06C", "S06D",
            "S06E", "S06F", "s06c", "s06d", "s06e", "s06f", "safety_r1")
    for r in sorted(recs, key=lambda x: x["path"]):
        if r["state"] == "COMMITTED_CLEAN":
            continue
        if any(k in r["path"] for k in keys):
            lines.append("%-18s %s" % (r["state"], r["path"]))
    lines.append("")
    lines.append("== ALL non-committed-clean (any path) ==")
    for r in sorted(recs, key=lambda x: x["path"]):
        if r["state"] != "COMMITTED_CLEAN":
            lines.append("%-18s %s" % (r["state"], r["path"]))
    lines.append("")
    lines.append("== committed-clean S06C/D/E/F docs (tracked) ==")
    for r in sorted(recs, key=lambda x: x["path"]):
        if r["state"] == "COMMITTED_CLEAN" and any(k in r["path"] for k in keys):
            lines.append("COMMITTED_CLEAN    %s" % r["path"])
    with open(os.path.join(RUN, "provenance_scan_historical.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
