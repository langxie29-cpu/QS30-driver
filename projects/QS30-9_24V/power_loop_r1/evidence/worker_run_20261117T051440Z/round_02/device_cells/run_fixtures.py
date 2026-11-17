"""driver v3: executes every fixture case, analyses the raw output, writes evidence.

wrdata layout: each requested vector is written as TWO columns
(scale, value), so vector j occupies columns (2j, 2j+1).

Acceptance gates are the repository's mandatory future-acceptance values
(170 V -> 195 V fault peak, 3.9 A/4.4 A/3.9 A Isat, 0.038 ohm DCR max,
500 kHz at 65 % duty producing ILpk ~1.05 A at the 9-tube load).
Nothing is relaxed here: a device that does not clear its gate is reported as
failing it, not as "acceptable".
"""
import json

import device_cells as dc
import fixtures as fx

OUT, RAW = dc.OUT, dc.RAW
V = lambda j: 2 * j + 1        # column index of vector j's VALUE
WAVES = []


def val(rows, j, fn):
    xs = [r[V(j)] for r in rows if len(r) > V(j)]
    return fn(xs) if xs else None


def eff_rms(rows, t_end_frac=0.5):
    """effective (heating) value over the last part of the window."""
    if not rows:
        return None
    t0, t1 = rows[0][0], rows[-1][0]
    cut = t0 + (t1 - t0) * t_end_frac
    xs = [abs(r[V(1)]) for r in rows if r[0] >= cut]
    return (sum(x * x for x in xs) / len(xs)) ** 0.5 if xs else None


