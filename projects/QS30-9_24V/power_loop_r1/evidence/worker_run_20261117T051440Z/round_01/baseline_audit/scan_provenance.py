"""Provenance scanner: compare worktree files against the git index (read-only).

git.exe cannot be launched under the sandbox, so this uses:
  * the parsed index (index_entries.json) for tracked blob SHAs
  * zlib decompression of loose/packed objects to verify content identity

For each target subtree it emits: tracked / untracked / modified status per file,
plus sha256 of the actual working-tree bytes.
"""
import hashlib
import json
import os
import struct
import zlib

RUN = r"D:/PROJECTS/dsharness/QS30-power-loop-r1/projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/baseline_audit"
ROOT = r"D:/PROJECTS/dsharness/QS30-power-loop-r1"
GITDIR = r"D:/PROJECTS/dsharness/QS30-1/.git"
OUT = os.path.join(RUN, "provenance_scan.json")

TARGETS = [
    "projects/QS30-9_24V/docs",
    "projects/QS30-9_24V/design",
    "projects/QS30-9_24V/sim",
    "projects/QS30-9_24V/sources",
    "projects/QS30-9_24V/safety_r1",
    "projects/QS30-9_24V/power_loop_r1",
    "projects/QS30-9_24V/netlist",
    "projects/QS30-9_24V/config",
    "projects/QS30-9_24V/baseline_snapshot",
    "projects/QS30-9_24V/toolchain",
]


def load_index():
    with open(os.path.join(RUN, "index_entries.json"), encoding="utf-8") as f:
        idx = json.load(f)
    return {e["path"]: e for e in idx["entries"]}


