"""Quantitative screening for architecture decisions; fixture-free and non-qualifying."""
from itertools import product
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
TOL = 0.01
V = 26.4
I_START = 1.649202
VLIM_MIN = 0.0485
VCB_MAX = 0.130
HOT_ASSUMPTIONS = [2.0, 2.5, 2.75, 3.1]
START_ASSUMPTIONS = [0.85, 1.0, 1.2, I_START]
L_ASSUMPTIONS = [100e-6, 135e-6, 150e-6]


def window(start, ceiling, tol=TOL):
    return VCB_MAX / (ceiling * (1 - tol)), VLIM_MIN / (start * (1 + tol))


def main():
    limits = []
    for start, ceiling in product(START_ASSUMPTIONS, HOT_ASSUMPTIONS):
        lower, upper = window(start, ceiling)
        limits.append(dict(start_A=start, breaker_ceiling_A=ceiling, lower_mohm=lower * 1000,
                           upper_mohm=upper * 1000, nonempty_static_only=lower <= upper))
    sensitivities = []
    for start, ceiling, inductance in product(START_ASSUMPTIONS, HOT_ASSUMPTIONS, L_ASSUMPTIONS):
        dc_ramp_us = 1e6 * (ceiling - start) * inductance / V
        cap_only_uf = 1e6 * inductance * (ceiling**2 - start**2) / V**2
        sensitivities.append(dict(initial_A=start, ceiling_A=ceiling, linear_L_uH=inductance * 1e6,
                                  Vin_V=V, dc_to_ceiling_us=dc_ramp_us,
                                  cap_only_zero_loss_budget_uF=cap_only_uf))
    for label, rows in [('frontend_static_windows', limits), ('frontend_storage_sensitivity', sensitivities)]:
        with (HERE / 'evidence' / f'{label}.csv').open('w', newline='', encoding='utf-8') as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    out = dict(
        static_startup_max_fraction=VLIM_MIN / VCB_MAX * (1 - TOL) / (1 + TOL),
        frozen_window_mohm=[1000 * r for r in window(I_START, 3.1)],
        max_start_A_at_3p1A=3.1 * (VLIM_MIN / VCB_MAX) * (1 - TOL) / (1 + TOL),
        min_ceiling_A_at_1A=VCB_MAX / VLIM_MIN * (1 + TOL) / (1 - TOL),
        lt3757a_rs20_dc_A=[0.100/(0.062*(1+TOL)), 0.120/(0.062*(1-TOL))],
        energy_mJ={
            'upstream_56p51uF_26p4V': 0.5 * 56.51e-6 * V**2 * 1000,
            'downstream_assumed_1uF_26p4V': 0.5 * 1e-6 * V**2 * 1000,
            'HV_22p315uF_195V': 0.5 * 22.315e-6 * 195**2 * 1000,
        },
        status='SENSITIVITY_ONLY_HOLD',
    )
    (HERE / 'evidence' / 'frontend_results.json').write_text(json.dumps(out,indent=2)+'\n',
                                                            encoding='utf-8')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
