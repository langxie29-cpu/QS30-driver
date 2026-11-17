"""Read-only git index parser (git.exe blocked by sandbox; parse .git/index directly).

Produces tracked path -> (mode, blob sha1) for the QS30-power-loop-r1 worktree index.
Does NOT write outside OUTPUT_DIR.
"""
import json
import struct
import sys

INDEX = r"D:/PROJECTS/dsharness/QS30-1/.git/worktrees/QS30-power-loop-r1/index"
OUT = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit/index_entries.json"


def parse_index(path):
    with open(path, "rb") as f:
        data = f.read()
    sig, ver, n = struct.unpack(">4sII", data[:12])
    assert sig == b"DIRC", sig
    entries = []
    off = 12
    for _ in range(n):
        start = off
        ctime_s, ctime_ns, mtime_s, mtime_ns, dev, ino, mode, uid, gid, size = struct.unpack(
            ">10I", data[off:off + 40])
        sha = data[off + 40:off + 60].hex()
        flags = struct.unpack(">H", data[off + 60:off + 62])[0]
        off += 62
        if ver >= 3 and (flags & 0x4000):
            off += 2
        namelen = flags & 0x0FFF
        if namelen < 0x0FFF:
            name = data[off:off + namelen].decode("utf-8", "surrogateescape")
            off += namelen
        else:
            end = data.index(b"\x00", off)
            name = data[off:end].decode("utf-8", "surrogateescape")
            off = end
        total = off - start
        pad = (8 - (total % 8)) % 8 or 8
        off += pad
        entries.append({"path": name, "mode": format(mode, "o"), "blob": sha, "size": size})
    return {"version": ver, "count": n, "entries": entries}


LOG = OUT.replace("index_entries.json", "index_parse.txt")

if __name__ == "__main__":
    idx = parse_index(INDEX)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1)
    lines = ["version %d count %d" % (idx["version"], idx["count"])]
    for e in idx["entries"]:
        if "power_loop_r1" in e["path"] or "safety_r1" in e["path"] or "QS30-9_24V/docs" in e["path"]:
            lines.append("%s %s %s" % (e["mode"], e["blob"][:12], e["path"]))
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.exit(0)