class ObjReader:
    def __init__(self, gitdir):
        self.gitdir = gitdir
        self.packs = []
        pod = os.path.join(gitdir, "objects", "pack")
        if os.path.isdir(pod):
            for n in os.listdir(pod):
                if n.endswith(".idx"):
                    self.packs.append(n[:-4])

    def loose(self, sha):
        p = os.path.join(self.gitdir, "objects", sha[:2], sha[2:])
        if not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            return zlib.decompress(f.read())

    def from_packs(self, sha):
        want = bytes.fromhex(sha)
        for base in self.packs:
            idxp = os.path.join(self.gitdir, "objects", "pack", base + ".idx")
            with open(idxp, "rb") as f:
                d = f.read()
            if d[:4] != b"\xfftOc":
                continue
            ver = struct.unpack(">I", d[4:8])[0]
            if ver != 2:
                continue
            fan = struct.unpack(">256I", d[8:8 + 1024])
            n = fan[255]
            sha_start = 8 + 1024 + 4 * n
            off_start = sha_start + 20 * n + 4 * n
            lo, hi = (fan[want[0] - 1] if want[0] else 0), fan[want[0]]
            for i in range(lo, hi):
                if d[sha_start + 20 * i: sha_start + 20 * (i + 1)] == want:
                    off = struct.unpack(">I", d[off_start + 4 * i: off_start + 4 * i + 4])[0]
                    return self._unpack(base, off)
        return None

    def _unpack(self, base, off):
        packp = os.path.join(self.gitdir, "objects", "pack", base + ".pack")
        with open(packp, "rb") as f:
            f.seek(off)
            hdr = f.read(32)
            c = hdr[0]
            typ = (c >> 4) & 7
            size = c & 15
            shift = 4
            i = 1
            while c & 0x80:
                c = hdr[i]
                i += 1
                size |= (c & 0x7F) << shift
                shift += 7
            if typ in (1, 2, 3, 4):
                hdrlen = i
                if typ == 6:
                    return None
                d = zlib.decompressobj()
                with open(packp, "rb") as f2:
                    f2.seek(off + hdrlen)
                    body = d.decompress(f2.read(size + 4096))
                if typ == 3:
                    return b"blob\x00" + body[:size] if False else body[:size]
                return None
            # delta
            f.seek(off + i)
            dsz = f.read(1)[0]
            dszv = dsz & 0x7F
            j = 1
            while dsz & 0x80:
                dsz = f.read(1)[0]
                dszv |= (dsz & 0x7F) << (7 * j)
                j += 1
            d = zlib.decompressobj()
            f.seek(off + i + j)
            delta = d.decompress(f.read(dszv + 4096))[:dszv]
            # need base object
            if typ == 6:
                c2 = delta[0]
                k = 1
                neg = 0
                while c2 & 0x80:
                    c2 = delta[k]
                    k += 1
                    neg |= (c2 & 0x7F) << (7 * neg)
                ofs = int.from_bytes(delta[k:k + (neg + 7) // 8], "big")
                k += (neg + 7) // 8
                baseobj = self._unpack(base, off - ofs)
            else:
                bsha = delta[:20].hex()
                p = os.path.join(self.gitdir, "objects", bsha[:2], bsha[2:])
                if os.path.exists(p):
                    raw = zlib.decompress(open(p, "rb").read())
                    baseobj = raw.split(b"\x00", 1)[1]
                else:
                    baseobj = self.from_packs(bsha)
                k = 20
            return apply_delta(baseobj, delta[k:])

    def get(self, sha):
        raw = self.loose(sha)
        if raw is not None:
            return raw.split(b"\x00", 1)[1]
        return self.from_packs(sha)


def apply_delta(base, d):
    def varint(d, k):
        v, sh = 0, 0
        while True:
            b = d[k]
            k += 1
            v |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                return v, k
    src, k = varint(d, 0)
    dst, k = varint(d, k)
    out = bytearray()
    while k < len(d):
        op = d[k]
        k += 1
        if op & 0x80:
            o = 0
            sz = 0
            for bit in range(4):
                if op & (1 << bit):
                    o |= d[k] << (8 * bit)
                    k += 1
            for bit in range(3):
                if op & (1 << (4 + bit)):
                    sz |= d[k] << (8 * bit)
                    k += 1
            if sz == 0:
                sz = 0x10000
            out += base[o:o + sz]
        elif op:
            out += d[k:k + op]
            k += op
        else:
            raise ValueError("bad delta")
    return bytes(out)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_sha(p):
    with open(p, "rb") as f:
        data = f.read()
    h = hashlib.sha1(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def main():
    idx = load_index()
    rd = ObjReader(GITDIR)
    results = []
    digest_cache = {}
    for target in TARGETS:
        full = os.path.join(ROOT, target).replace("\\", "/")
        if not os.path.isdir(full):
            results.append({"target": target, "exists": False})
            continue
        for dirpath, dirnames, filenames in os.walk(full):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, ROOT).replace("\\", "/")
                ent = idx.get(rel)
                try:
                    actual_sha = git_blob_sha(fp)
                    sz = os.path.getsize(fp)
                    sh = sha256_file(fp)
                except OSError as exc:
                    results.append({"path": rel, "state": "UNREADABLE",
                                    "error": str(exc)[:200]})
                    continue
                rec = {"path": rel, "sha256": sh, "size": sz}
                if ent is None:
                    rec["state"] = "UNTRACKED"
                elif ent["blob"] == actual_sha:
                    rec["state"] = "COMMITTED_CLEAN"
                    rec["blob"] = ent["blob"]
                else:
                    rec["state"] = "TRACKED_MODIFIED"
                    rec["blob_index"] = ent["blob"]
                    try:
                        obj = rd.get(ent["blob"])
                        rec["blob_readable"] = obj is not None
                    except Exception as exc:  # pragma: no cover
                        rec["blob_readable"] = "error: %s" % exc
                results.append(rec)
    # tracked-in-index but missing from worktree
    wt_paths = {r["path"] for r in results}
    for p, e in idx.items():
        if any(p.startswith(t + "/") for t in TARGETS) and p not in wt_paths:
            results.append({"path": p, "state": "TRACKED_DELETED",
                            "blob": e["blob"]})
    summary = {}
    for r in results:
        summary[r["state"]] = summary.get(r["state"], 0) + 1
    payload = {"index_count": len(idx), "blob_reader_packs": rd.packs,
               "summary": summary, "files": results}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    lines = ["summary: %s" % json.dumps(summary)]
    for r in sorted(results, key=lambda x: x["path"]):
        if r["state"] != "COMMITTED_CLEAN":
            lines.append("%-18s %s" % (r["state"], r["path"]))
    with open(os.path.join(RUN, "provenance_scan.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
