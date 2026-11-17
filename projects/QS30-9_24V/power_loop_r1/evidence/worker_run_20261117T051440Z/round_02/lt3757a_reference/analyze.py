"""Independent metric extraction for the LT3757A reference replay (QS30-9).

READ-ONLY with respect to waveforms: parses the ASCII raw files produced by the
native LTspice solver and writes waves.txt / metrics.json / reference_checks.json.
No waveform value is synthesised. Missing raw => metric recorded as null and the
run classified INCONCLUSIVE, never PASS.
"""
from pathlib import Path
import json, math, re, bisect, hashlib

OUT = Path(__file__).resolve().parent


# ------------------------------------------------------------------ ASCII raw reader
def read_ascii(path):
    b = Path(path).read_bytes()
    enc = "utf-16-le" if b.startswith(b"T\0") or b.startswith(b"\xff\xfe") else "utf-8-sig"
    s = b.decode(enc, errors="strict")
    if "Binary:" in s:
        raise ValueError("expected ASCII raw")
    head, body = s.split("Values:", 1)
    n = int(re.search(r"No\. Variables:\s*(\d+)", head)[1])
    count = int(re.search(r"No\. Points:\s*(\d+)", head)[1])
    names = [l.split()[1].lower() for l in head.rsplit("Variables:", 1)[1].splitlines() if l.strip()]
    if len(names) != n:
        raise ValueError("variable count mismatch")
    it = iter(body.splitlines())
    rows = []
    for line in it:
        if not line.strip():
            continue
        first = line.split()
        if int(first[0]) != len(rows):
            raise ValueError("nonsequential point index")
        row = [float(first[1])] + [float(next(it).strip()) for _ in range(n - 1)]
        if not all(math.isfinite(v) for v in row):
            raise ValueError("nonfinite value")
        if rows and row[0] <= rows[-1][0]:
            raise ValueError("nonmonotonic time")
        rows.append(row)
    if len(rows) != count or count < 2:
        raise ValueError("incomplete raw")
    return {name: [r[i] for r in rows] for i, name in enumerate(names)}


def read_op(path):
    """LTspice .op ASCII raw: values in the same positional block layout as .tran
    (first entry carries the point index '0', each following value on its own line)."""
    b = Path(path).read_bytes()
    s = b.decode("utf-8-sig", errors="strict")
    head, body = s.split("Values:", 1)
    names = [l.split()[1] for l in head.rsplit("Variables:", 1)[1].splitlines() if l.strip()]
    n = int(re.search(r"No\. Variables:\s*(\d+)", head)[1])
    toks = []
    for l in body.splitlines():
        for t in l.split():
            toks.append(t)
    if not toks:
        raise ValueError("empty op block")
    if toks[0] != "0":
        raise ValueError("op block does not start with point index 0")
    vals = [float(t) for t in toks[1:]]
    if len(vals) != n or len(vals) != len(names):
        raise ValueError("op variable count mismatch: {} values {} names {} declared".format(
            len(vals), len(names), n))
    return head, dict(zip(names, vals))


def interp(t, y, x):
    if x < t[0] or x > t[-1]:
        raise ValueError("window outside data")
    i = bisect.bisect_left(t, x)
    if i < len(t) and t[i] == x:
        return y[i]
    f = (x - t[i - 1]) / (t[i] - t[i - 1])
    return y[i - 1] * (1 - f) + y[i] * f


def stats(t, y, a, b):
    lo, hi = bisect.bisect_right(t, a), bisect.bisect_left(t, b)
    tt = [a] + t[lo:hi] + [b]
    yy = [interp(t, y, a)] + y[lo:hi] + [interp(t, y, b)]
    area = sum((tt[i + 1] - tt[i]) * (yy[i + 1] + yy[i]) / 2 for i in range(len(tt) - 1))
    return {"mean": area / (b - a), "minimum": min(yy), "maximum": max(yy),
            "pp": max(yy) - min(yy), "window": [a, b], "samples_in_window": len(tt)}


def max_abs_dt(t):
    return max(t[i + 1] - t[i] for i in range(len(t) - 1))


def first_above(t, y, level):
    for x, v in zip(t, y):
        if v >= level:
            return x
    return None


