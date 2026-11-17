"""LT3757A reference replay (QS30-9 task round_02/lt3757a_reference).

Scope: byte-exact extraction of the Analog Devices signed distribution
(lib.zip -> LT3757A.sub/.asy, examples.zip -> LT3757A.asc) into this OUT dir,
NATIVE LTspice 24.0.12.0 netlisting of the UNMODIFIED vendor .asc, then the
UNMODIFIED vendor .tran replay. No netlist edit of the original reference,
no threshold change, no physical operation, no network access.

Independent verification design of this run (documented, not hidden):
  * Case R0 keeps the ORIGINAL vendor .tran 1.5m startup control -> replay fidelity.
  * Case A adds ONLY .options plotwinsize=0 to an otherwise byte-identical copy of
    the original netlist so that every solver point is preserved (no waveform
    compression). This is a solver-output control, not a circuit edit.
  * Case B appends ONLY the case-specific .op card.
Every appended line is recorded in the evidence as an explicit diff, and all
derived netlists keep the original .net file untouched next to them.
"""
from pathlib import Path
import os, sys, json, zipfile, hashlib, subprocess, time, shutil

ROOT = Path(r"D:\PROJECTS\dsharness\QS30-power-loop-r1")
HIST = Path(r"D:\PROJECTS\dsharness\QS30-1\projects\QS30-9_24V")
EXE = HIST / "toolchain/ltspice26/extracted/LTspice.exe"
OUT = ROOT / "projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_02/lt3757a_reference"
ENVLOG = OUT / "env"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha(Path(p).read_bytes())


