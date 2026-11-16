"""Static independent detector screening; not SPICE or circuit qualification."""
import itertools
import json
from pathlib import Path


def bounds(top, bottom, ref, bias, tol=0.001 + 25e-6 * 75):
    # Sum of equal upper resistor fractions has the same extremes.
    vals = [v * (1 + top * (1 + tu) / (bottom * (1 + tb))) + i * top * (1 + tu)
            for v, tu, tb, i in itertools.product(ref, [-tol, tol], [-tol, tol], [-bias, bias])]
    return [min(vals), max(vals)]


def main():
    ovp = bounds(464000, 1000, [.396, .404], 15e-9)
    residual_rise = bounds(136200, 1000, [.396, .404], 15e-9)
    residual_fall = bounds(136200, 1000, [.387, .400], 15e-9)
    result = dict(scope='STATIC_ASSUMPTION_SCREEN_NOT_SPICE_NOT_HARDWARE_PASS',
                  resistor_initial_fraction=.001, resistor_TCR_ppm_per_K=25,
                  resistor_temperature_excursion_K=75,
                  resistor_exact_MPN='HOLD',
                  ovp_rising_V=ovp, residual_rising_V=residual_rise,
                  residual_falling_V=residual_fall,
                  criteria={'OVP_interval_V': [183, 190], 'residual_upper_engineering_only_V': 60},
                  OVP_static_screen='PASS' if ovp[0] >= 183 and ovp[1] <= 190 else 'FAIL',
                  residual_static_screen='PASS' if max(residual_rise) < 60 else 'FAIL',
                  excluded=['dynamic overshoot', 'maximum delay', 'unpowered behavior',
                            'single divider fault', 'touch safety standard', 'PCB leakage',
                            'input clamp damage', 'actual precision resistor MPN'])
    Path(__file__).with_name('threshold_screen.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