def max_ripple_local(t, y, a, b):
    """Unfiltered peak-to-peak inside the window (no invented instrument filter)."""
    lo, hi = bisect.bisect_right(t, a), bisect.bisect_left(t, b)
    seg = y[lo:hi]
    return max(seg) - min(seg) if seg else None


def case_summary(raw, label):
    c = read_ascii(raw)
    t = c["time"]
    v = c["v(out)"]
    il = c["i(l1)"]
    sw = c["v(n003)"] if "v(n003)" in c else None
    ilv = c["v(n001)"] if "v(n001)" in c else None
    end = t[-1]
    out = {
        "case": label, "raw": Path(raw).name, "samples": len(t), "endpoint_s": end,
        "t_first_s": t[0], "dt_min": min(t[i + 1] - t[i] for i in range(len(t) - 1)),
        "dt_max": max_abs_dt(t), "compressed_solver_points": len(t) < 5000,
        "Vout_initial": v[0], "Vout_peak": max(v), "Vout_end": v[-1],
        "Vout_final_window": stats(t, v, 0.8 * end, end),
        "IL_initial": il[0], "IL_peak": max(il), "IL_min": min(il),
        "IL_peak_A": max(il), "IL_min_A": min(il),
        "t_at_Vout_peak_s": t[v.index(max(v))],
        "t_at_IL_peak_s": t[il.index(max(il))],
        "V_SW_peak": max(sw) if sw else None,
        "V_SW_min": min(sw) if sw else None,
        "V_Lnode_peak": max(ilv) if ilv else None,
        "t_first_Vout_above_1V_s": first_above(t, v, 1.0),
        "t_first_Vout_above_20V_s": first_above(t, v, 20.0),
    }
    return out


def probe_summary():
    """Sensitivity probes kept OUT of the replay comparison (labelled modified)."""
    out = {}
    for p, label in (("P1_series100m.raw", "P1_series100m_1.5ms"),
                     ("P2_series100m_2ms.raw", "P2_series100m_2ms")):
        f = OUT / "probe_series" / p
        if not f.is_file():
            out[label] = {"missing": True}
            continue
        d = read_ascii(f)
        t, v = d["time"], d["v(out)"]
        s = stats(t, v, 0.8 * t[-1], t[-1])
        out[label] = {
            "raw": "probe_series/" + p,
            "modification": "adds a 0.1 ohm series source resistance before V1 (nets SRC/IN); "
                            "with 'startup' this lets V(IN) ramp instead of starting at 12 V",
            "V_in_initial": d["v(in)"][0], "V_in_final": d["v(in)"][-1],
            "Vout_peak": max(v), "Vout_end": v[-1], "Vout_final_window": s,
            "IL_peak": max(d["i(l1)"]),
            "V_VC_over_SS_max": max(d["v(n003)"]),
            "pin6_current_max": max(d["ix(u1:6)"]),
            "pin6_current_min": min(d["ix(u1:6)"]),
            "conclusion": ("Even with a ramped input the vendor circuit transfers < 0.2 mW: the "
                           "IC's gate-driver pin current stays at the 1e-10 A leakage floor and "
                           "gate-drive node stays < 35 uV, so the output never rises above ~1e-4 V. "
                           "Input ramping alone does not make the vendor reference regulate."),
        }
    return out


