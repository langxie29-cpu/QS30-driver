## QS30 R3 Round1 Stress Independent Review (draft, no tools)

**Status: NOT a sign-off.** No manufacturing approval granted. Values below are engineering assessments from the supplied evidence/assumptions only. Guaranteed vs typical must remain separated; where only "typical" is credible, treat as unproven for tolerance/end-of-life.

### 1. Metric definitions (required, physically separated)

For every component report these separately; do not mix external-terminal signed integrals with intrinsic silicon loss:

1. **External terminal power integral** \(P_{term}(t)=v_{term}(t)\,i_{term}(t)\), signed, per terminal, integrated over one switching cycle and over repetition window.
2. **Intrinsic silicon loss** (junction-referenced; includes reverse-recovery, avalanche, channel, body-diode, gate-charge loss), reported per device.
3. **Energy storage return**: net energy returned to source/bulk per cycle (e.g., inductor/resonant return), explicitly not counted as dissipation.
4. **Repetition allowance**: per-pulse energy × repetition rate vs a *repetitive* rating; single-pulse \(E_{AS}\) may not be used.
5. **Peak/instantaneous** values: \(V_{DS}\), \(V_{GS}\), \(I_D\)/\(I_S\), \(dI/dt\), \(dV/dt\), \(T_J\) (where a thermal model exists).
6. **RMS and average** terminal currents and junction temperatures over mission profile.
7. **Model validity flags**: temperature range, whether thermal model exists, model version/source.

### 2. MOSFET STP9NK50Z (LG7.5nH, LS7.5nH, LD4.5nH, RD0.584Ω; package L not duplicated)

- Device abs max: 500 V, \(V_{GS}\pm30\) V, \(I_D\) 7.2 A@25 °C / 4.5 A@100 °C, \(I_{DM}\) 28.8 A (pulse, SOA-limited), \(I_{AR}\) 7.2 A (T\(_J\)-limited), \(E_{AS}\) 190 mJ single @25 °C, \(I_D\) 7.2 A, \(V_{DD}\) 50 V; \(R_{\theta JC}=1.14\) °C/W, \(R_{\theta JA}=62.5\) °C/W.
- **\(E_{AS}\) is a single-pulse start-25 °C value; it is not a repetitive allowance.** Any repetitive avalanche/recovery budget must come from SOA/repetitive ratings and thermal model; neither is provided in the supplied model (25 °C only, no thermal model).
- Required metrics: peak \(V_{DS}\) (incl. avalanche), peak/ringing \(V_{GS}\) (must stay within ±30 V guaranteed; R2 saw internal \(V_{GS}\) −0.412…+11.909 V — margin exists but not bounded over all transients), peak \(I_D\)/\(I_S\), instantaneous shunt and device power, \(dI/dt\) spike power, junction temperature via a real thermal model (cannot be signed off without one).
- **Cannot be signed off**: repetitive avalanche/recovery energy, T\(_J\) rise, worst-case \(V_{GS}\) ringing, model validity beyond 25 °C.

### 3. R2 observations and interpretation

R2 stable nominal 170 V, sense 0.10955 V, but pulses retained. R2 showed: drain external −311 V, intrinsic \(V_{DS}\) −0.651 V, internal \(V_{GS}\) −0.412…+11.909 V, source shunt 10–12 A, \(I_L\sim1.65\) A, diode reverse ~10 A and reverse ~400 V avalanche-like. Qrr integrated −112.60 nC over a fixed 1.02–1.10 µs window **includes displacement current**; different datasheet \(t_{rr}\) test conditions do not permit inferring a max Qrr.

KCL (use as-is; verify sign conventions against model):
- \(I_{Qd}=I_L-I_{DREC}-I_{RSNUB}\)
- \(I_{Qs}=-I_{RSRC}-I_{RF}+I_{RGS}-I_{RNEG}\)
- \(I_{Qg}=(V_{out}-V_{gate})/22-I_{RGS}+I_{RNEG}\)

The drain external −311 V vs intrinsic −0.651 V indicates the external metric is dominated by package/parasitic/reference path, not intrinsic silicon stress. **Do not use external terminal magnitude alone as intrinsic stress.** Conversely, −0.651 V intrinsic does not mean the part is safe; the 400 V reverse event and ~10 A are the stress to bound.

### 4. Inductor Coilcraft MSS1583-154KE

150 µH ±10%; DCR max 0.159/0.160 Ω @25 °C; L drop 10/20/30 % at 3.1/3.6/3.9 A; \(I_{rms}\) 1.55/2.2 A for 20/40 °C rise. Hot DCR and hot saturation unknown. Required: peak/RMS current vs saturation, hot R rise, temperature. Cannot sign off hot behavior without measured/derated data.

### 5. Shunt 0.062 Ω (value only, no exact MPN)

