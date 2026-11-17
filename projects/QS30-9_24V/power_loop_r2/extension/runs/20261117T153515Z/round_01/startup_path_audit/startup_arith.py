"""startup_path_audit -- executable arithmetic only (CODE ONLY; NOT executed by this worker).
Every symbol is a prompt/principal-supplied constant, a datasheet value copied from
OLD/sources/TPS2660.txt at the cited line, or a value copied from
R2/evidence/principal/startup_bounds/results.json (literal, PURE ARITHMETIC -- no raw read).
No simulator, shell, network, job or model call. Writes ONE json next to this file.
Principal runs:  python startup_arith.py  ->  startup_arith.json (same directory).
"""
import json
from pathlib import Path

import numpy as np

DN = Path(__file__).resolve().parent  # output stays inside OUTPUT_DIR
OUT = {}

# ---- prompt-supplied constants (task INPUT / verified local context) ----
PIN, PMAX = 6.0, 26.4                # W required HV power ; V worst fixed input
R33 = 33.0                           # ohm nominal series precharge (33 -5% = 31.35)
R33MIN, R33MAX = 33.0 * 0.95, 33.0 * 1.05
GMAX, IMAX, CMIN = 25.5, 5.5e-6, 42.3e-9   # V/V ; A ; F  (worst-case dVdT programming)
DVMAX = 1.0                          # V proposed bypass-enable |Vin - Vout| window
CSTART = 24.36e-6                    # F (startup_bounds COUT)
VUSB = 4.75                          # V configured-USB minimum (S05_CIRCUIT_CANDIDATES.md L88)
PHV = 5.7156                         # W S06 HV/AUX-side allocation (SPRINT06B_REPORT.md L9)

# ---- datasheet values, OLD/sources/TPS2660.txt (SLVSDG2G, JULY2016, REV DECEMBER 2019) ----
GAIN_SS = dict(min=23.75, typ=24.6, max=25.5, src='TPS2660.txt L453 GAIN(dVdT)')
SINK_ABS = dict(value_mA=10.0, src='TPS2660.txt L309 IFLT/IdVdT/ISHDN sink 10 mA')
ILIM_V = dict(value_V=1.0, src='TPS2660.txt L457 V(ILIM) bias')
OL_12K = dict(min=0.95, typ=1.0, max=1.05, src='L461 R(ILIM)=12k, V(IN)-V(OUT)=1V')
OL_536K = dict(min=2.11, typ=2.23, max=2.35, src='L465')
CB_120K = dict(min=0.045, typ=0.073, max=0.11, src='L478 MODE=open')
CB_536K = dict(min=2.0, typ=2.21, max=2.4, src='L480 MODE=open')
TYP_ONLY = dict(
    tCB_dly=dict(typ_ms=4.0, src='L642'), tFASTTRIP=dict(typ_ns=250.0, src='L615'),
    tCBretry=dict(typ_ms=540.0, src='L644'), tdVdT_47n=dict(typ_ms=10.0, src='L635'),
    tdVdT_open=dict(typ_v=23.9, typ_ms=1.6, src='L636 + L1365'))
VREVTH = dict(min_mV=-15.0, typ_mV=-10.0, max_mV=-5.0, src='L530 (figure claim at L2215/2216)')
MSS = dict(mpn='MSS1583-154KED', L_uH=150.0, tol_pct=10.0, DCRmax_ohm=0.159,
           Isat_10pct_A=3.1, Isat_20pct_A=3.6, Isat_30pct_A=3.9,
           Irms_20Crise_A=1.55, Irms_40Crise_A=2.2,
           src='OLD/docs/S06_CIRCUIT_DELTA.md L9; the 154KE_ row in MSS1583.txt is NOT this row')

