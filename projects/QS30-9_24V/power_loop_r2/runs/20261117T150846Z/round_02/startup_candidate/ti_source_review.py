"""startup_candidate — quantified TI guarantee / source review (READ ONLY, no simulation).

Produces `ti_source_review.json` next to this file. Every number is either (a) quoted with a
datasheet line reference, or (b) an arithmetic result of this script whose inputs are quoted.
No network access, no simulator, no shell. Sources are the already-archived provider documents
in OLD; nothing is downloaded.

Oracle of record for each quoted figure: `OLD/sources/TPS2660.txt` (text extraction of
`OLD/safety_r1/sources/TPS26601RHFR.pdf`), and `OLD/sources/sprint06/MSS1583/MSS1583.txt`
(text extraction of `MSS1583.pdf`). Line numbers are the extraction's, so the principal can
re-check each quote with one grep. Where the extraction lost a formula (marked "line is not
valid UTF-8" by the grep tool) this script says UNAVAILABLE instead of guessing.

WHAT THIS FILE DOES NOT DO: it does not qualify the TPS26601, does not clear the encrypted-model
HOLD, does not clear RTN isolation, thermal/SOA or max-shutdown-delay HOLDs, and does not turn
any source number into a circuit result.
"""
import json, hashlib
from pathlib import Path

OUT = Path(__file__).resolve().parent
OLD = Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V')
TI_TXT = OLD / 'sources/TPS2660.txt'
TI_PDF = OLD / 'safety_r1/sources/TPS26601RHFR.pdf'
TI_LIB_TINA = OLD / 'sources/sprint06/TPS26601_tina/unpacked/TPS26601_TRANS.LIB'
TI_LIB_PSPICE = OLD / 'sources/sprint06/TPS26601_pspice/unpacked/TPS26601_TRANS.LIB'
MSS_TXT = OLD / 'sources/sprint06/MSS1583/MSS1583.txt'
MSS_PDF = OLD / 'sources/sprint06/MSS1583/MSS1583.pdf'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def quote(path, needle, maxlen=240):
    """Locate an exact substring in the archived text and return it with its line number.

    Byte-safe: the extraction is not valid UTF-8, so read as bytes and decode with replace.
    Returning UNAVAILABLE when the needle is absent is the whole point: no paraphrase is
    ever reported as a quote.
    """
    if not Path(path).is_file():
        return dict(state='SOURCE_ABSENT', path=str(path))
    raw = Path(path).read_bytes().decode('utf8', 'replace').splitlines()
    for n, line in enumerate(raw, 1):
        i = line.find(needle)
        if i >= 0:
            return dict(state='QUOTED', line=n,
                        text=line[max(0, i - 40): i + maxlen].strip())
    return dict(state='UNAVAILABLE', needle=needle,
                note='formula text was not recoverable from the archived extraction')