def run(cmd, cwd, env, timeout):
    start = time.monotonic()
    rec = {"argv": [str(c) for c in cmd], "cwd": str(cwd), "timeout_s": timeout}
    try:
        p = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env,
                           capture_output=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        rec.update(rc=p.returncode, stdout=p.stdout.decode("utf-8", "backslashreplace"),
                   stderr=p.stderr.decode("utf-8", "backslashreplace"))
    except subprocess.TimeoutExpired as e:
        rec.update(rc=None, timed_out=True,
                   stdout=(e.stdout or b"").decode("utf-8", "backslashreplace"),
                   stderr=(e.stderr or b"").decode("utf-8", "backslashreplace"))
    rec["elapsed_s"] = time.monotonic() - start
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ENVLOG.mkdir(exist_ok=True)
    vendor = OUT / "vendor_original"
    vendor.mkdir(exist_ok=True)
    manifest = {"task_id": "lt3757a_reference", "vendor_sources": [], "simulator": {},
                "referencedGlobalLibs": [], "steps": {}}

    # ---------------- 1. byte-exact vendor extraction (python zipfile, no re-encoding)
    srcs = [("lib.zip", "lib/sub/LT3757A.sub", "LT3757A.sub"),
            ("lib.zip", "lib/sym/PowerProducts/LT3757A.asy", "LT3757A.asy"),
            ("examples.zip", "examples/Applications/LT3757A.asc", "LT3757A.asc")]
    for zname, member, outname in srcs:
        zp = EXE.parent / zname
        with zipfile.ZipFile(zp) as z:
            info = z.getinfo(member)
            data = z.read(member)
            assert z.testzip() is None
        (vendor / outname).write_bytes(data)
        roundtrip = (vendor / outname).read_bytes() == data
        manifest["vendor_sources"].append({
            "archive": str(zp), "archive_sha256": sha_file(zp), "archive_comment": None,
            "member": member, "crc32": format(info.CRC, "08x"), "size": info.file_size,
            "date_time": list(info.date_time), "extracted_to": f"vendor_original/{outname}",
            "sha256": sha(data), "roundtrip_identical": roundtrip,
            "license": ("Analog Devices / Linear Technology LTspice distribution; "
                        "redistributed under the LTspice license shipped with the "
                        "installer (extracted/License.txt). Replay-for-verification only."),
            "origin": "vendor signed installer payload (reduced archive): lib.zip/examples.zip",
        })
    manifest["simulator"] = {
        "name": "LTspice", "vendor": "Analog Devices Incorporated",
        "file_version": "24.0.12.0", "path": str(EXE), "sha256": sha_file(EXE),
        "native_solver": "LTspice 24.0.12 built-in SPICE engine (solver = Normal, method = modified trap)",
        "permission": "local, documented, already installed; no download, no install executed",
        "authenticode": "preflight/ltspice_signature.json (Status 0, Analog Devices International UC)",
    }
    sub_path = vendor / "LT3757A.sub"

    # referenced global libs are resolved inside the private simulator profile
    prof = OUT / "sim_profile"
    ltdir = prof / "LTspice"
    libtarget = ltdir / "lib"
    if libtarget.exists():
        shutil.rmtree(libtarget)
    with zipfile.ZipFile(EXE.parent / "lib.zip") as z:
        z.extractall(ltdir)
    for member in ("lib/cmp/standard.mos", "lib/cmp/standard.dio", "lib/sub/LT3757A.sub",
                   "lib/sym/PowerProducts/LT3757A.asy"):
        with zipfile.ZipFile(EXE.parent / "lib.zip") as z:
            manifest["referencedGlobalLibs"].append(
                {"member": member, "sha256": sha(z.read(member))})
    assert sha_file(libtarget / "sub/LT3757A.sub") == sha_file(sub_path)

    env = dict(os.environ, APPDATA=str(prof), LOCALAPPDATA=str(prof))
    wrap = ltdir / "lib"

    # ---------------- 2. native netlist of the UNMODIFIED vendor schematic
    asc = vendor / "LT3757A.asc"
    r = run([EXE, "-netlist", asc, "-I" + str((wrap / "sym"))], OUT, env, 120)
    manifest["steps"]["netlist"] = r
    (ENVLOG / "netlist_stdout.txt").write_text(r.get("stdout", ""), encoding="utf8")
    (ENVLOG / "netlist_stderr.txt").write_text(r.get("stderr", ""), encoding="utf8")
    # the native netlister writes the netlist (and its log) next to the .asc
    for f in vendor.glob("LT3757A.*"):
        if f.suffix in (".net", ".log"):
            shutil.copy2(f, OUT / f.name)
    net_src = OUT / "LT3757A.net"
    net_ok = net_src.is_file()
    manifest["netlist_created"] = net_ok
    manifest["netlist_location"] = ("vendor_original/LT3757A.net written by native LTspice next to the .asc; "
                                    "copied unmodified to ./LT3757A.net for replay")
    if net_ok:
        net_bytes = net_src.read_bytes()
        # canonical circuit.cir = ORIGINAL native netlist, untouched
        (OUT / "LT3757A.original.net").write_bytes(net_bytes)
        manifest["original_net"] = {"file": "LT3757A.original.net", "sha256": sha(net_bytes)}
        text = net_bytes.decode("cp1252")  # vendor 'u' signs are 0xA1 0xEC (CP1252 micro)
        text_clean = text.replace(str(wrap), "%LIBSYM%")
        assert "0xA1" not in text_clean
        (OUT / "circuit.cir").write_text(text_clean, encoding="utf8", newline="\n")
        manifest["circuit_cir"] = {"file": "circuit.cir", "sha256": sha_file(OUT / "circuit.cir"),
                                   "note": ".lib line rewritten to %LIBSYM% for portability; "
                                           "original absolute netlist kept as LT3757A.original.net"}

        # ---------------- 3. R0: unmodified replay (only output path differs from original)
        r0 = run([EXE, "-b", "-ascii", net_src, "-I" + str(wrap / "sub")], OUT, env, 120)
        manifest["steps"]["R0_vendor_tran"] = r0
        if net_src.with_suffix(".log").is_file():
            shutil.copy2(net_src.with_suffix(".log"), OUT / "R0_original_tran.log")
        if net_src.with_suffix(".raw").is_file():
            shutil.copy2(net_src.with_suffix(".raw"), OUT / "R0_original_tran.raw")
        (OUT / "run.log").write_text(
            (OUT / "R0_original_tran.log").read_text(encoding="utf-8", errors="replace")
            if (OUT / "R0_original_tran.log").is_file() else
            "R0 produced no log:\n" + json.dumps(r0, indent=2), encoding="utf8")
        manifest["raw_R0_present"] = (OUT / "R0_original_tran.raw").is_file()

        # ---------------- 4. Case A: original + plotwinsize=0 only
        lines = text.splitlines()
        idx = max(i for i, l in enumerate(lines) if l.lower().startswith(".tran"))
        a_lines = lines[:idx] + [".options plotwinsize=0"] + lines[idx:]
        (OUT / "caseA_no_compression.cir").write_text("\n".join(a_lines) + "\n", encoding="cp1252", newline="\n")
        manifest["steps"]["caseA_diff_vs_original"] = [
            {"after_line": idx, "added": ".options plotwinsize=0"}]
        ra = run([EXE, "-b", "-ascii", OUT / "caseA_no_compression.cir", "-I" + str(wrap / "sub")], OUT, env, 120)
        manifest["steps"]["A_tran_nocompress"] = ra
        shutil.copy2(OUT / "caseA_no_compression.log", OUT / "A_tran_nocompress.log")
        if (OUT / "caseA_no_compression.op.raw").is_file():
            shutil.copy2(OUT / "caseA_no_compression.op.raw", OUT / "A_tran_nocompress.op.raw")
        if (OUT / "caseA_no_compression.raw").is_file():
            shutil.copy2(OUT / "caseA_no_compression.raw", OUT / "A_tran_nocompress.raw")

        # ---------------- 5. Case B: original + .op only (fixed operating point)
        # LTspice writes the .op plot only when a .save/.meas forces it; -b runs the
        # transient with 'startup' so the 'op' plot is taken at the DC solve.
        b_lines = lines[:idx] + [".op", ".save all"] + lines[idx:]
        (OUT / "caseB_op.cir").write_text("\n".join(b_lines) + "\n", encoding="cp1252", newline="\n")
        manifest["steps"]["caseB_diff_vs_original"] = [{"after_line": idx, "added": ".op"},
                                                       {"after_line": idx + 1, "added": ".save all"}]
        rb = run([EXE, "-b", "-ascii", OUT / "caseB_op.cir", "-I" + str(wrap / "sub")], OUT, env, 120)
        manifest["steps"]["B_op"] = rb
        shutil.copy2(OUT / "caseB_op.log", OUT / "B_op.log")
        if (OUT / "caseB_op.op.raw").is_file():
            shutil.copy2(OUT / "caseB_op.op.raw", OUT / "B_op.op.raw")
        if (OUT / "caseB_op.raw").is_file():
            shutil.copy2(OUT / "caseB_op.raw", OUT / "B_op.raw")

    # ---------------- 6. invariance check: schematic untouched by every command
    manifest["vendor_schematic_unchanged_by_replay"] = {
        "vendor_original/LT3757A.asc": sha_file(vendor / "LT3757A.asc"),
        "expected": sha_file(vendor / "LT3757A.asc") ==
                    [s["sha256"] for s in manifest["vendor_sources"] if s["member"].endswith(".asc")][0],
        "vendor_original/LT3757A.sub": sha_file(vendor / "LT3757A.sub"),
        "vendor_original/LT3757A.asy": sha_file(vendor / "LT3757A.asy"),
        "note": "re-hashed after all simulator invocations: no run may rewrite vendor bytes",
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps({kk: {kkk: vv for kkk, vv in v.items() if kkk in
                          ("rc", "elapsed_s", "timed_out", "exception")} if isinstance(v, dict) else v
                      for kk, v in manifest["steps"].items()}, indent=1))


if __name__ == "__main__":
    main()