# ---- startup_bounds measurements, copied literals (not recomputed) ----
MEAS = dict(uncontrolled_peak_A=9.557205715216934, uncontrolled_Vout_peak_V=45.063842693104874,
            precharge_peak_A=0.7850974777642024, precharge_ppk_W=19.323451854700178,
            precharge_energy_J=0.007937059145663273, precharge_bound_A=0.8421052631578947,
            slew_peak_A=0.09448891831428566)
MEAS_SRC = 'R2/evidence/principal/startup_bounds/results.json (3x rc=0 COMPLETED_UNREVIEWED)'


def efuse_slew():
    """Exact linear dVdT ramp from datasheet worst-case limits: it is a BOUND, not a run."""
    v_pin = ILIM_V['value_V'] * GMAX                      # V(dVdT) when V(ILIM)=1 V
    t_pin = CMIN * v_pin / IMAX                           # s, cap-charge time dv/dt=Il/C
    rate = IMAX * GMAX / CMIN                             # V/s, fastest gain-limited rate
    t_26p4 = PIN / rate                                   # s, 0 -> 26.4 V at that rate
    t_absmax = t_pin * (SINK_ABS['value_mA'] * 1e-3)       # s, same ramp read at 10 mA sink
    t_open = TYP_ONLY['tdVdT_open']['typ_ms'] * 1e-3 * (PIN / TYP_ONLY['tdVdT_open']['typ_v'])
    return dict(gain_ss=GAIN_SS, gain_max_src='L453 MAX 25.5 V/V', cmin_F=CMIN, i_prog_A=IMAX,
                dvdt_pin_at_ilim_V=float(v_pin), cap_time_t_pin_s=float(t_pin),
                slew_V_per_s=float(rate), rise_0_to_26p4V_s=float(t_26p4),
                same_ramp_at_10mA_sink_s=float(t_absmax), sink_abs_max=SINK_ABS,
                rise_cdvdt_open_equiv_s=float(t_open), typ_only_src=TYP_ONLY['tdVdT_open'],
                assertions=dict(identity_holds=bool(np.isclose(CMIN * rate, IMAX * GMAX)),
                                fastest_rate_consistent=bool(rate > 0),
                                bound_not_model=True),
                statement='slew/rise are datasheet-limit arithmetic; a source ramp is NOT a TPS26601')


def fixed33():
    """Permanent series 33 ohm into a fixed load: max power transfer caps the supply."""
    q = PIN ** 2 / (4 * R33)                    # W, Vin^2/(4R) maximum deliverable
    qlo, qhi = PIN ** 2 / (4 * R33MAX), PIN ** 2 / (4 * R33MIN)   # looser R -> less power
    iload = PIN / PMAX                          # A, 6 W drawn at 26.4 V through the R
    r_series_6w = PIN ** 2 / (2 * PIN ** 2)     # 0.5 ohm: passes 6 W at 26.4 V (P=I^2R, I=6/26.4)
    return dict(route='PERMANENT 33 ohm SERIES RESISTOR', q_mpt_W=float(q),
                q_mpt_five_pct_W=[float(qlo), float(qhi)],
                q_as_pct_of_6W_typ=float(100 * q / PIN), q_as_pct_of_6W_lo=float(100 * qlo / PIN),
                load_A_for_6W=float(iload), r_series_ohm_for_6W=float(r_series_6w),
                r_loss_at_6W_W=float(iload ** 2 * R33),
                vout_for_6W_if_R_dissipates=float(np.sqrt(2 * PIN * R33)),
                duty_6W_at_26p4V=float(PIN / (PMAX ** 2 / (4 * R33))),
                duty_6W_at_usb_floor=float(PIN / (VUSB ** 2 / (4 * R33))),
                duty_s06_alloc=float(PHV / (PMAX ** 2 / (4 * R33))),
                r_ohm=R33, r_min_ohm=R33MIN, r_max_ohm=R33MAX,
                assertions=dict(cannot_supply_6W=bool(100 * qlo / PIN < 100),
                                r_loss_far_exceeds_load=bool(iload ** 2 * R33 > PIN)))


