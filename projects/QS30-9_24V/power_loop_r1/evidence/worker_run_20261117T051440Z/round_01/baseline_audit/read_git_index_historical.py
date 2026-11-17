"""Read-only git index parser for the HISTORICAL workspace (QS30-1).

Parses D:/PROJECTS/dsharness/QS30-1/.git/index and indexes worktrees so that
S06C/D/E/F artefacts in the read-only historical workspace can be labelled
committed vs uncommitted without launching git.exe (blocked by sandbox).
"""
import json
import os
import struct
import sys

GITDIR = r"D:/PROJECTS/dsharness/QS30-1/.git"
RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"


def parse_index(path):
    with open(path, "rb") as f:
        data = f.read()
    sig, ver, n = struct.unpack(">4sII", data[:12])
    assert sig == b"DIRC", sig
    entries = []
    off = 12
    for _ in range(n):
        start = off
        (ctime_s, ctime_ns, mtime_s, mtime_ns, dev, ino, mode, uid, gid,
         size) = struct.unpack(">10I", data[off:off + 40])
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
        off += (8 - (total % 8)) % 8 or 8
        entries.append({"path": name, "mode": format(mode, "o"),
                        "blob": sha, "size": size})
    return {"version": ver, "count": n, "entries": entries}


if __name__ == "__main__":
    idx = parse_index(os.path.join(GITDIR, "index"))
    with open(os.path.join(RUN, "index_entries_historical.json"), "w",
              encoding="utf-8") as f:
        json.dump(idx, f, indent=1)
    out = ["HISTORICAL index version %d count %d" % (idx["version"], idx["count"])]
    keys = ("sprint06c", "sprint06d", "sprint06e", "sprint06f", "S06C", "S06D",
            "S06E", "S06F", "s06c", "s06d", "s06e", "s06f", "safety_r1")
    for e in idx["entries"]:
        if any(k in e["path"] for k in keys):
            out.append("%s %s %s" % (e["mode"], e["blob"][:12], e["path"]))
    with open(os.path.join(RUN, "index_parse_historical.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    sys.exit(0)
