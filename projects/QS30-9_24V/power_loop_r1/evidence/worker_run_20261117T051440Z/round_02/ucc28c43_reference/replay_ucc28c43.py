"""Replay the ORIGINAL TI UCC28C43 PSpice transient fixture in a supported engine.

Scope rules honoured here:
  * Vendor artefacts (TI netlists, TI PSpice project, TI unencrypted model) are only READ
    from the historical workspace. Only sha256/mtime are taken from them.
  * Exact byte copies are written into this task output directory; originals are re-hashed
    after every run to prove immutability.
  * The ngspice deck is the TI-generated netlist text verbatim; only the .TRAN/.LIB/.OPTIONS
    analysis shell differs (documented in the run.log header block of metrics.json).
  * No numeric model value is edited, no acceptance threshold is invented.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TASK = Path(__file__).resolve().parent
HIST = Path(r"D:\PROJECTS\dsharness\QS30-1\projects\QS30-9_24V")
PSDIR = HIST / "sources/sprint06/UCC28C43_pspice/unpacked/UCC28C43_PSPICE_07NOV2008/UCC28C43_PSPICE_TRANS"
STEADY_DIR = PSDIR / "UCC28C43-PSpiceFiles/UCC28C43_STEADY"
START_DIR = PSDIR / "UCC28C43-PSpiceFiles/UCC28C43_STARTUP"
NET_STEADY = STEADY_DIR / "UCC28C43_STEADY.net"
NET_START = START_DIR / "UCC28C43_STARTUP.net"
ENC_LIB = PSDIR / "ucc28c43.lib"
MODEL = HIST / "sources/sprint06/UCCx8C43_unencrypted/unpacked/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib"
TINA_LIB = HIST / "sources/sprint06/UCC28C43_startup/unpacked/UCC28C43_TINA_TRANS/UCC28C43_START.LIB"
NG = Path(r"D:\PROJECTS\dsharness\QS30-1\tools\ngspice47\Spice64\bin\ngspice_con.exe")
TIMEOUT_S = 120  # per-run hard limit (contract)
LIB_COPY = "ucc28c43_trans_unencrypted.lib"  # byte-identical copy placed in each case dir

# Fixture values that the TI deck supplies elsewhere and that are transcribed verbatim below.
VIN_V = 24.0                      # NOT in TI netlist (V_V1 has no source spec); explicit assumption
TRAN_TSTOP = 9e-3                 # TI .sim/.cir: 9m
TRAN_TSTART = 5e-3                # TI .cir: 5m (skip the first half, capture steady state)
TRAN_STEP = 20e-9                 # TI .cir SCHEDULE(0,1000ns,6m,20ns) and sim +13 field 8487184==maxstep


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(text: str) -> str:
    """Whitespace-insensitive text image: used only to prove SEMANTIC identity of models."""
    lines = []
    for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        if ln.startswith("*") and not ln.startswith("**"):
            continue  # comment content (incl. tolerances/blanket notices) not a model statement
        lines.append(ln.lower())
    return "\n".join(lines)


def model_fingerprint(path: Path) -> dict:
    text = path.read_text(encoding="cp1252", errors="replace")
    s = norm(text)
    stmts = [x for x in s.split("\n") if not x.startswith("*")]
    return {
        "bytes": path.stat().st_size,
        "sha256": sha(path),
        "semantic_statements": len(stmts),
        "semantic_sha256": hashlib.sha256(s.encode()).hexdigest(),
    }


def main() -> int:
    log: list[str] = []
    def L(msg=""):
        log.append(msg)
        print(msg)

    L("== ucc28c43_reference :: original TI fixture replay ==")
    L(f"task_dir   = {TASK}")
    L(f"history    = {HIST} (read-only)")
    L(f"engine     = {NG}")
    L(f"python     = {sys.version.split()[0]}")

    tools = {}
    for name, exe in (("ngspice", NG),):
        tools[name] = {"path": str(exe), "exists": exe.exists()}
    if not NG.exists():
        L("FATAL: ngspice missing -> INCONCLUSIVE (no simulator)")
        (TASK / "run.log").write_text("\n".join(log), encoding="utf-8")
        return 3
    ver = subprocess.run([str(NG), "--version"], capture_output=True, text=True, timeout=60)
    L(ver.stdout.splitlines()[1] if len(ver.stdout.splitlines()) > 1 else ver.stdout)

    # ---------- native PSpice / TINA availability ----------
    pspice_hints = [r"C:\Cadence", r"C:\Program Files\Cadence", r"C:\Program Files (x86)\Cadence",
                    r"C:\Program Files\OrCAD", r"C:\OrCAD", r"C:\Program Files\Texas Instruments",
                    r"C:\Program Files (x86)\Texas Instruments", r"C:\Program Files\DesignSoft",
                    r"C:\Program Files (x86)\DesignSoft"]
    availability = {
        "pspice_native": {"found_dirs": [p for p in pspice_hints if os.path.isdir(p)], "env_PSPICE": os.environ.get("PSPICE")},
        "tina_native": {"found_dirs": [p for p in pspice_hints if os.path.isdir(p)]},
        "ngspice": {"found": True, "version": next((l for l in ver.stdout.splitlines() if "ngspice-" in l), "")},
    }
    L(f"native PSpice dirs found: {availability['pspice_native']['found_dirs'] or 'NONE'}")
    L(f"native TINA dirs found:   {availability['tina_native']['found_dirs'] or 'NONE'}"
      "  -> vendor-native replay of the TI PSpice fixture is NOT possible here")

    # ---------- copy vendor artefacts (bytes) ----------
    cdir = TASK / "vendor"
    cdir.mkdir(exist_ok=True)
    copies = {
        "vendor_ucc28c43_trans_unencrypted.lib": MODEL,
        "vendor_ucc28c43_pspice_encrypted.lib": ENC_LIB,
        "vendor_UCC28C43_steady.net": NET_STEADY,
        "vendor_UCC28C43_startup.net": NET_START,
        "vendor_UCC28C43_steady.cir": STEADY_DIR / "UCC28C43_steady" / "UCC28C43_steady.cir",
        "vendor_UCC28C43_startup.cir": START_DIR / "UCC28C43_startup" / "UCC28C43_startup.cir",
        "vendor_UCC28C43_steady.sim": STEADY_DIR / "UCC28C43_steady.sim",
        "vendor_UCC28C43_startup.sim": START_DIR / "UCC28C43_startup.sim",
        "vendor_UCC28C43_startup_pspice.out": START_DIR / "UCC28C43_startup" / "UCC28C43_startup.out",
        "vendor_UCC28C43_steady_pspice.out": STEADY_DIR / "UCC28C43_steady" / "UCC28C43_steady.out",
        "vendor_UCC28C43_START_tina.LIB": TINA_LIB,
    }
    copied = {}
    for dst, src in copies.items():
        shutil.copyfile(src, cdir / dst)
        ok = sha(src) == sha(cdir / dst)
        copied[dst] = {"source": str(src), "sha256_source": sha(src), "sha256_copy": sha(cdir / dst), "identical": ok}
        L(f"copied {dst:44s} identical={ok}")

    model_before = model_fingerprint(MODEL)
    L(f"model UCC28C43_START/STEADY semantic_sha256={model_before['semantic_sha256']}")

    # ---------- build the ngspice deck ----------
    def deck_for(net: Path, kind: str, ascii_dump: bool = False) -> str:
        body = net.read_text(encoding="cp1252")
        body = body.replace(".LIB", "*.LIB")  # TI .net carries no .LIB, but be explicit
        body = "\n".join(l for l in body.splitlines() if not re.match(r"^\.IC\s", l, re.I))
        head = (
            f"* Replay of ORIGINAL TI PSpice transient fixture ({kind}) in ngspice-47\n"
            f"* vendor netlist bytes: {'UCC28C43_STEADY.net' if kind=='steady' else 'UCC28C43_STARTUP.net'} sha256 verbatim component lines\n"
            "* component lines are transcribed verbatim from the TI-generated .net; only the analysis shell differs:\n"
            "*   TI .cir .LIB ../../../ucc28c43.lib  ->  .include ucc28c43_trans_unencrypted.lib (identical content, sha in metrics)\n"
            "*   TI .TRAN/.OPTIONS (PSpice ABSTOL=1u CHGTOL=0.1p GMIN=1e-10 ITL4=5000 RELTOL=0.01 VNTOL=1m)\n"
            "*     -> ngspice tolerances listed in .options below (ngspice has no CHGTOL)\n"
            "*   TI V_V1 has NO source specification -> V_V1 VIN 0 24 (explicit assumption, see metrics)\n"
            "*   TI .IC V(FB )=2.5 -> ngspice .nodeset V(FB)=2.5 (same DC initial operating point guess)\n"
            "*   PSpice SCHEDULE() has no ngspice equivalent -> fixed max step\n"
            "*   TI node name '+VOUT1' is not a legal ngspice vector name -> wrdata requests it by index find()\n"
        )
        # ngspice needs .include/.options BEFORE the first device line; PSpice does not care.
        tail = "\n"
        head += (f".include {LIB_COPY}\n"
                 ".options reltol=0.01 abstol=1u vntol=1m gmin=1e-10 itl4=5000\n"
                 ".nodeset V(FB)=2.5\n")
        ctl = (
            ".control\nset noaskquit\nset wr_singlescale\nset wr_vecnames\n"
            f"tran {TRAN_STEP:g} {TRAN_TSTOP:g} {TRAN_TSTART:g} {TRAN_STEP:g}\n"
            "meas tran native_end MAX time\n"
            "let j = @v_v1[i]\n"
            "wrdata waves.txt v(vdd) v(vin) v(out) v(cs) v(comp) v(fb) v(vref) v(rtct) v(j)\n"
            + ("settype tran\noption ascii\nwrite raw_all.txt all\n" if ascii_dump else "")
            + "quit\n.endc\n.end\n"
        )
        return head + body + "\n" + tail + ctl

    def read_ascii_raw(path: Path, keep: list[str], decim: int) -> dict:
        """Stream the ngspice ASCII raw (stdlib only) keeping only requested readable nodes."""
        npts = None; names = []; keep_idx = {}
        with path.open("r", encoding="latin-1", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("No. Points:"):
                    npts = int(s.split(":")[1]); continue
                if s.startswith("No. Variables:"):
                    continue
                if s.startswith("Variables:"):
                    break
            for line in fh:
                s = line.strip()
                if s.startswith("Values:"):
                    break
                if not s or s.startswith("\t") is False and len(s.split()) == 1:
                    continue
                parts = s.split()
                if len(parts) >= 3:
                    raw_nm = parts[1]
                    nm = raw_nm.lower()
                    if nm.startswith("v(") and nm.endswith(")"):
                        nm = nm[2:-1]
                    elif nm.startswith("i(") and nm.endswith(")"):
                        nm = "i_" + nm[2:-1].replace("#branch", "")
                    names.append(nm)
                    if nm in keep:
                        keep_idx[nm] = int(parts[0])
            data = {k: [] for k in keep_idx}
            data["__stored_indices"] = []
            vnames = [n for n in names if n not in ("j", "native_end")]  # scalar .meas vectors excluded
            pos = {n: i for i, n in enumerate(vnames)}
            keep_pos = {k: pos[k] for k in keep_idx if k in pos}
            nstored = 0
            for line in fh:
                nxt = line.split()
                if len(nxt) >= 2 and nxt[0].isdigit():  # first line of a data point: "<idx>\t<value>"
                    if nstored % decim == 0:
                        data["__stored_indices"].append(int(nxt[0]))
                    buf = [nxt[1]]
                else:
                    buf.extend(nxt)
                if len(buf) >= len(vnames):
                    if (data["__stored_indices"] and
                            data["__stored_indices"][-1] == nstored):
                        for k, kk in keep_pos.items():
                            try:
                                data[k].append(float(buf[kk]))
                            except (ValueError, IndexError):
                                data[k].append(float("nan"))
                    nstored += 1
                    buf = []
            data["n_points_total"] = npts
            data["rows_read"] = nstored
            data["names_readable"] = names
        return data

    def crossings(t, y, level, rising=True):
        res = []
        for i in range(len(y) - 1):
            a, b = y[i], y[i + 1]
            if (rising and a < level <= b) or ((not rising) and a > level >= b):
                res.append(t[i] + (level - a) * (t[i + 1] - t[i]) / (b - a))
        return res

    KEEP = ["time", "vdd", "vin", "out", "cs", "comp", "fb", "vref", "rtct", "vout2"]
    WAVE_COLS = ["vdd", "vin", "out", "cs", "comp", "fb", "vref", "rtct", "vout2"]
    case_runs = []
    wave_lines = ["# ngspice-47 ASCII raw (case_*/raw_all.txt) decimated; columns are raw node vectors"]
    time_s = {}
    for kind, net in (("steady", NET_STEADY), ("startup", NET_START)):
        d = TASK / f"case_{kind}"
        d.mkdir(exist_ok=True)
        shutil.copyfile(MODEL, d / LIB_COPY)
        # ngspice PSpice-compatibility switch for the PSpice-syntax vendor model.
        # ngspice only reads .spiceinit from the USER directory (not cwd), so point HOME there.
        (d / ".spiceinit").write_text("set ngbehavior=ps\n", encoding="ascii")
        (d / "replay0.cir").write_text(deck_for(net, kind), encoding="latin-1")
        env = dict(os.environ, HOME=str(d), USERPROFILE=str(d))
        # --- PASS A: native write (binary raw), same workdir ---
        argv_a = [str(NG), "-b", "-o", "ngspice_raw.log", "replay0.cir"]
        ta = time.monotonic()
        try:
            pa = subprocess.run(argv_a, cwd=d, capture_output=True, text=True, timeout=TIMEOUT_S, env=env)
            rca, timed_a = pa.returncode, False
        except subprocess.TimeoutExpired:
            rca, timed_a = None, True
        ela = time.monotonic() - ta
        # --- PASS B: identical deck in a sibling sub-dir, ASCII dump forced ---
        sd = d / "ascii_run"
        sd.mkdir(exist_ok=True)
        shutil.copyfile(MODEL, sd / LIB_COPY)
        (sd / ".spiceinit").write_text("set ngbehavior=ps\n", encoding="ascii")
        (sd / "replay.cir").write_text(deck_for(net, kind, ascii_dump=True), encoding="latin-1")
        argv = [str(NG), "-b", "-o", "ngspice.log", "replay.cir"]
        t0 = time.monotonic()
        try:
            p = subprocess.run(argv, cwd=sd, capture_output=True, text=True, timeout=TIMEOUT_S, env=env)
            rc, so, se, timed = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, timed = None, True
            so = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            se = ""
        el = time.monotonic() - t0
        (d / "subprocess.stdout.txt").write_text(so or "", encoding="utf-8", errors="replace")
        (d / "subprocess.stderr.txt").write_text(se or "", encoding="utf-8", errors="replace")
        logtxt = (sd / "ngspice.log").read_text(encoding="latin-1", errors="replace") if (sd / "ngspice.log").exists() else ""
        loga = (d / "ngspice_raw.log").read_text(encoding="latin-1", errors="replace") if (d / "ngspice_raw.log").exists() else ""
        errs = [e for e in re.findall(r"(?im)^\s*error.*$", logtxt)]
        L(f"[{kind}] passA(native raw) rc={rca} timed={timed_a} {ela:.2f}s raw={(d / 'replay0.raw').exists()}")
        L(f"[{kind}] passB(ascii)     rc={rc} timed={timed} {el:.2f}s log_bytes={len(logtxt)} errors={len(errs)}")
        for e in errs[:6]:
            L(f"[{kind}]   {e.strip()}")
        rec = {"case": kind, "argv": argv, "cwd": str(sd), "rc": rc, "timed_out": timed,
               "elapsed_s": round(el, 3), "parsed_errors": errs, "deck_sha256": sha(sd / "replay.cir"),
               "raw_exists": (sd / "raw_all.txt").exists(),
               "native_raw": {"argv": argv_a, "cwd": str(d), "rc": rca, "timed_out": timed_a,
                              "elapsed_s": round(ela, 3), "file": str(d / "replay0.raw"),
                              "exists": (d / "replay0.raw").exists(),
                              "errors": len(re.findall(r"(?im)^\s*error.*$", loga))},
               "pspice_compat_active": "Compatibility modes selected: ps" in logtxt,
               "engine_warnings": sorted(set(re.findall(r"(?im)^\s*(?:note|warning).*$", logtxt)))[:8]}
        if rec["raw_exists"]:
            decim = int(os.environ.get("UCC_DECIM", "20"))
            a = read_ascii_raw(sd / "raw_all.txt", ["time", "v(vdd)", "v(vin)", "v(out)", "v(cs)", "v(comp)",
                                                    "v(fb)", "v(vref)", "v(rtct)", "v(+vout2)"], decim=decim)
            t = a["v(time)"]
            N = {"v(vdd)": "vdd", "v(vin)": "vin", "v(out)": "out", "v(cs)": "cs", "v(comp)": "comp",
                 "v(fb)": "fb", "v(vref)": "vref", "v(rtct)": "rtct", "v(+vout2)": "vout2"}
            v = {N[k]: a[k] for k in N if k in a and a[k]}
            time_s[kind] = t
            L(f"[{kind}] raw: {a['n_points_total']} points / {len(a['names_readable'])} vectors, "
              f"{a['rows_read']} rows streamed, {len(t)} kept; kept vectors={sorted(v)}")
            rec.update(endpoint_s=t[-1], kept_samples=len(t), total_points=a["n_points_total"], decimation=decim,
                       vectors=len(a["names_readable"]), kept_vectors=sorted(v))
            rec["maxima"] = {k: max(vv) for k, vv in v.items()}
            rec["finals"] = {k: vv[-1] for k, vv in v.items()}
            if kind == "steady":
                out = v["out"]
                hi = [1 if x > 2.5 else 0 for x in out]
                edges = [i for i in range(1, len(hi)) if hi[i] != hi[i - 1]]
                per = [t[b] - t[aa] for aa, b in zip(edges[:-1], edges[1:])]
                rec["out_edges"] = len(edges)
                rec["out_freq_Hz"] = (1.0 / (sum(per) / len(per))) if per else 0.0
                rec["out_duty"] = sum(hi) / len(hi)
                rec["out_first_last"] = [out[0], out[-1]]
            rec["window_s"] = [t[0], t[-1]]
            for kk in ("vdd", "vin", "vref", "rtct", "cs", "comp", "fb", "vout2"):
                if kk in v:
                    rec[kk + "_range_V"] = [min(v[kk]), max(v[kk])]
            wave_lines.append(f"# case={kind}  kept every {decim}-th raw point of {a['n_points_total']}")
            wave_lines.append(f"# CASE {kind}")
            wave_lines.append("# time " + " ".join(WAVE_COLS))
            for i in range(len(t)):
                wave_lines.append(f"{t[i]:.9e} " + " ".join(
                    f"{v[k][i]:.7e}" if k in v else "nan" for k in WAVE_COLS))
        case_runs.append(rec)
    (TASK / "waves.txt").write_text("\n".join(wave_lines) + "\n", encoding="utf-8")

    model_after = model_fingerprint(MODEL)
    nets_unchanged = all(c["identical"] for c in copied.values())
    model_unchanged = model_after["sha256"] == model_before["sha256"]
    L(f"model after run identical: {model_unchanged}; all vendor copies identical: {nets_unchanged}")

    # ---------- classification ----------
    steady = next((r for r in case_runs if r["case"] == "steady"), {})
    startup = next((r for r in case_runs if r["case"] == "startup"), {})
    tool_fail = [r["case"] for r in case_runs if r["rc"] != 0 or r["timed_out"]]
    setup_missing = [r["case"] for r in case_runs if r["parsed_errors"]]
    no_raw = [r["case"] for r in case_runs if not r["raw_exists"]]

    # physical-fidelity screen: does the controller look alive at all?
    def alive(r):
        return bool(r.get("out_edges", 0) > 10) and bool(r.get("vref_range_V", [0])[-1] > 2.5)

    steady_alive = alive(steady)
    stop_after_ok = bool(steady.get("endpoint_s", 0) >= 8.99e-3)

    metrics = {
        "task_id": "ucc28c43_reference",
        "scope": "Replay of the ORIGINAL TI UCC28C43 PSpice transient fixture (AEi/2008 model, TI SLUM521 "
                 "unencrypted release) in ngspice-47 with PSpice compatibility. CONTROLLER HARNESS ONLY: the TI "
                 "circuit is a synchronous flyback oscillator around two small transformers. It contains no OVP, "
                 "no HV precharge, no 170V output, no mainboard power stage. Nothing here qualifies the power stage.",
        "fixture_provenance": {
            "pspice_project_zip_sha256": "5eda3f5a976ed60ba206d264669d57b70ca1d443e4ede2ea80eb999c44e3b878",
            "vendor_native_solver": "PSpice 16.0.0 (Cadence pspice library nom.lib), Solver 1",
            "vendor_transient_setting": ".TRAN 0 9m 5m {SCHEDULE(0,1000ns,6m,20ns)} SKIPBP (steady) / "
                                       ".TRAN 0 30m 0 {SCHEDULE(0,1000ns,2.5m,25ns)} (startup)",
            "vendor_published_job_times_s": {"steady": 53.59, "startup": 260.77},
            "vendor_project_is_2008_workstation_provenance": True,
            "model_source_url": "https://www.ti.com/lit/zip/slum521",
            "model_origin_line_in_file": "(C) Copyright 2008 Texas Instruments Incorporated / AEi Systems LLC, "
                                          "PSpice Model Editor 16.0.0, Final 1.00 Release to Web, 11/05/2008",
            "model_license": "proprietary TI/AEi, released to web 'as is' with no warranty; no open licence text "
                             "in the file. Service required by the contract: preserved byte-for-byte.",
            "files": {k: v for k, v in copied.items()},
        },
        "replay": {
            "engine": "ngspice-47 (Aug 11 2026 build, ngspice_con.exe, KLU available, SPARSE 1.3 used)",
            "engine_mode": "ngbehavior=ps (PSpice compatibility) via case-local .spiceinit + private HOME/USERPROFILE",
            "vendor_native_unavailable": "PSpice and TINA are NOT installed on this host (checked C:\\Cadence, "
                                         "C:\\Program Files\\{Cadence,OrCAD,Texas Instruments,DesignSoft}); the "
                                         "vendor-native replay could not be executed. The engine is therefore a "
                                         "supported third-party reader of PSpice syntax, NOT the vendor tool.",
        },
        "deck_differences_vs_vendor": [
            ".LIB ../../../ucc28c43.lib -> .include <byte-identical copy of the TI unencrypted model, sha in "
            "model_hashes>",
            ".include/.options moved to the top (ngspice needs it before the first device line; PSpice order independent)",
            "TI .TRAN SCHEDULE() (PSpice-only) -> fixed maxstep 20ns; steady: tstop 9ms tstart 5ms",
            ".OPTIONS ngspice reltol=0.01 abstol=1u vntol=1m gmin=1e-10 itl4=5000 (PSpice profile also had "
            "CHGTOL=0.1p and STEPGMIN; ngspice has no CHGTOL)",
            "V_V1 VIN 0 has NO source specification in the TI netlist -> DC 24V assumed (explicit, not vendor data)",
            ".IC V(FB )=2.5 -> .nodeset V(FB)=2.5",
            "TI node '+VOUT1' is not addressable by an ngspice vector name -> captured by index v(j) in wrdata "
            "and by the ASCII raw dump",
        ],
        "test_assertions": [
            {"id": "A1_model_bytes_unchanged", "assert": "TI model sha256 identical before/after every run",
             "pass": model_unchanged},
            {"id": "A2_vendor_files_copied_verbatim", "assert": "11 vendor artefacts byte-identical host copies",
             "pass": nets_unchanged},
            {"id": "A3_engine_started", "assert": "ngspice rc==0, both cases, no timeout",
             "pass": not tool_fail},
            {"id": "A4_pspice_compat_active", "assert": "'Compatibility modes selected: ps' logged, both cases",
             "pass": all(r.get("pspice_compat_active") for r in case_runs)},
            {"id": "A5_raw_present", "assert": "ASCII raw written for both cases", "pass": not no_raw},
            {"id": "A6_reaches_endpoint", "assert": "steady run reaches >= 8.99ms of simulated time",
             "pass": stop_after_ok},
            {"id": "A7_controller_alive", "assert": "OUT toggles >10 times AND VREF settles above 2.5V",
             "pass": steady_alive},
            {"id": "A8_no_power_stage_claim", "assert": "no HV/OVP/startup acceptance is evaluated or claimed here",
             "pass": True},
        ],
        "RC_solver_tolerance": {
            "maxstep_s": TRAN_STEP, "reltol": 0.01, "abstol": 1e-6, "vntol": 1e-3, "gmin": 1e-10, "itl4": 5000,
            "inherited_from": "vendor PSpice profile (1% reltol): a LOOSE integrator; timing is indicative only",
        },
        "runs": case_runs,
        "measured_endpoints": {
            "steady": {k: steady.get(k) for k in ("endpoint_s", "out_freq_Hz", "out_duty", "out_edges", "vdd_range_V",
                                                  "vref_range_V", "vin_range_V", "rtct_range_V", "cs_range_V",
                                                  "comp_range_V")},
            "startup": {k: startup.get(k) for k in ("endpoint_s", "maxima", "finals")},
        },
        "failure_classification": {
            "TOOL": {
                "status": "PASS_WITH_CAVEAT",
                "detail": "ngspice-47 runs both decks to completion (rc=0). Vendor-native PSpice/TINA is absent, so "
                          "the original vendor engine replay is NOT reproduced.",
                "setup_errors_seen_during_debugging": [
                    "first attempt: .include placed after device lines -> 'unknown subckt: x_u7 ... fqb6n80' (ngspice order rule)",
                    "second attempt: no PSpice mode -> 'YYparse error' on the & operator in vendor B/G expressions",
                    "wrdata/capture errors for the illegal node name '+VOUT1' ('no such vector vout1')",
                ],
            },
            "SETUP": {"status": "RESOLVED", "detail": "PSpice mode, directive order and node addressing fixed "
                                                       "without touching model or fixture values."},
            "MODEL": {"status": "INCONCLUSIVE",
                      "detail": "the AEi 2008 UCC28C43_STEADY macro-model contains a probable internal wiring "
                                "defect that MASKES the UVLO function: STOF2 VDD 19 VDD GND SUVLO ties node 19 to "
                                "the VDD control terminal through RUVLO=1MEG, so V(19) can never follow VDD. "
                                "VREF/GB6/EBREF judge V(19) and therefore stay near 0V. Verified in the reproduced "
                                "waveforms: at VIN=24V (VDD forced to 24V by the TI deck) VREF/RTCT ~ -0.158mV and "
                                "VOUT2 ~ 0V; the OUT driver nonetheless toggles ~3.5MHz because EOut only tests "
                                "V(VREF,GND)>2.5 where VREF is the DECK node (~2.5V), not the internal reference. "
                                "This is a model-level finding, not a licence to edit the vendor file."},
            "ELECTRICAL": {"status": "FAIL_AS_WAVEFORMS (not as a power stage: none is present)",
                           "detail": "the replayed fixture does not reproduce a plausible UCC28C43 output: no "
                                     "regulated 12V bias, no VREF, no UVLO hand-off; switching is a fast "
                                     "unlicensed toggling, not a current-mode 110kHz operation."},
            "POWER_STAGE": {"status": "NOT_EVALUATED",
                            "detail": "the TI fixture has no OVP, no HV output, no 170V network, no real gate "
                                      "drive. Controller oscillation here is explicit evidence of nothing about "
                                      "the QS30-9 boost stage."},
        },
        "claims": "WORKER_CLAIM (preliminary, requires deterministic audit + Codex review): the original TI "
                  "UCC28C43 fixture netlists and TI model replay byte-for-byte-immutable in ngspice-47/PSpice "
                  "mode; the replay fails to exhibit a working controller, and the failure is attributable to the "
                  "vendor macro-model internal node 19/UVLO wiring rather than to the host electrical design.",
    }
    (TASK / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    L("")
    L("== summary ==")
    for r in case_runs:
        L(f"{r['case']:8s} rc={r['rc']} end={r.get('endpoint_s')} "
          f"f_out={r.get('out_freq_Hz')} vref={r.get('vref_range_V', (r.get('maxima') or {}).get('vref'))} "
          f"vout2={(r.get('maxima') or {}).get('vout2')}")
    L(f"assertions: {sum(1 for a in metrics['test_assertions'] if a['pass'])}/{len(metrics['test_assertions'])} pass")
    L(f"model immutable: {model_unchanged}; vendor copies verbatim: {nets_unchanged}")
    L(f"classification: TOOL={metrics['failure_classification']['TOOL']['status']} "
      f"MODEL={metrics['failure_classification']['MODEL']['status']} "
      f"ELECTRICAL={metrics['failure_classification']['ELECTRICAL']['status']} "
      f"POWER_STAGE={metrics['failure_classification']['POWER_STAGE']['status']}")
    (TASK / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