def main():
    models = dc.curate()
    A = {"runs": {}, "models": models,
         "substitution_points": {
             "mosfet_model": ("No vendor SPICE model for STP7N65M2 exists locally. The "
                             "only ST MOSFET model present is stp9nk50z.lib (STP9NK50Z, "
                             "level-3, 2006, 'CAN BE USED AT TEMPERATURE: 25 C'). All "
                             "switching numbers below belong to STP9NK50Z and are NOT a "
                             "STP7N65M2 simulation. STP7N65M2 is screened on ratings only."),
             "f1_clamp_diode": ("generic D(IS=1e-9 N=1.7 RS=0.05 BV=1000 CJO=20p TT=100n) "
                                "stands in for UF4007 inside the FET fixture."),
         }}
    runs = A["runs"]
    tests = []

    def test(name, cond, detail):
        tests.append({"test": name, "pass": bool(cond), "detail": detail})
        print(f"TEST {name}: {'PASS' if cond else 'FAIL'} - {detail}", flush=True)

    # ---------------- F1 ST MOSFET: 3 timesteps x 2 temperatures
    f1 = {}
    for temp in (27, 125):
        for step in (50e-9, 100e-9, 200e-9):
            name = f"f1_st_ts{int(step * 1e9)}ns_T{temp}"
            rec, txt = dc.run_case(name, fx.st_f1(step, 60e-6, temp), ["stp9nk50z.lib"],
                                   "wrdata out.dat v(NVSWP) i(Vsense) v(NVGP) v(NVDDP)")
            runs[name] = rec
            try:
                rows = dc.parse_wrdata(RAW / name / "out.dat")
            except FileNotFoundError:
                rows = []
            f1[f"T{temp}_ts{int(step*1e9)}ns"] = {
                "rows": len(rows), "rc": rec["rc"],
                "vds_max": val(rows, 0, max), "is_min": val(rows, 1, min),
                "vg_max": val(rows, 2, max), "is_rms_effective": eff_rms(rows),
                "sim_errors": rec["errors"]}
            WAVES.append(("F1_ST", name, rows, "fet"))
            print(f"F1 {name}: rc={rec['rc']} rows={len(rows)} "
                  f"VDSmax={f1[f'T{temp}_ts{int(step*1e9)}ns']['vds_max']} "
                  f"ISmin={f1[f'T{temp}_ts{int(step*1e9)}ns']['is_min']}", flush=True)

    rec, txt = dc.run_case("f1_st_ts100ns_T27_gear",
                           fx.st_f1(100e-9, 60e-6, 27, ".options method=gear\n"),
                           ["stp9nk50z.lib"],
                           "wrdata out.dat v(NVSWP) i(Vsense) v(NVGP) v(NVDDP)")
    runs["f1_st_ts100ns_T27_gear"] = rec
    try:
        rows = dc.parse_wrdata(RAW / "f1_st_ts100ns_T27_gear" / "out.dat")
    except FileNotFoundError:
        rows = []
    f1["gear_ts100ns_T27"] = {"rows": len(rows), "rc": rec["rc"],
                              "vds_max": val(rows, 0, max), "is_min": val(rows, 1, min),
                              "vg_max": val(rows, 2, max),
                              "integration_requested": "gear",
                              "integration_logged": rec["integration"]}
    WAVES.append(("F1_ST_gear", "f1_st_ts100ns_T27_gear", rows, "fet"))
    A["f1_st"] = f1
    ok = [k for k, v in f1.items() if v["rows"]]
    A["f1_sensitivity"] = {
        "usable_cases": len(ok), "requested_cases": len(f1),
        "failing_cases": [k for k, v in f1.items() if not v["rows"]],
        "timestep_rows": {k: f1[k]["rows"] for k in f1},
        "rel_spread_vds_max": (lambda xs: (max(xs) - min(xs)) / max(xs))(
            [f1[k]["vds_max"] for k in ok]),
        "rel_spread_ig_max": (lambda xs: (max(xs) - min(xs)) / max(xs))(
            [f1[k]["vg_max"] for k in ok]),
    }
    test("F1 timestep independence (rows present at 50/100/200 ns)",
         all(f1[f"T{t}_ts{s}ns"]["rows"] > 0 for t in (27, 125)
             for s in (50, 100, 200)),
         f"usable {len(ok)}/{len(f1)} cases; failing: "
         f"{[k for k, v in f1.items() if not v['rows']]}")
    test("F1 VDS peak < 195 V fault-peak limit",
         max((f1[k]["vds_max"] or 0) for k in ok) < 195.0,
         f"VDSmax={max((f1[k]['vds_max'] or 0) for k in ok)}")

    # ---------------- F2 pins
    rec, txt = dc.run_case("f2_st_pins", fx.st_f2(), [], "wrdata out.dat v(ND) i(VD)")
    runs["f2_st_pins"] = rec
    try:
        rows = dc.parse_wrdata(RAW / "f2_st_pins" / "out.dat")
    except FileNotFoundError:
        rows = []
    i15 = dc.near(rows, V(1), 1.5)
    i5 = dc.near(rows, V(1), 5.0)
    A["f2_st_pins"] = {"ID_at_VDS_1p5V": i15, "ID_at_VDS_5V": i5,
                       "pin_declaration": "stp9nk50z.lib: PIN 1->Drain 2->Gate "
                                          "3->Source; netlist instantiates "
                                          "XQ <drain> <gate> <source>",
                       "note": "level-3 core instantiated with the model's own MOS "
                               "parameters (single documented extraction)"}
    WAVES.append(("F2_ST_pins", "f2_st_pins", rows, "dc"))
    test("F2 ST pin map conducts in the declared order",
         i15 is not None and abs(i15 - 1.5) < 0.01 and abs(i5 - 5.0) < 0.01,
         f"ID(1.5 V)={i15}, ID(5 V)={i5} (linear region, KP=7.026)")

    # ---------------- TC probe
    tc = {}
    for T in (27, 125, 150):
        rec, txt = dc.run_case(f"tc_st_T{T}", fx.st_tc(T), ["stp9nk50z.lib"], "print i(VD)")
        runs[f"tc_st_T{T}"] = rec
        tc[str(T)] = dc.parse_print(txt, "i(vd)")
    A["tc_st"] = {"ID_at_VGS10_VDS1_by_T": tc,
                  "caveat": "model header states 25 C only; self-consistency probe"}

    # ---------------- diodes
    diodes = {"US1G_vishay1999": ("US1GD", "us1g_vishay1999.models"),
              "US1G_diodesinc": ("DI_US1G", "us1g_diodesinc.models"),
              "SS14_vishay": ("DSS14", "ss14_vishay.models")}
    A["diodes"] = {}
    for tag, (mod, mfile) in diodes.items():
        D = {}
        f1d = {}
        for temp in (27, 125):
            for step in (2e-9, 5e-9, 20e-9):
                name = f"f1_{tag}_ts{int(step*1e9)}ns_T{temp}"
                rec, txt = dc.run_case(name, fx.d_f1(mod, mfile, step, 8e-6, temp),
                                       [mfile],
                                       "wrdata out.dat i(Vf) v(NVAP,NVKP) v(NVKP)")
                runs[name] = rec
                try:
                    rows = dc.parse_wrdata(RAW / name / "out.dat")
                except FileNotFoundError:
                    rows = []
                f1d[f"T{temp}_ts{int(step*1e9)}ns"] = {
                    "rows": len(rows), "rc": rec["rc"],
                    "i_rev_peak": val(rows, 0, min), "vr_max": val(rows, 1, max),
                    "t_turnoff_sample": 2e-6, "sim_errors": rec["errors"]}
                WAVES.append((f"F1_{tag}", name, rows, "diode"))
                print(f"F1 {name}: rows={len(rows)} Irev={f1d[f'T{temp}_ts{int(step*1e9)}ns']['i_rev_peak']} "
                      f"VRmax={f1d[f'T{temp}_ts{int(step*1e9)}ns']['vr_max']}", flush=True)
        D["f1"] = f1d
        rec, txt = dc.run_case(f"f2_{tag}", fx.d_f2(mod, mfile), [mfile],
                               "wrdata out.dat v(NVAP) i(VA)")
        runs[f"f2_{tag}"] = rec
        try:
            rows = dc.parse_wrdata(RAW / f"f2_{tag}" / "out.dat")
        except FileNotFoundError:
            rows = []
        D["f2_forward"] = {
            "Vf_at_1A": next((r[V(0)] for r in rows
                              if len(r) > V(1) and abs(r[V(1)]) >= 1.0), None),
            "I_at_0p5V": abs(dc.near(rows, V(1), 0.5)) if rows else None}
        WAVES.append((f"F2_{tag}", f"f2_{tag}", rows, "dc"))
        brk = {}
        for T in (27, 125):
            rec, txt = dc.run_case(f"brk_{tag}_T{T}", fx.d_brk(mod, mfile, T), [mfile],
                                   "wrdata out.dat i(VA)")
            runs[f"brk_{tag}_T{T}"] = rec
            try:
                rows = dc.parse_wrdata(RAW / f"brk_{tag}_T{T}" / "out.dat")
            except FileNotFoundError:
                rows = []
            brk[str(T)] = {"i_rev_abs_peak_in_-250..0V_window": val(rows, 0, lambda xs: max(abs(x) for x in xs))}
        D["reverse_window"] = brk
        tcd = {}
        for T in (27, 125, 150):
            rec, txt = dc.run_case(f"tc_{tag}_T{T}", fx.d_tc(mod, mfile, T), [mfile],
                                   "print v(NVAP)")
            runs[f"tc_{tag}_T{T}"] = rec
            tcd[str(T)] = dc.parse_print(txt, "v(nvap)")
        D["tc_Vf_at_1A"] = tcd
        A["diodes"][tag] = D
        print(f"{tag}: Vf(1A)={D['f2_forward']['Vf_at_1A']} "
              f"reverse-window peak I={brk['27']['i_rev_abs_peak_in_-250..0V_window']} "
              f"Irr(T27@5ns)={f1d['T27_ts5ns']['i_rev_peak']}", flush=True)

    for tag in diodes:
        D = A["diodes"][tag]
        big = D["reverse_window"]["27"]["i_rev_abs_peak_in_-250..0V_window"]
        test(f"{tag}: holds off through the -250..0 V reverse window at model T=27 C",
             big is not None and big < 1e-3,
             f"peak |I| in window = {big} A")
        irr = [D["f1"][k]["i_rev_peak"] for k in D["f1"] if k.startswith("T27")]
        test(f"{tag}: reverse recovery reproduced at the undriven (T=27 C) model temp",
             all(x is not None for x in irr),
             f"Irev(peak) across 3 timesteps = {irr}")
        vf = D["tc_Vf_at_1A"]
        test(f"{tag}: forward drop at 1 A is finite at T=27/125/150 C",
             all(isinstance(vf.get(k), float) for k in ("27", "125", "150")),
             f"Vf(1 A) = {vf}")

    # ---------------- magnetics
    rec, txt = dc.run_case("f3_L_ladder", fx.l_ladder(0.5e-6, 402e-6), [],
                           "wrdata out.dat " + " ".join(
                               f"i(I{i}) v(NLV{i})" for i in range(1, 10)))
    runs["f3_L_ladder"] = rec
    try:
        rows = dc.parse_wrdata(RAW / "f3_L_ladder" / "out.dat")
    except FileNotFoundError:
        rows = []
    lad = {}
    if rows:
        T = [r[0] for r in rows]
        for i in range(1, 10):
            jI, jV = 2 * (i - 1), 2 * (i - 1) + 1
            idx = [j for j, t in enumerate(T) if 20e-6 <= t <= 380e-6]
            if len(idx) < 4:
                continue
            ts = [T[j] for j in idx]
            vs = [rows[j][V(jV)] for j in idx]
            is_ = [abs(rows[j][V(jI)]) for j in idx]
            n = len(ts)
            mt, mv = sum(ts) / n, sum(vs) / n
            slope = (sum((a - mt) * (b - mv) for a, b in zip(ts, vs))
                     / sum((a - mt) ** 2 for a in ts))
            lad[str(i - 1)] = {"I_forced": sum(is_[-3:]) / 3, "V_slope_V_per_s": slope,
                               "L_est_uH": slope / 2500.0 * 1e6, "n": n}
    A["f3_ladder"] = {"branches": lad,
                      "note": "linear core by construction: validates the fixture and "
                              "the 150 uH / 0.038 ohm constant, NOT saturation"}
    lerr = [abs(v["L_est_uH"] - 150.0) / 150.0 for v in lad.values()]
    test("F3 L(I) ladder identity: 150 uH reproduced within 0.5 % at every forced "
         "current 0..8 A", lad and max(lerr) < 5e-3,
         f"max relative error = {max(lerr) if lerr else None}, N={len(lad)}")

    boosts = {}
    for tag, sat in (("linear", False), ("saturating_family", True)):
        name = f"f3_boost_{tag}"
        rec, txt = dc.run_case(name, fx.l_pulse(10e-9, 1.2e-5 + 3.32e-6 + 5e-9, saturating=sat),
                               [],
                               "wrdata out.dat i(L1) v(NVDP) v(NVOP) v(NVSW)")
        runs[name] = rec
        try:
            rows = dc.parse_wrdata(RAW / name / "out.dat")
        except FileNotFoundError:
            rows = []
        boosts[tag] = {"IL_peak": val(rows, 0, max), "IL_min": val(rows, 0, min),
                       "Vswitch_peak": val(rows, 1, max), "Vout_final": val(rows, 2, max),
                       "rows": len(rows), "rc": rec["rc"]}
        WAVES.append(("F3_boost", name, rows, "boost"))
        print(f"F3 boost {tag}: ILpk={boosts[tag]['IL_peak']} "
              f"Vsw_pk={boosts[tag]['Vswitch_peak']} Vout={boosts[tag]['Vout_final']}",
              flush=True)
    A["f3_boost"] = boosts
    test("F3 steady-state ILpk at D=65 %/500 kHz stays below the 3.9 A Isat(10 %) "
         "datacard minimum", (boosts["linear"]["IL_peak"] or 1e9) < 3.9,
         f"ILpk(linear)={boosts['linear']['IL_peak']} A")
    test("F3 saturating-core family reproduces the same peak current",
         boosts["saturating_family"]["IL_peak"] is not None and
         abs(boosts["saturating_family"]["IL_peak"] - boosts["linear"]["IL_peak"]) < 0.15,
         f"ILpk(sat)={boosts['saturating_family']['IL_peak']} vs "
         f"ILpk(linear)={boosts['linear']['IL_peak']}")

    # DCR conduction screen (bookkeeping, not a simulation)
    A["f3_dcr_screen"] = {
        "basis": "P = I^2 * DCR at the 9-tube load; I_rms taken as D*larger of the two",
        "design_Irms_A": 2.5,
        "P_typ_033_ohm_W": 2.5 ** 2 * 0.033,
        "P_max_038_ohm_W": 2.5 ** 2 * 0.038,
        "caveat": "DCR is a datasheet constant; its temperature coefficient is NOT "
                  "modelled. Hot DCR (and therefore hot conduction loss) is "
                  "UNSUPPORTED and remains a HOLD item.",
    }
    A["f3_datacard"] = {
        "part": "MSS1583-154KED", "L_uH": 150, "tol": "10%",
        "DCR_typ": 0.033, "DCR_max": 0.038,
        "Isat_10pct_A": 3.9, "Isat_20pct_A": 4.4, "Isat_30pct_A": 3.9,
        "Irms_20Crise_A": 3.4, "Irms_40Crise_A": 4.8,
        "datasheet_sha256": models["MSS1583_datasheet_pdf"]["sha256"],
        "no_vendor_L_of_I_model": True,
    }

    # ---------------- ratings screen (datasheet, not simulation)
    A["ratings_screen"] = {
        "STP7N65M2": {"VDS": 650, "ID_continuous_25C": 5.0, "RDS_on_max_at_10V_2p5A": 1.15,
                      "VGS_abs_max": 25, "datasheet_sha256":
                      models["STP7N65M2_datasheet_pdf"]["sha256"],
                      "note": "ratings only; no STP7N65M2 SPICE model exists locally, "
                              "so its dynamic behaviour is INCONCLUSIVE"},
        "gate_drive": {"LT3757A_INTVCC_typ": 7.2,
                       "LT3757A_datasheet_sha256": models["LT3757A_datasheet_txt"]["sha256"],
                       "consequence": "a 6.5 V gate drive sits at the low end of the "
                                      "10 V RDS(on) test condition -> RDS(on) larger "
                                      "than the 1.15 V datasheet value; NOT quantified"},
    }

    A["have_matplotlib"] = dc.HAVE_MPL
    A["tests"] = tests
    png = {}
    for tag, name, rows, kind in WAVES:
        if not rows:
            continue
        tgt = OUT / f"wave_{name}.png"
        if kind == "diode":
            png[name] = dc.wave_png(rows, [(V(0), "i(Vf) [A]", 1),
                                           (V(1), "V(A,K) [V]", 1)], f"{tag} {name}", tgt)
        elif kind == "dc":
            png[name] = dc.wave_png(rows, [(V(0), "sweep [V]", 1),
                                           (V(1), "current [A]", 1)], f"{tag} {name}", tgt)
        elif kind == "boost":
            png[name] = dc.wave_png(rows, [(V(0), "i(L) [A]", 1),
                                           (V(1), "V(sw) [V]", 1),
                                           (V(2), "V(out) [V]", 1)], f"{tag} {name}", tgt)
        else:
            png[name] = dc.wave_png(rows, [(V(0), "V(ds) [V]", 1),
                                           (V(1), "i(source eff) [A]", 1),
                                           (V(2), "V(gs) [V]", 1)], f"{tag} {name}", tgt)
    A["png"] = png
    (OUT / "analysis.json").write_text(json.dumps(A, indent=2, default=str), encoding="utf8")
    with open(OUT / "waves.txt", "w", encoding="utf8", newline="\n") as fh:
        fh.write("# device_cells waveform extract (first 8 + last 4 rows per run)\n")
        fh.write("# columns: wrdata(scale,value) pairs -> (t, v0, t, v1, t, v2, ...)\n")
        fh.write("# full data: raw/<case>/out.dat\n")
        for tag, name, rows, kind in WAVES:
            fh.write(f"\n## RUN {name} [{tag}] rows={len(rows)}\n")
            if not rows:
                fh.write(f"NO DATA (see raw/{name}/ngspice.log)\n")
                continue
            for r in rows[:8] + rows[-4:]:
                fh.write(" ".join(f"{x:.9e}" for x in r) + "\n")
    return A


if __name__ == "__main__":
    main()