Required: peak instantaneous power \(=I^2R\), RMS power, pulse energy per cycle, thermal resistance/pulse rating (unknown MPN). At 10–12 A, instantaneous \(P=0.062\times(10\text{–}12)^2=6.2\) W (10 A) to 8.93 W (12 A); at 1.65 A \(\approx0.169\) W. These are instantaneous only; do not treat as thermal rating.

### 6. RC delay tolerance (22 Ω, 4.7 nF; assume 1 % R, 5 % C)

\(\tau=RC\), nominal 103.4 ns. Worst corners:
- Min: \(21.78\ \Omega\times4.465\text{ nF}=97.25\) ns
- Max: \(22.22\ \Omega\times4.935\text{ nF}=109.66\) ns

So \(\tau\approx97.3\)–109.7 ns (\(\pm\sim6\) %). This is *candidate delay* only; it must be compared to LT3757A blanking (100 ns — **verify guaranteed vs typical; propagation/threshold maxima unavailable**) and to real switching transition times. Not a validated dead-time/blanking guarantee.

### 7. \(\Delta I\) over delay vs 135/121.5 µH

For \(\Delta I=(V/L)\cdot\Delta t\) at 170 V:
- \(L=135\ \mu H\): 1.259 A/µs → at 97.25/103.4/109.66 ns ≈ 0.1225/0.1302/0.1381 A
- \(L=121.5\ \mu H\): 1.399 A/µs → ≈ 0.1361/0.1447/0.1534 A

These bound the current increment attributable to the candidate delay. Repetition/thermal effect still requires the per-cycle energy and thermal model.

### 8. PCB parasitic sensitivity at 1 A/ns

\(V=L_{par}\,dI/dt\). At 1 A/ns:
- 1 nH → 1 V; 5 nH → 5 V; 10 nH → 10 V.

So a few nH of layout/source/drain/Kelvin inductance produces multi-volt offsets in gate-drive/sense loops and can explain the R2 external −311 V vs intrinsic −0.651 V discrepancy. **Parasitic inductance must be extracted/measured, not assumed**; the gate/source Kelvin and shunt routing are stress-critical.

### 9. Why simple absolute-maximum current checks are insufficient

Because (a) \(I_{DM}/I_{AR}\) are SOA/T\(_J\)-limited, not instantaneous switching limits; (b) stresses are energy/pulse-width/repetition dependent (avalanche, reverse recovery, body diode); (c) external terminal magnitudes conflate parasitic/package/reference effects with intrinsic silicon stress; (d) junction temperature and thermal model are absent; (e) abs max values are guaranteed device limits, while the circuit stress depends on parasitics, timing tolerance, and hot parameters (DCR, saturation, capacitance). A single \(I<28.8\) A or \(V<500\) V check does not prove SOA compliance (and similarly for Qrr/\(E_{AS}\)).

### 10. Other bounded items

- Output caps ECQE2106JF 10 µ/250 V ×2 + 300 n module: ESR 0.1 Ω is a **placeholder**, not MPN ESR. Required: ripple RMS current, voltage derating, self-heating; cannot sign off.
- Negative gate SS14: candidate only; pulse bound unknown; not approved.
- LT3757A: 100 ns blanking must be confirmed guaranteed vs typical; propagation/threshold/cycle-by-cycle max limits unavailable.

### 11. Bounded alternative diode exploration (max 2 candidates; no blind recommendation)

Only both listed as **candidates requiring credible model prerequisites** (reverse-recovery charge, junction capacitance, thermal model, max repetitive avalanche/reverse energy, temperature range, and correlation to datasheet test conditions). Neither is recommended until the model is credible against the R2 measured Qrr/displacement issue and thermal model exists:
1. Candidate A: higher-voltage ultrafast/soft-recovery diode with specified max \(Q_{rr}\), \(t_{rr}\), and repetitive reverse-energy limit — precondition: pulsed reverse-recovery and thermal model.
2. Candidate B: SiC Schottky (if voltage class permits) — precondition: capacitance/leakage/thermal model, surge/repetitive current limit, and no reverse-recovery assumption from Si test data.

### 12. Cannot be signed off (summary)

- MOSFET repetitive avalanche/SOA energy and T\(_J\) (no thermal model, \(E_{AS}\) non-repetitive).
- Qrr/negative-Qrr interpretation and max Qrr (contaminated integration window; datasheet test mismatch).
- Shunt thermal/pulse rating (no MPN).
- Inductor hot saturation/DCR (unknown).
- Output cap ESR/ripple/self-heating (placeholder ESR).
- SS14 pulse bound.
- LT3757A blanking/propagation guaranteed limits.
- PCB parasitic inductance and its effect on external-terminal readings.
- Any manufacturing release.

**Assumptions to confirm:** RC minimum/maximum corners are for candidate delay only; 170 V nominal for \(\Delta I\); shunt current 10–12 A per R2; all "max" values are device/component maxima as supplied; no model beyond 25 °C for the MOSFET.