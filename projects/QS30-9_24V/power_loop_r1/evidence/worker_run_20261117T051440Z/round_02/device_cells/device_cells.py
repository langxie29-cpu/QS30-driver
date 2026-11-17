"""device_cells (QS30-9 round_02) - exact-candidate device qualification fixtures.

Independent, single-device SPICE fixtures (no controller, no converter) for the
EXACT candidate devices of the QS30-9 24 V -> ~170 V boost cell.

CANDIDATES (all bytes copied byte-for-byte into model_bytes/)
<<<MODEL_TABLE>>>

FIXTURES per candidate
  F1 nonlinear switching (double pulse for the FET, turn-off + reverse recovery
     for the diodes), 3 timesteps x 2 temperatures
  F2 pin fixture (device pins connected exactly as the model/netlist declares)
  F3 magnetics: L(I) ladder under forced current, boost switch-node pulse, DCR
  TC model temperature-coefficient probe (self-consistency only)

Nothing outside THIS output directory is written. No threshold is relaxed.
Simulator: ngspice-47 (KLU), invoked via Python subprocess with explicit argv.

KNOWN LIMITS (do not read as PASS)
  * STP7N65M2 has NO local vendor model: only stp9nk50z.lib (STP9NK50Z) exists,
    so the exact device is screened on datasheet ratings + an exact-model
    substitute cell (one documented substitution point).
  * The ST model is stated "CAN BE USED AT TEMPERATURE: 25 C" -> T=125 C rows
    are a model-temperature probe, not a validated hot-device claim.
  * Coilcraft publish no inductance-vs-current (saturation) SPICE model: the
    magnetics screens are bounded brute force, not the vendor's L(I) curve.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

NG = Path(r"D:/PROJECTS/dsharness/QS30-1/tools/ngspice47/Spice64/bin/ngspice_con.exe")
HIST = Path(r"D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V")
R1W = Path(r"D:/PROJECTS/dsharness/QS30-power-loop-r1")
OUT = R1W / "projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_02/device_cells"
MB = OUT / "model_bytes"
RAW = OUT / "raw"

SRC = {
    "STP9NK50Z_MOSFET": HIST / "sources/sprint06b/ST_model_cn/unpacked/stp9nk50z.lib",
    "US1G_Vishay_1999": HIST / "sources/sprint06b/Vishay_US1G/us1g.txt",
    "US1G_Diodes_Inc": HIST / "sources/sprint06b/Diodes_US1G/Diodes_US1G.txt",
    "SS14_Vishay": HIST / "sources/sprint06c/SS14/original.lib",
    "MSS1583_datasheet_pdf": HIST / "sources/sprint06b/MSS1583_current/original.pdf",
    "STP7N65M2_datasheet_pdf": HIST / "sources/sprint06c/STP7N65M2_datasheet/original.pdf",
    "LT3757A_datasheet_txt": HIST / "sources/sprint06c/LT3757A_datasheet_retry/original.txt",
    "vendor_models_model_index": R1W / ("projects/QS30-9_24V/power_loop_r1/runs/"
                                        "20261117T051440Z/round_01/vendor_models/model_index.json"),
}
CURATED = {
    "stp9nk50z.lib": "STP9NK50Z_MOSFET",
    "us1g_vishay1999.models": "US1G_Vishay_1999",
    "us1g_diodesinc.models": "US1G_Diodes_Inc",
    "ss14_vishay.models": "SS14_Vishay",
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha(Path(p).read_bytes())


# ---------------------------------------------------------------- 1. curation
def curate():
    MB.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    m = {}
    for k, p in SRC.items():
        m[k] = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha_file(p)}
    out = {}
    for target, key in CURATED.items():
        data = SRC[key].read_bytes()
        (MB / target).write_bytes(data)
        assert (MB / target).read_bytes() == data, target
        out[target] = {"source_key": key, "sha256": sha(data), "bytes": len(data),
                       "roundtrip_identical": True,
                       "non_ascii_bytes": sum(1 for b in data if b > 127)}
    m["curated"] = out
    return m


# ---------------------------------------------------------------- 2. decks
def sim(step, end, tstart):
    # NOTE gminsteps/srcsteps must stay at their defaults: 0 makes ngspice fail the
    # initial point on these stiff switching decks (observed, kept out on purpose).
    return (".options reltol=1e-4 abstol=1e-12 vntol=1e-8 chgtol=1e-15\n"
            ".options itl4=500 maxord=2 gmin=1e-12\n"
            f".tran {step:g} {end:g} {tstart:g} uic\n")


ST_HEAD = ("* ST model stp9nk50z.lib, byte-identical (STP9NK50Z stands in for STP7N65M2)\n"
           ".include stp9nk50z.lib\n")


def st_f1(step, end, temp):
    """F1 clamped inductive double pulse; Vbus 170 V, L2 150 uH, gate 6.5 V/10 ohm."""
    return ("* F1 nonlinear switching: clamped inductive double pulse, STP9NK50Z model\n"
            + ST_HEAD + f".temp {temp}\n"
            "Vbus b 0 170\n"
            "Lbus b d 1u\n"
            "XQ d g s STP9NK50Z\n"
            "Rs s 0 1m\n"
            "L2 d2 0 150u\n"
            "Ds d2 d DUF\n"
            "Vp p 0 PULSE(0 6.5 1u 100n 100n 25u 100u)\n"
            "Rg p g 10\n"
            "Rgs g 0 10k\n"
            "VV 0 s 0\n"
            ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\n"
            + sim(step, end, end - 10e-6))


def st_f2():
    """F2 pins: ST declares PIN 1=Drain 2=Gate 3=Source."""
    return ("* F2 pins: STP9NK50Z pin map (1=D 2=G 3=S), VGS=10 V, VDS swept 0..5 V\n"
            + ST_HEAD + ".temp 27\n"
            "VG g 0 10\n"
            "VS s 0 0\n"
            "XQ d g s STP9NK50Z\n"
            "VD d 0 0\n"
            ".dc VD 0 5 0.01\n")


def st_f2_swapped():
    """F2 negative control: pins deliberately mis-wired (2 treated as drain)."""
    return ("* F2 negative control: pin order deliberately WRONG (2=D 1=G 3=S)\n"
            + ST_HEAD + ".temp 27\n"
            "VG g 0 10\n"
            "VS s 0 0\n"
            "XQ g d s STP9NK50Z\n"
            "VD d 0 0\n"
            ".dc VD 0 5 0.01\n")


def st_tc(temp):
    return ("* TC probe: model self-consistency only (Id at fixed VGS/VDS) vs TEMP\n"
            + ST_HEAD + f".temp {temp}\n"
            "VG g 0 10\n"
            "VS s 0 0\n"
            "XQ d g s STP9NK50Z\n"
            "VD d 0 1\n"
            ".op\n")


def d_f1(model, step, end, temp):
    return ("* F1 nonlinear turn-off: 1 A forward (10 uH) then reverse to 195 V in 195 ns\n"
            f".include {model}\n.temp {temp}\n"
            "Vf f 0 10\n"
            "Rf 1 f 10\n"
            "Lf 1 a 10u\n"
            "D1 a c DCAND\n"
            "Vr c 0 PULSE(0 195 10u 195n 195n 40u 100u)\n"
            + sim(step, end, end - 8e-6))


def d_f2(model):
    return ("* F2 pins: 2-terminal device (A K); forward sweep + reverse window probe\n"
            f".include {model}\n.temp 27\n"
            "VA a 0 0\n"
            "X1 a k DCAND\n"
            "VK k 0 0\n"
            ".dc VA 0 1.2 0.005\n")


def d_brk(model, temp):
    return ("* reverse window probe: -250 V .. 0 V sweep (breakdown current must stay tiny)\n"
            f".include {model}\n.temp {temp}\n"
            "VA a 0 0\n"
            "X1 a k DCAND\n"
            "VK k 0 0\n"
            ".dc VA -250 0 0.5\n")


def d_tc(model, temp):
    return ("* TC probe: forward drop at 1 A vs TEMP (model self-consistency)\n"
            f".include {model}\n.temp {temp}\n"
            "Vf f 0 1\n"
            "Rf 1 a 1\n"
            "X1 a 0 DCAND\n"
            ".op\n")


def l_ladder(step, end):
    """F3a: 9 paralleled branches, each forcing a constant current 0..8 A through
    150 uH + 38 mohm. V(node) = L dI/dt, so a regression of V vs current gives
    the L(I) curve; a core that saturates shows as collapsing V."""
    s = ("* F3a L(I) ladder: forced currents 0..8 A (9 branches, 150u, Rser=0.038)\n"
         ".temp 27\n")
    for i in range(1, 10):
        s += (f"I{i} 0 n{i} PWL(0 0 1u {(i - 1) * 1.0} 401u {i * 1.0})\n"
              f"Ln{i} n{i} 0 150u Rser=0.038\n")
    return s + sim(step, end, 0)


def l_pulse(step, end):
    """F3b: boost switch-node pulse at the cell operating point 24 V, D=0.65, 500 kHz."""
    return ("* F3b boost switch node: Vin 24 V, D=0.65, fsw 500 kHz, L 150u DCR 0.038\n"
            ".temp 27\n"
            "Vbus b 0 24\n"
            "Vsw sw 0 PULSE(0 1 1u 20n 20n 1.3u 2u)\n"
            "Ssw d 0 sw 0 SWM\n"
            ".model SWM SW(VT=0.5 RON=1m ROFF=100meg)\n"
            "L1 b d 150u Rser=0.038\n"
            "D1 d o DUF\n"
            ".model DUF D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n)\n"
            "Co o 0 47u\n"
            "Rld o 0 3k\n"
            + sim(step, end, 100e-6))


# ---------------------------------------------------------------- 3. runner
def run_case(name, deck_text, includes, what, timeout=240, control_pre=""):
    d = RAW / name
    d.mkdir(parents=True, exist_ok=True)
    for fn in includes:
        shutil.copyfile(MB / fn, d / fn)
    deck = d / "deck.cir"
    deck.write_text(deck_text, encoding="latin-1", newline="\n")
    script = d / "run.sp"
    script.write_text(deck_text + "\n.control\nrun\n" + control_pre + what +
                      "\n.endc\n.end\n", encoding="latin-1", newline="\n")
    logp = d / "ngspice.log"
    t0 = time.monotonic()
    rec = {"case": name, "argv": [str(NG), "-b", "-o", logp.name, script.name],
           "cwd": str(d), "timeout_s": timeout,
           "deck_sha256": sha(deck.read_bytes()),
           "script_sha256": sha(script.read_bytes())}
    try:
        p = subprocess.run([str(NG), "-b", "-o", logp.name, script.name], cwd=str(d),
                           capture_output=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        rec["rc"] = p.returncode
    except subprocess.TimeoutExpired:
        rec["rc"] = None
        rec["timed_out"] = True
    rec["elapsed_s"] = round(time.monotonic() - t0, 3)
    txt = logp.read_text(encoding="utf-8", errors="replace") if logp.is_file() else ""
    low = txt.lower()
    rec["log_present"] = logp.is_file()
    rec["errors"] = [ln.strip() for ln in txt.splitlines()
                     if re.search(r"\berror\b|fatal|no such|singular|too small|"
                                  r"failed|interrupted", ln, re.I)][:10]
    rec["timestep_substitution"] = bool(re.search(r"bisect|trying alternative", low))
    rec["integration"] = ("gear" if re.search(r"method\s*[:=]?\s*gear", low)
                          else "trap (default)")
    rec["warnings"] = [ln.strip() for ln in txt.splitlines()
                       if re.search(r"warn", ln, re.I)][:8]
    rec["solver"] = next((ln.strip() for ln in txt.splitlines()
                          if "Direct Linear Solver" in ln), None)
    rec["data_rows"] = next((int(m.group(1)) for ln in txt.splitlines()
                             for m in [re.search(r"No\. of Data Rows : (\d+)", ln)]
                             if m), None)
    return rec, txt


def parse_wrdata(p):
    """ngspice wrdata: repeating (scale, value) pairs, whitespace separated."""
    rows = []
    for ln in Path(p).read_text(errors="replace").splitlines():
        parts = ln.split()
        if len(parts) < 2:
            continue
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue
    return rows


def parse_print(txt, var):
    m = re.search(rf"^\s*{re.escape(var)}\s*=\s*([-+0-9.eE]+)", txt, re.M)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- 4. analysis
TOL = {"target_abs": 1e-3,        # 1 ms in absolute time comparisons
       "target_rel": 1e-3,        # 0.1 % on current/voltage measurements
       "comment": ("solver tolerance = ngspice reltol 1e-4 / abstol 1e-12 / vntol 1e-8 / "
                   "chgtol 1e-15, maxord=2 (gear-2 when the case selects it); measured "
                   "quantities are compared across 3 timesteps x 2 temperatures and the "
                   "spread is reported instead of being hidden.")}


def col(rows, k):
    return [r[k] for r in rows if len(r) > k]


def maxcol(rows, k):
    v = col(rows, k)
    return max(v) if v else None


def mincol(rows, k):
    v = col(rows, k)
    return min(v) if v else None


def at_time(rows, k, t):
    best = None
    for r in rows:
        if len(r) > k and r[0] >= t:
            best = r[k]
            break
    return best


def near(rows, k, t):
    """value at the sample nearest to time t"""
    best, bd = None, 1e30
    for r in rows:
        if len(r) > k:
            d = abs(r[0] - t)
            if d < bd:
                bd, best = d, r[k]
    return best


try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:      # pragma: no cover
    HAVE_MPL = False


def wave_png(rows, spec, title, path, xcol=0):
    if not HAVE_MPL:
        return False
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=110)
    for k, label, scale in spec:
        v = [(r[xcol], r[k] * scale) for r in rows if len(r) > k and len(r) > xcol]
        if v:
            xs = [p[0] * 1e6 for p in v] if xcol == 0 else [p[0] for p in v]
            ax.plot(xs, [p[1] for p in v], label=label, lw=0.8)
    ax.set_xlabel("time [us]" if xcol == 0 else "sweep variable [V]")
    ax.grid(alpha=.3)
    ax.legend(fontsize=7, loc="best")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True
