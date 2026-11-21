"""Compare identical electrical corners using a first-order DCM energy model."""
import csv
from itertools import product
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET_V = 170
BASE_LOAD_A = TARGET_V * (2 / 496000 + 1 / 2009300 + 1 / 1854200)
INPUTS = [(4.75, .190), (5.0, .190), (5.25, .190), (4.3, 0)]
CORNERS = list(product(INPUTS, (.76, 2.475), (0, .00765, .0099)))
OPTIONS = {
    "A": ((33,), (40, 50, 65, 80, 100), (0,), 2.5, .97, 200, 4.50, 652800),
    "B": ((8, 10, 12), (100, 150, 200, 350), (10, 12, 14.5), 3.0, .90, 100, 2.97, 1208961),
    "C": ((10,), (100, 150, 200), (10,), 3.0, .90, 100, 2.9, 1010000),
    "D": ((18, 22, 26.4), (80, 100, 120), (0,), 2, .925, 600, 3.5, 1698000),
}


def screen(route, nominal_l, freq, ratio, efficiency, capacitance, corner):
    _, _, _, peak_limit, duty_limit, rating, uvlo, fb_r = OPTIONS[route]
    (source, rpath), lv, load = corner
    output_a = load + BASE_LOAD_A + TARGET_V / fb_r
    hv_power = TARGET_V * output_a
    rail_power = lv + hv_power / efficiency
    discriminant = source**2 - 4 * rpath * rail_power
    terminal = (source + math.sqrt(discriminant)) / 2
    inductance = nominal_l * 1e-6
    period = .001 / freq
    peak = math.sqrt(2 * hv_power * period / (efficiency * inductance))
    ton = inductance * peak / terminal
    reflected = (TARGET_V + .8) / ratio if ratio else TARGET_V + .8 - terminal
    toff = inductance * peak / reflected
    # Boost switch sees output, flyback switch sees reflected output plus input.
    drain_plateau = terminal + reflected
    secondary_peak = peak / ratio if ratio else peak
    ripple = output_a * max(0, period - toff) / (capacitance * 1e-6) + secondary_peak * .1
    leakage_w = .5 * inductance * (1-.95**2) * peak**2 / period if ratio else None
    shunt_margin = .125 - (.033 * peak + .132 * ton/period) if route == "B" else None
    reasons = []
    if terminal < uvlo:
        reasons.append("UVLO_MAX")
    if ton + toff >= period or ton > duty_limit * period:
        reasons.append("TIMING")
    if peak > peak_limit:
        reasons.append("ASSUMED_PEAK_LIMIT")
    if drain_plateau >= .8 * rating:
        reasons.append("VDS_PLATEAU_OVER_80PCT")
    if ripple > 1:
        reasons.append("RIPPLE_ESTIMATE")
    if shunt_margin is not None and shunt_margin < 0:
        reasons.append("SENSE_HEADROOM")
    if route == "D" and freq < 100:
        reasons.append("OUTSIDE_VENDOR_FREQ")
    return dict(route=route, l_uH=nominal_l, frequency_kHz=freq, ratio=ratio,
                assumed_efficiency=efficiency, effective_cap_uF=capacitance,
                source_v=source, cable_ohm=rpath, lv_load_w=lv, tube_load_A=load,
                terminal_v=terminal, hv_load_w=hv_power, peak_A=peak, on_us=ton*1e6,
                demag_us=toff*1e6, occupancy=(ton+toff)/period, plateau_V=drain_plateau,
                ripple_est_Vpp=ripple, leakage_energy_rate_W=leakage_w,
                min_sense_margin_V=shunt_margin, screen_failures="|".join(reasons),
                evidence="ANALYTICAL_ONLY")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pareto(rows):
    # Cost is unavailable for whole stages. Compare only calculated risk indicators.
    dims = ("max_occupancy", "max_peak_A", "max_ripple_Vpp", "worst_leakage_W")
    return [candidate for candidate in rows if not any(
        all(other[k] <= candidate[k] for k in dims) and any(other[k] < candidate[k] for k in dims)
        for other in rows
    )]


def main():
    all_rows = []
    summary = []
    for route, (inductances, frequencies, ratios, *_) in OPTIONS.items():
        for l, f, ratio, eff, cap in product(inductances, frequencies, ratios, (.55, .65), (.47, 1, 2, 3.3)):
            cases = [screen(route, l, f, ratio, eff, cap, corner) for corner in CORNERS]
            all_rows.extend(cases)
            summary.append(dict(route=route, l_uH=l, frequency_kHz=f, ratio=ratio,
                                assumed_efficiency=eff, effective_cap_uF=cap,
                                corners=len(cases), cleared=sum(not row["screen_failures"] for row in cases),
                                max_occupancy=max(row["occupancy"] for row in cases),
                                max_peak_A=max(row["peak_A"] for row in cases),
                                max_ripple_Vpp=max(row["ripple_est_Vpp"] for row in cases),
                                worst_leakage_W=max(row["leakage_energy_rate_W"] or 0 for row in cases),
                                qualification="UNQUALIFIED"))
    write_csv(HERE/"evidence/analytical_corners.csv", all_rows)
    write_csv(HERE/"evidence/analytical_ranking.csv", summary)
    for route in OPTIONS:
        group = [row for row in summary if row["route"] == route]
        best_count = max(row["cleared"] for row in group)
        best = pareto([row for row in group if row["cleared"] == best_count])
        print(route, best_count, len(CORNERS), min(best, key=lambda x: (x["max_ripple_Vpp"], x["max_peak_A"])))
    front = [
        row for route in OPTIONS for eff in (.55,.65)
        for row in pareto([x for x in summary if x["route"] == route and x["assumed_efficiency"] == eff
                           and x["cleared"] == max(y["cleared"] for y in summary
                                                  if y["route"] == route and y["assumed_efficiency"] == eff)])
    ]
    write_csv(HERE/"evidence/analytical_pareto.csv", front)


if __name__ == "__main__":
    main()