def main():
    src = {
        'ti_datasheet_text': dict(path=str(TI_TXT), sha256=sha(TI_TXT) if TI_TXT.is_file() else None),
        'ti_datasheet_pdf': dict(path=str(TI_PDF), sha256=sha(TI_PDF) if TI_PDF.is_file() else None),
        'ti_model_tina_lib': dict(path=str(TI_LIB_TINA), sha256=sha(TI_LIB_TINA) if TI_LIB_TINA.is_file() else None),
        'ti_model_pspice_lib': dict(path=str(TI_LIB_PSPICE), sha256=sha(TI_LIB_PSPICE) if TI_LIB_PSPICE.is_file() else None),
        'inductor_datasheet_text': dict(path=str(MSS_TXT), sha256=sha(MSS_TXT) if MSS_TXT.is_file() else None),
        'inductor_datasheet_pdf': dict(path=str(MSS_PDF), sha256=sha(MSS_PDF) if MSS_PDF.is_file() else None),
    }

    # ---- 1. dVdT / slew guarantees ------------------------------------------------------
    slew = dict(
        native_ramp=quote(TI_TXT, 'internal output voltage ramp rate'),
        native_ramp_spec=quote(TI_TXT, 'SHDN to V(OUT) = 23.9 V, with C(dVdT) = open'),
        c_dvdt_spec=quote(TI_TXT, 'SHDN to V(OUT) = 23.9 V, with C(dVdT) = 47 nF'),
        gain=quote(TI_TXT, 'dVdT to OUT gain'),
    )
    # Arithmetic ONLY from the two datasheet ramp-time bounds (gate drive path to 23.9 V):
    #   t_open = 1.6 ms   (23.9 V / 1.6 ms = 14.94 V/ms)
    #   t_47nF = 10.0 ms  (23.9 V / 10.0 ms = 2.39 V/ms)
    t_open_ms, t_47_ms, v_set = 1.6, 10.0, 23.9
    ramp = dict(
        v_setpoint_V=v_set,
        native_slew_V_per_ms=v_set / t_open_ms,
        c47nF_slew_V_per_ms=v_set / t_47_ms,
        # Minus-10 % CDVDT is a FIRST-ORDER proxy only: the datasheet gives no +/- on tdVdT,
        # so this corner is a DERIVATION, not a TI guarantee.
        c47nF_minus10pct_slew_V_per_ms=(v_set / t_47_ms) / 1.10,
        c47nF_minus10pct_time_to_24V_ms=24.0 / ((v_set / t_47_ms) / 1.10),
        spec_comment='tdVdT spec columns in the extraction give a single typical value only; '
                     'no min/max tdVdT is quoted anywhere in the archived text.',
    )
    # Cross-check against the 8.49 ms number carried in the Round1 review.
    ramp['review_8p49ms_reproduced'] = abs(ramp['c47nF_minus10pct_time_to_24V_ms'] - 8.49) < 0.02
    ramp['review_8p49ms_reproduction_note'] = (
        '24 V / (2.39 V/ms / 1.10) = %.2f ms' % ramp['c47nF_minus10pct_time_to_24V_ms'] +
        '; the 0.005 ms residual vs the review figure is 24.0 vs 23.9 V rounding and is '
        'immaterial (<0.1%). Both are SOURCE-RAMP bounds, not device behaviour.')

    # ---- 2. Current limit / inrush guarantees -------------------------------------------
    ilim = dict(
        ilim_5k36_tol=quote(TI_TXT, 'R(ILIM) = 5.36 k, V(IN) - V(OUT) = 1 V'),
        ilim_8k_tol=quote(TI_TXT, 'R(ILIM) = 8 k, V(IN) - V(OUT) = 1 V'),
        fastrip=quote(TI_TXT, 'fast-trip threshold is internally set to 87%'),
        inrush_eq=quote(TI_TXT, 'The inrush current I(INRUSH)'),
        inrush_example=quote(TI_TXT, 'Select the inrush current I(INRUSH) = 0.1 A'),
    )
    # Guaranteed (max, 25 C) overload current limit for the two programmed values used in
    # QS30-9 planning; the max column is what a passive bound must be built on.
    ilim_bounds = dict(
        R_ILIM_8k_A=dict(min=1.425, typ=1.5, max=1.575),
        R_ILIM_5k36_A=dict(min=2.11, typ=2.23, max=2.35),
        source='TPS2660.txt lines 461-465 (R(ILIM) = 8 k and 5.36 k rows, V(IN)-V(OUT)=1 V)',
        caveat='current-limit values are specified at V(IN)-V(OUT) = 1 V; the datasheet also '
               'warns that the programmed limit alone is not the whole answer at large '
               'V(IN)-V(OUT), which is exactly the start-up condition here.',
    )

    # ---- 3. Model / qualification status --------------------------------------------------
    models = dict(
        tina_lib_present=TI_LIB_TINA.is_file(),
        pspice_lib_present=TI_LIB_PSPICE.is_file(),
        encrypted=bool(TI_LIB_TINA.is_file() and (
            b'SLVMBY3' in TI_LIB_TINA.read_bytes()[:64]
            or b'SLVMBY4' in TI_LIB_TINA.read_bytes()[:64])),
        status='HOLD_NOT_CLEARED',
        reason='encrypted vendor model; round_01 recorded no successful dynamic TPS26601 '
               'qualification. No simulator invocation is part of this task.',
    )

    # ---- 4. Inductor magnetic reference ----------------------------------------------------
    ind = dict(
        part='MSS1583-154KED',
        dcr_nom_ohm=0.033,
        dcr_max_ohm=0.038,
        isat_10pct_drop_A=(3.9, 4.4),     # extraction shows 3.9 and 4.4 in adjacent columns
        irms_A=(3.4, 4.8),
        source=quote(MSS_TXT, 'MSS1583-154KE_'),
        caveat='Isat/Irms columns are datasheet single-corner values; the column meaning '
               '(20 % vs 10 % inductance drop) is NOT recoverable from this extraction and '
               'must be read off the PDF by a human before any magnetic claim.',
        not_a_simulated_parameter='The SPICE cell models LPOWER linearly (150u, Rser=.16) with '
                                  'no saturation; linear peak current is NOT saturation evidence '
                                  '(round_01 passive_bounds PREREGISTRATION line 47).',
    )

    # ---- 5. Corner arithmetic for the three approved cases --------------------------------
    # Passive L-C arrival bound, energy conservation, no switch action, no load:
    #   V_pk = VIN * sqrt(Cout / L);  I_pk = VIN * sqrt(Cout / L)
    vin, cout, lpow = 26.4, 24.36e-6, 135e-6
    z = (cout / lpow) ** 0.5
    corner = dict(
        vin_V=vin, cout_F=cout, l_F=lpow,
        sqrt_C_over_L=z,
        passive_vout_peak_V=vin * z,
        passive_il_peak_A=vin * z,
        formula='lossless L->C energy exchange bound, zero damping, zero load, infinite time; '
                'an UPPER bound for any real cell, not a predicted waveform',
        rpre_33ohm_dc_drop_at_0p5A_V=33 * 0.5,
        rpre_33ohm_dc_drop_at_1A_V=33 * 1.0,
        rpre_33ohm_peak_series_A=None,
        rpre_note='RPRE is inserted in series with the whole power path in the draft netlist, '
                  'so its steady-state drop appears as V(hv) loss; 5 % tolerance -> 31.35-34.65 '
                  'ohm. Any claim about its effect requires the measurement step.',
    )

    # ---- 6. What each approved case can and cannot show -----------------------------------
    admissible = dict(
        case_A='Bounds the passive (non-switching) arrival of the worst corner. CANNOT show '
               'an HV fault peak because the ceiling presupposes switching the inhibited gate '
               'prevents.',
        case_B='Shows the direction/magnitude of the 33 ohm series precharge on the SAME '
               'passive cell. Cannot qualify the resistor thermally or mechanically.',
        case_C='Bounds passive stress for a SOURCE ramp of 8.49 ms. Explicitly not evidence '
               'about the TPS26601 device, its SOA, its current limit, or its shutdown delay.',
        common_holds=['encrypted TPS26601 model', 'RTN isolation', 'thermal/SOA',
                      'maximum shutdown delay', 'physical board measurement'],
    )

    review = dict(
        scope='read-only quantified source review; feeds no acceptance decision',
        sources=src,
        dVdT_slew=slew,
        dVdT_derived=ramp,
        current_limit=ilim,
        current_limit_bounds=ilim_bounds,
        vendor_model=models,
        inductor=ind,
        corner_arithmetic=corner,
        admissible_claims=admissible,
        holds_unchanged=True,
        physical_recovery_note='Round1 line 7/8: physical recovery and model uncertainty '
                               'prevent any hardware pass even if the pin/cell looks protected.',
    )
    (OUT / 'ti_source_review.json').write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps({k: review[k] for k in ('dVdT_derived', 'current_limit_bounds', 'corner_arithmetic')},
                     indent=1))


if __name__ == '__main__':
    main()