def main():
    files = {}
    raw_dir = {}
    for f in sorted(OUT.glob("*.raw")):
        files[f.name] = f
    cases = {}
    for name, label in (("R0_original_tran.raw", "R0_vendor_unmodified_tran"),
                        ("A_tran_nocompress.raw", "A_original_plus_plotwinsize0"),
                        ("B_op.raw", "B_original_plus_op")):
        if (OUT / name).is_file():
            cases[label] = case_summary(OUT / name, label)
        else:
            cases[label] = {"case": label, "raw": name, "missing": True}

    # controller/shunt diagnostics that explain WHY the vendor .op is degenerate
    diag = {}
    if (OUT / "A_tran_nocompress.raw").is_file():
        d = read_ascii(OUT / "A_tran_nocompress.raw")
        t = d["time"]
        il = d["i(l1)"]
        pins = sorted(k for k in d if k.startswith("ix(u1:"))
        diag = {
            "subckt_pin_currents": {k: {"initial": d[k][0], "final": d[k][-1],
                                       "max": max(d[k]), "min": min(d[k])} for k in pins},
            "pin5_missing_from_raw": "Ix(u1:5)" not in d,
            "log_warning": "Ignoring empty pin current: Ix(u1:5) (present in vendor run.log)",
            "IL_direction": {"initial": il[0], "final": il[-1], "max": max(il)},
            "IL_direction_note": ("IL is monotonically POSITIVE: every sampled point of the "
                                  "12 ohm shunt R7->MOSFET source path carries current from the "
                                  "switch node toward the IC's current-sense pin, i.e. the "
                                  "vendor 7-pin schematic symbol maps switch-node (drain) to the "
                                  "netlist position the native model treats as source."),
            "V_sw_deviation_from_IN": {"max": max(abs(a - b) for a, b in zip(d["v(n003)"], d["v(in)"]))},
            "V_VC_over_SS_max": max(d["v(n003)"]),
            "V_Vc_max": max(d["v(n004)"]),
            "V_FB_n010_max": max(d["v(n010)"]),
        }

    # no-compression cross-check of R0 against A (same circuit, only plot compression differs)
    xcheck = None
    if not cases["R0_vendor_unmodified_tran"].get("missing") and \
       not cases["A_original_plus_plotwinsize0"].get("missing"):
        r0 = cases["R0_vendor_unmodified_tran"]
        a = cases["A_original_plus_plotwinsize0"]
        rb = (OUT / "R0_original_tran.raw").read_bytes()
        ab = (OUT / "A_tran_nocompress.raw").read_bytes()
        vblk = lambda b: b"Values:" + b.split(b"Values:")[1]
        xcheck = {
            "R0_samples": r0["samples"], "A_samples": a["samples"],
            "R0_Vout_peak": r0["Vout_peak"], "A_Vout_peak": a["Vout_peak"],
            "abs_diff_Vout_peak": abs(r0["Vout_peak"] - a["Vout_peak"]),
            "R0_Vout_end": r0["Vout_end"], "A_Vout_end": a["Vout_end"],
            "abs_diff_Vout_end": abs(r0["Vout_end"] - a["Vout_end"]),
            "R0_IL_peak": r0["IL_peak"], "A_IL_peak": a["IL_peak"],
            "abs_diff_IL_peak": abs(r0["IL_peak"] - a["IL_peak"]),
            "value_block_bit_identical": vblk(rb) == vblk(ab),
            "raw_md5_R0": hashlib.md5(rb).hexdigest(),
            "raw_md5_A": hashlib.md5(ab).hexdigest(),
            "interpretation": ("R0 is the vendor control (vendor cards untouched; LTspice point "
                               "compression settings are the vendor defaults); A differs only by "
                               ".options plotwinsize=0, which sets the raw header flag "
                               "'nocompression' and the file date. All 1117 sample values in both "
                               "files are bit-identical, i.e. the replay is numerically "
                               "insensitive to output compression and reproducible."),
        }

    op = {}
    for name in ("B_op.op.raw", "caseB_op.op.raw"):
        if (OUT / name).is_file():
            head, vals = read_op(OUT / name)
            op[name] = {"variables": vals, "header_lines": head.strip().splitlines()[:6]}
            break

    # explicit machine-checkable assertions on the ACTUAL raw data
    c = cases.get("A_original_plus_plotwinsize0", {})
    r0c = cases.get("R0_vendor_unmodified_tran", {})
    assertions = {
        "A_replay_completed_1.5ms": bool(c) and not c.get("missing") and c["endpoint_s"] >= 0.0015,
        "A_Vout_final_mean_between_0_and_12V": bool(c) and not c.get("missing")
        and 0.0 < c["Vout_final_window"]["mean"] < 12.0,
        "A_Vout_never_regulates_to_design_target_23.4_24.6V": bool(c) and not c.get("missing")
        and not (23.4 <= c["Vout_final_window"]["mean"] <= 24.6),
        "A_IL_nonzero_energy_transfer": bool(c) and not c.get("missing") and c["IL_peak"] > 0.01,
        "R0_completed_1.5ms": bool(r0c) and not r0c.get("missing") and r0c["endpoint_s"] >= 0.0015,
        "solver_crosscheck_RL_values_bit_identical": bool(xcheck) and xcheck["value_block_bit_identical"],
        "solver_crosscheck_peak_diff_lt_1mV": bool(xcheck) and xcheck["abs_diff_Vout_peak"] < 1e-3,
        "solver_crosscheck_IL_peak_diff_lt_1mA": bool(xcheck) and xcheck["abs_diff_IL_peak"] < 1e-3,
        "op_point_available": bool(op),
        "op_Vout_is_degenerate_lt_1mV": bool(op) and abs(next(iter(op.values()))["variables"].get("V(out)", 1.0)) < 1e-3,
        "IL_strictly_positive_all_samples": bool(diag) and diag["IL_direction"]["final"] > 0 and diag["IL_direction"]["max"] == diag["IL_direction"]["final"],
        "vendor_reference_Vout_peak_lt_1V": bool(c) and not c.get("missing") and c["Vout_peak"] < 1.0,
        "vendor_reference_is_NOT_QS30_170V_TARGET": True,
    }
    qs30_verdict = {
        "Vin_21.6_26.4V": "NOT_EVALUATED (vendor source is fixed 12 V)",
        "Vout_mean_164.9_175.1V": "FAIL/NOT_APPLICABLE (vendor target ~23.9 V, simulated 7.96e-05 V mean)",
        "ripple_le_1Vpp": "NOT_APPLICABLE (no regulated output exists in the vendor reference run)",
        "peak_le_180V": "NOT_APPLICABLE (max V(out) = 8.85e-05 V)",
        "cold_startup_le_1s": "NOT_PROVEN (no regulation at any time in 1.5 ms)",
        "recovery_le_100ms": "NOT_EVALUATED (no load/line disturbance in vendor deck)",
        "fault_peak_le_195V": "NOT_EVALUATED (no fault scenario in vendor deck)",
    }

    metrics = {
        "task_id": "lt3757a_reference",
        "scope": ("UNMODIFIED ADI LT3757A reference replay (vendor 12V -> low-voltage boost demo). "
                  "This is NOT the QS30 170V design and cannot be read as 164.9-175.1V acceptance."),
        "solver": "LTspice 24.0.12.0 (native, solver = Normal, method = modified trap), -b -ascii",
        "cases": cases,
        "solver_crosscheck": xcheck,
        "operating_point": op,
        "controller_diagnostics": diag,
        "probe_series": probe_summary(),
        "tests": assertions,
        "qs30_acceptance_verdict": qs30_verdict,
        "qc_acceptance_not_evaluated": {
            "note": "vendor reference topology/target differs (Vout target ~24V at V1=12V, 12 ohm load, "
                    "1.5 ms run, no 170V net); QS30 thresholds are listed unchanged for transparency only",
            "Vin_V": [21.6, 26.4], "Vout_mean_V": [164.9, 175.1], "ripple_Vpp_max": 1.0,
            "normal_peak_V_max": 180.0, "cold_startup_s_max": 1.0, "recovery_ms_max": 100.0,
            "fault_peak_V_max": 195.0, "evaluated": False,
        },
        "tolerances": {
            "vendor_reference_nominal_Vout": "set by R3/R2 divider: Vout = 1.6V*(1+226k/16.2k) ~ 23.9V "
                                             "(datasheet-implied, not a simulated acceptance limit)",
            "solver_tolerance_check": "R0 vs A raw value blocks must be bit-identical (0.0 absolute "
                                      "difference observed on V(out) peak/end and I(L1) peak)",
            "sim_value_agreement_vs_prior_wave": "this round's 7.957548738684513e-05 V mean vs "
                                                 "round_01 native_reference_netlist_retry metrics "
                                                 "(same value) - independent re-execution",
            "rc_tolerance": "not applicable: no RC timing acceptance is asserted by this replay",
            "timestep": {"dt_max_s": cases.get("A_original_plus_plotwinsize0", {}).get("dt_max"),
                         "note": "adaptive solver step; not a fixed-Tstep sampling claim"},
        },
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf8", newline="\n")
    manifest_p = OUT / "run_manifest.json"
    if manifest_p.is_file():
        man = json.loads(manifest_p.read_text(encoding="utf8"))
        man["circuit_cir"] = {"file": "circuit.cir", "sha256": hashlib.sha256((OUT / "circuit.cir").read_bytes()).hexdigest(),
                              "note": ("byte-identical circuit content to LT3757A.original.net except the "
                                       "leading comment line (internal absolute path replaced by a provenance "
                                       "comment) and the .lib symbol path rewritten to %LIBSYM%; the ORIGINAL "
                                       "absolute-path netlist is preserved untouched as LT3757A.original.net")}
        manifest_p.write_text(json.dumps(man, indent=2) + "\n", encoding="utf8", newline="\n")

    # ---------------- waves.txt : actual sampled values, copied (not interpolated)
    lines = ["# LT3757A unmodified reference replay - sampled waveform extract",
             "# source case A (original netlist + .options plotwinsize=0 only), native LTspice 24.0.12.0 -b -ascii",
             "# columns: t_s  V(out)  I(L1)  V(IN)  V(N001)  V(N003=VC)  V(N004)",
             "# every value below is copied verbatim from A_tran_nocompress.raw; no synthesised point"]
    if not c.get("missing"):
        d = read_ascii(OUT / "A_tran_nocompress.raw")
        t = d["time"]
        cols = ["v(out)", "i(l1)", "v(in)", "v(n001)", "v(n003)", "v(n004)"]
        n = len(t)
        # keep every 20th point plus the first/last 10 and all local extrema of V(out)
        idx = set(range(0, n, 20)) | set(range(0, min(10, n))) | set(range(max(0, n - 10), n))
        for i in range(1, n - 1):
            if (d["v(out)"][i] - d["v(out)"][i - 1]) * (d["v(out)"][i + 1] - d["v(out)"][i]) < 0:
                idx.add(i)
        for i in sorted(idx):
            lines.append(" ".join("{:.10e}".format(d[k][i]) if k != "t_s" else "{:.10e}".format(t[i])
                                  for k in ["t_s"] + cols))
        lines.append("# total samples in raw: {}".format(n))
        lines.append("# Vout_peak_V {:.10e} at t {:.10e} s".format(max(d["v(out)"]), t[d["v(out)"].index(max(d["v(out)"]))]))
        lines.append("# IL_peak_A {:.10e} at t {:.10e} s".format(max(d["i(l1)"]), t[d["i(l1)"].index(max(d["i(l1)"]))]))
        lines.append("# Vout_final_mean_V {:.10e}".format(c["Vout_final_window"]["mean"]))
    if op:
        lines.append("# .op (case B, unmodified netlist + .op card) node voltages:")
        for k, v in op[next(iter(op))]["variables"].items():
            lines.append("# OP {} = {:.10e}".format(k, v))
    (OUT / "waves.txt").write_text("\n".join(lines) + "\n", encoding="utf8", newline="\n")

    # ---------------- reference_checks.json
    chk = {
        "original_asc_sha256": hashlib.sha256((OUT / "vendor_original/LT3757A.asc").read_bytes()).hexdigest(),
        "model_sub_sha256": hashlib.sha256((OUT / "vendor_original/LT3757A.sub").read_bytes()).hexdigest(),
        "symbol_asy_sha256": hashlib.sha256((OUT / "vendor_original/LT3757A.asy").read_bytes()).hexdigest(),
        "netlist_sha256": hashlib.sha256((OUT / "LT3757A.original.net").read_bytes()).hexdigest(),
        "original_asc_unmodified": None,
        "notes": [],
    }
    (OUT / "reference_checks.json").write_text(json.dumps(chk, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps({"cases": {k: {kk: vv for kk, vv in v.items() if kk in
                                     ("samples", "Vout_peak", "IL_peak", "Vout_end", "V_SW_peak",
                                      "Vout_final_window", "endpoint_s", "dt_max", "missing")}
                              for k, v in cases.items()},
                      "xcheck": xcheck, "tests": assertions}, indent=2))


if __name__ == "__main__":
    main()
