"""Independent checks on the exported R9 costs and analytical bounds."""

import csv
from decimal import Decimal, ROUND_HALF_UP
from math import log, sqrt
from pathlib import Path


def cents(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def verify_costs():
    filename = Path(__file__).with_name("BOM_COST_MODEL.csv")
    with filename.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for variant in ("A", "B"):
        for boards in (1, 3, 10):
            batch = [row for row in rows
                     if row["oled"] == variant and row["build_qty"] == str(boards)]
            summary = {row["item"]: row for row in batch if row["record"] == "SUMMARY"}
            materials = [row for row in batch if row["record"] == "MATERIAL"]
            assert len(summary) == 8 and len(materials) == 35
            used, cash, extras = Decimal(0), Decimal(0), Decimal(0)
            for row in materials:
                need = int(row["installed_per_board"]) * boards
                unit = Decimal(row["model_unit_cny"])
                buy = int(row["planned_buy_qty"])
                assert int(row["used_qty"]) == need and buy >= need
                assert Decimal(row["used_or_summary_cny"]) == cents(unit * need)
                assert Decimal(row["cash_cny"]) == cents(unit * buy)
                used += cents(unit * need)
                cash += cents(unit * buy)
                additional = max(0, int(row["installed_per_board"]) * max(boards, 2) - buy)
                extras += cents(unit * additional)

            freight = sum(Decimal(row["cash_cny"]) for row in batch if row["record"] == "CASH")
            outsource = Decimal(115 + 13 * max(boards, 2))
            per = cents(used / boards)
            expect = {
                "MATERIAL_PER_BOARD": per,
                "MATERIAL_BATCH": used,
                "FIRST_BUY_LANDED": cash + freight,
                "OUTSOURCED_ASSEMBLY": outsource,
                "FIRST_PCBA_LANDED": cash + freight + outsource + extras,
                "GAP_TO_60": per - 60,
                "GAP_TO_100": per - 100,
            }
            assert Decimal(summary["OUTSOURCED_ASSEMBLY"]["cash_cny"]) == outsource + extras
            if boards > 1:
                expect["REPEAT_PCBA_PER_BOARD"] = cents((used + outsource) / boards)
            else:
                assert not summary["REPEAT_PCBA_PER_BOARD"]["used_or_summary_cny"]
            for key, amount in expect.items():
                field = "cash_cny" if key in ("FIRST_BUY_LANDED", "FIRST_PCBA_LANDED") else "used_or_summary_cny"
                assert Decimal(summary[key][field]) == amount, (variant, boards, key)
    assert len([row for row in rows if row["record"] == "TARGET"]) == 3
    assert all(row["build_qty"] == "" and row["model_unit_cny"] == ""
               for row in rows if row["record"] in ("QUOTE", "TARGET"))
    print("BOM verified: six scenarios, 210 installed lines, quote and target separation")


def near(actual, expected, tolerance):
    assert abs(actual - expected) <= tolerance, (actual, expected)


def verify_calculations():
    # R8 comparison values remain research thresholds.
    vbus, anode_r, bleed_path = 195.0, 19_800, 502_980
    c_out = 3.63e-6
    energy = 0.5 * c_out * vbus**2
    fixed_peak = vbus**2 / (4 * anode_r)
    near(energy * 1000, 69.02, 0.005)
    near(fixed_peak, 0.480, 0.001)
    for r, expected in [(bleed_path/2, 39.66), (bleed_path, 46.53)]:
        x = sqrt(anode_r**2 + anode_r*r)
        fraction = x / (x + anode_r + (x + anode_r)**2/r)
        near(energy*fraction*1000, expected, 0.02)
    for cap, expected_energy, expected_time in [
        (1, 22.815, 0.356), (2.2, 50.193, 0.783),
        (3.3, 75.290, 1.174), (4.7, 107.230, 1.672)
    ]:
        maximum = 1.2 * cap * 1e-6
        near(0.5*maximum*vbus**2*1000, expected_energy, 0.001)
        near(maximum*bleed_path/2*log(vbus/60), expected_time, 0.001)
    near(1.0 + 3030*(0.000330 + 1.0/9900), 2.306, 0.002)
    normal = (170*0.00255*3 + 0.116 + 0.03)/0.7 + 3.3*0.2/0.87 + 0.05
    peak = (170*0.0033*3 + 0.116 + 0.03)/0.65 + 3.3*0.6/0.8 + 0.12
    near(normal, 2.87, 0.01)
    near(peak, 5.41, 0.01)
    near(peak/4.4, 1.23, 0.005)
    inductance, frequency, v_in = 17.6e-6, 100e3, 4.4
    max_current = sqrt(2 * 1.85 / (0.65 * inductance * frequency))
    duty = inductance * max_current * frequency / v_in
    switch_rms_squared = max_current**2 * duty / 3
    near(sqrt(switch_rms_squared), 0.88, 0.01)
    near(switch_rms_squared * 3.1, 2.4, 0.02)
    near(switch_rms_squared * 0.38, 0.29, 0.01)
    off_fraction = inductance * max_current * frequency / (170 - v_in)
    near(sqrt(max_current**2 * off_fraction / 3 - 0.0109**2), 0.143, 0.001)
    print("Analytical screens verified: base drive, steady/peak input, switch and capacitor RMS, and fault energy")


if __name__ == "__main__":
    verify_costs()
    verify_calculations()