def bypass():
    """Independent precharge + bypass, closed only when |Vin-Vout|<=1 V and PWM disabled."""
    r_series_6w = PIN ** 2 / (2 * PIN ** 2)
    return dict(
        route='B. independent precharge + bypass (NOT BUILT)',
        hardware_missing=True, bypass_model_claimed=None, max_delay_claimed=None,
        enable_condition_V=DVMAX, pwm_state_required='DISABLED',
        max_delay_reason='tCB(dly)/tFASTTRIP/tCBretry/tdVdT are TYP-only (L642/L615/L644/L635); '
                         'no guaranteed max exists -> no max delay claimed',
        typ_only=TYP_ONLY, gain_ss=GAIN_SS, iol_at_12k=OL_12K, iol_at_536k=OL_536K,
        cb_mode_open_120k=CB_120K, cb_mode_open_536k=CB_536K, reverse_threshold=VREVTH,
        ilim_for_6W_A=float(PIN / PMAX), r_series_ohm_for_6W=float(r_series_6w),
        r_33ohm_loss_at_6W_W=float((PIN / PMAX) ** 2 * R33),
        section_variants=dict(A='series R permanent, eFuse MODE=open CB+latch',
                              B='precharge R + parallel bypass, eFuse MODE=402k limiting+latch'),
        observed=dict(uncontrolled_peak_A=MEAS['uncontrolled_peak_A'],
                      uncontrolled_vout_peak_V=MEAS['uncontrolled_Vout_peak_V'],
                      precharge_peak_A=MEAS['precharge_peak_A'],
                      precharge_ppk_W=MEAS['precharge_ppk_W'],
                      precharge_energy_J=MEAS['precharge_energy_J'],
                      precharge_bound_A=MEAS['precharge_bound_A'], slew_peak_A=MEAS['slew_peak_A'],
                      src=MEAS_SRC),
        assertions=dict(uncapped_inrush_exceeds_6W_current=bool(MEAS['uncontrolled_peak_A'] > PIN / PMAX),
                        precharge_under_forced_bound=bool(
                            MEAS['precharge_peak_A'] <= MEAS['precharge_bound_A']),
                        scope_rule='identical Vin and +5% tolerance applied to both devices'))


def startup_c():
    """Loss into Cstart=24.36 uF at 26.4 V for each datasheet slew duration (arithmetic)."""
    tau = dict(c_dvdt_min=float(PIN / (IMAX * GMAX / CMIN)),
               c_47n=10.0e-3, c_open=1.6e-3)
    return {k: dict(tau_s=v, energy_J=0.5 * CSTART * PIN ** 2,
                    mean_slew_A=float(CSTART * PIN / v), charge_C=float(CSTART * PIN))
            for k, v in tau.items()}


OUT.update(dict(
    efuse=efuse_slew(), fixed33_ohm=fixed33(), bypass=bypass(),
    startup_C=dict(c_F=CSTART, energy_J=0.5 * CSTART * PIN ** 2, charge_C=CSTART * PIN,
                   by_slew=startup_c()),
    inductor=MSS,
    power_budget=dict(hv_W=PHV, usb_min_V=VUSB, usb_A=float(PHV / VUSB),
                      required_A=float(PIN / PMAX), vin_abs_max_gain_V=float(ILIM_V['value_V'] * GMAX)),
    measured=MEAS, measured_src=MEAS_SRC,
    solver=dict(name='none', reason='arithmetic only; this task forbids shell/simulator/jobs'),
    status='INCONCLUSIVE: arithmetic bounds delivered; no TPS26601 dynamic model, no bypass HW, '
           'no datasheet maximum for any protection delay'))
(DN / 'startup_arith.json').write_text(json.dumps(OUT, indent=2, ensure_ascii=False) + '\n',
                                       encoding='utf8')
print(json.dumps({k: OUT[k] for k in ('efuse', 'fixed33_ohm')}, indent=1))
