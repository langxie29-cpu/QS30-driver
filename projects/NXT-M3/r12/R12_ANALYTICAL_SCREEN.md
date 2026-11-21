# R12 analytical pre-screen — why lower frequency / lower inductance can help

**Evidence level: IDEALIZED ESTIMATE ONLY. Not an executed ngspice result, not an EVT release.**

## A. Freeze the R11 operating point

R11 source: `projects/NXT-M3/r11/BLOCKER_CLOSURE_REPORT.md`, `LOWLINE_BLOCKER_SWEEP.csv`, `sim/controller_proxy.inc`.
- Source 4.75 V, round-trip cable 0.190 ohm, 3.3 V simultaneous load 2.475 W, HV tube load 9.9 mA; HV-boost input observed roughly 4.32–4.38 V in proxy cases.
- Nominal HV target 170 V; selected conservative analytical `Vin_power = 4.35 V`.
- Two 496 kohm bleeders consume 2*(170/496000)=0.685 mA. R11 also has FB, OVP and residual sense divider currents (~0.100, ~0.085, ~0.092 mA).
- At 170 V, total output-side draw is roughly 9.900 + 0.685 + 0.100 + 0.085 + 0.092 = **10.862 mA**, or **1.847 W**. The division currents and bleeder should not be omitted from sizing even when model load BLOAD is 9.9 mA.
- For rough feasibility **only**, assume `efficiency = 0.60`. Changing efficiency changes the entire table.

## B. DCM single-inductor, first-order screening

At high boost ratio and DCM, approximate stored inductor energy per switching cycle `E ~= Pout / (eta*f)`, `Ipk ~= sqrt(2E/L)`, and `Ton ~= L*Ipk/Vin`.
Off time approximated as `Toff ~= L*Ipk/(Vout-Vin)`. These are **only feasibility approximations**, ignoring parasitics, min-off time, skip, slope compensation, MOSFET gate drive, diode recovery, ripple, protection overhead and magnetic saturation.

| L | f | Period | Approx Ipk | Approx Ton | Interpretation |
|---|---:|---:|---:|---:|---|
| 17.6 µH | 100 kHz | 10.0 µs | 1.87 A | 7.57 µs | more conduction-time margin; highest peak current |
| 22 µH | 100 kHz | 10.0 µs | 1.67 A | 8.46 µs | possible but tight against controller/duty losses |
| 26.4 µH | 100 kHz | 10.0 µs | 1.53 A | 9.27 µs | very tight; any maximum duty/blanking can force dropout |
| 33 µH | 100 kHz | 10.0 µs | 1.37 A | 10.36 µs | **not possible in this simplified 60% model** |
| 33 µH | 80 kHz | 12.5 µs | 1.53 A | 11.59 µs | tight, check Toff and minimum off time |
| 33 µH | 50 kHz | 20.0 µs | 1.93 A | 14.65 µs | plausible timing margin; check peak current and saturation |

This supports a **hypothesis**, NOT a verified root cause: 22→26.4 µH may hit max-on-time/peak energy limits in the R11 proxy, while 22 µH/80 kHz is better. The actual controller must be proven. R11 proxy has synthetic slope compensation, timing and an assumed maximum on-time. Never copy its success to silicon.

## C. Practical decisions before selecting controller

1. Test the *same* magnetic, MOSFET and realistic losses at 4.35 V HV input, 7.65/9.9 mA + real divider/bleeder draw. Sweep frequency 40/50/65/80/100 kHz, L ±20%, ambient, Rds(on), DCR, gate voltage, current sense thresholds, diode reverse recovery.
2. UCC3803's 4.1 V on/3.6 V off UVLO must be reviewed at the actual controller pin with startup transients and 4 V VREF/driver headroom. The fact that 4.35 V > 4.1 V does **not** prove a valid design.
3. Compare LM3478/LM3488 (2.97–40 V controller range) against UCC3803 at same 4.35 V low-line input. **Do not claim controller-model qualification unless the actual manufacturer's macro-model ran successfully** (with exact compatibility changes documented).
4. For flyback, use `Vds_peak = Vin + Vreflected + leakage_spike` measured from the actual winding ratio/leakage and clamp. 100 V MOSFET used in open-source flyback is **not** an alternative for NXT's single-inductor Boost stage.
5. Evaluate controller + magnetic + MOSFET + diode + HV capacitor + protections as one BOM; savings from a controller alone are insufficient to meet the ¥60 whole-HV target.

## D. Cost baseline — R10, single module, historical estimate

The following R10 BOM cost groups sum to **¥104.00**, before allocation of the shared front-end eFuse U1, fault latch/wdog and PCB area, and before the Type-C R11 expansion:

| R10 group | CNY |
|---|---:|
| LM5155 boost controller | 11.50 |
| L3 magnetic | 5.50 |
| Q32 MOSFET | 17.12 |
| D3 rectifier | 0.90 |
| U16/U18 gate bias/driver | 7.50 |
| Feedback/sense/comp/snubber | 5.40 |
| C47 HV reservoir | 10.50 |
| U11 HV cut/reverse block | 13.68 |
| independent HV OVP/OCP | 6.00 |
| branch fault detect allowance | 8.00 |
| permanent bleeders | 2.80 |
| anode resistors | 4.20 |
| 5 V fuse/TVS and protection passives | 5.40 |
| residual voltage sense/re-arm | 5.50 |
| **subtotal** | **104.00** |

**This subtotal is a defined comparable cost scope, not a fully priced final HV BOM**. Some line items are estimates/allowances; R10 safety latch/window watchdog and U1 shared input eFuse are not in the subtotal. An apples-to-apples HV<60 quote must track those components and avoid double counting, rather than silently excluding them.

**Current objective:** demonstrate a source-qualified BOM less than 60 CNY per complete HV set while retaining the named protections; the `HV_COST_CEILINGS.csv` is the planning cap (sum 55.50), not a BOM or procurement claim.

## E. Reference links

- Open-source 5V 170V DCM boost with UCC3803, 33 µH, KiCad/BOM/LTspice: https://github.com/drkmsmithjr/NixiePowerSupply
- LM3488/hand-wound EFD15 flyback with measured 5.07 V→180 V at 9.5 mA: https://github.com/esynr3z/nixie-ps
- LT3757/DA2032-ALB 1:10 flyback BOM: https://github.com/tonyp7/170v-nixie-power-supply
- TI controllers: https://www.ti.com/product/UCC3803 ; https://www.ti.com/product/LM3478 ; https://www.ti.com/product/LM3488
