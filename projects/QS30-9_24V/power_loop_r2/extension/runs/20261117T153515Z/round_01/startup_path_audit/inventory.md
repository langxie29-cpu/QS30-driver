# startup_path_audit — inventory (Round 3, CODE ONLY)

U101 = **TPS26601RHFR**. Sources: `OLD/sources/TPS2660.txt` (SLVSDG2G, July 2016, rev. Dec 2019),
`OLD/docs/S05_CIRCUIT_CANDIDATES.md` L30/L59, `OLD/docs/S06_CIRCUIT_DELTA.md` L9/L24,
`R2/ROUND1_REVIEW.md`, `R2/startup_bounds.py`, `R2/evidence/principal/startup_bounds/results.json`.

## Fact table

| # | Fact | Source line |
|---|------|-------------|
| 1 | MODE **Open** on TPS26601 = *electronic circuit breaker with latch-off*; auto-retry is TPS26600/26602. NOT continuous current limiting. | TPS2660.txt L170, L1412–L1413, L1717–L1719 |
| 2 | Current-breaker threshold I(CB) from R(ILIM); FLT asserts after t(CB) while I(CB) < I(LOAD) < I(FASTRIP). FET turns *off* and latches until SHDN reset or POR. | L1483, L1502–L1504, L276 |
| 3 | MODE = **402 kΩ to RTN** = *active current limiting with latch-off*; MODE shorted to RTN = limiting **with auto-retry**. Different behaviour, still latched for 402 k. | L554–L555, L1426–L1430 |
| 4 | Fast-trip comparator (I > I(FASTRIP)) turns the FET off in **250 ns typical**. | L1528–L1529, L615 |
| 5 | Guaranteed (MIN/MAX) limits that *do* exist: GAIN(dVdT) 23.75/**25.5** V/V; I(OL) @12 kΩ 0.95/1.05 A; I(CB) @120 kΩ MODE-open 0.045/0.11 A; @5.36 kΩ 2.0/2.4 A; V(REVTH) −15/−5 mV. | L453, L461, L478, L480, L530 |
| 6 | **TYPICAL-ONLY** delays (no MAX published): t(CB)(dly) 4 ms; t(FASTRIP)(dly) 250 ns; t(CBretry)(dly) 540 ms; t(dVdT) 10 ms @47 nF and 23.9 V/1.6 ms with dVdT open. No datasheet maximum may be claimed. | L642, L615, L644, L635–L636, L1365 |
| 7 | dVdT programming current **5.5 µA** = prompt/principal worst-case constant (not a TPS2660.txt line); IFLT/IdVdT/ISHDN sink absolute max **10 mA**. | prompt INPUT; TPS2660.txt L309 |
| 8 | Encrypted TPS26601 models (SLVMBY3 PSpice, SLVMBY4 TINA) did not pass ngspice; model also does not model temperature. **No substitution.** | S06_CIRCUIT_DELTA.md L24; sprint06/manifest.json L58–L93 |
| 9 | S05 planned MODE13 **floating** (latch), R(ILIM) 12 kΩ → RTN, C(dVdT) 47 n, RTN100 separate from GND. | S05_CIRCUIT_CANDIDATES.md L59 |
| 10 | R8 approves controlled slew with LT enable inhibited + independent 33 Ω -5% precharge fallback; **bypass/default-off supervisor not implemented and cannot qualify**. | ROUND1_REVIEW.md L8 |

## Correct inductor row (do not substitute another row)

**MSS1583-154KED only** — 150 µH ±10 %, **DCR max 0.159 Ω**, I(sat) at 10/20/30 % drop = **3.1 / 3.6 / 3.9 A**, I(rms) at 20/40 °C rise = **1.55 / 2.2 A** (S06_CIRCUIT_DELTA.md L9; manifest sha256 `dba193ba…`). The `MSS1583-154KE_` row in the extracted text is **not** this part and is not used.

## Arithmetic script

`startup_arith.py` (141 lines, numpy, writes `startup_arith.json` in this directory) computes from datasheet limits and the copied `results.json` literals: worst-case slew rate & 0→26.4 V rise for Cmin 42.3 n / Imax 5.5 µA / Gmax 25.5; P_max = Vin²/(4R) into fixed 33 Ω vs the 6 W requirement; the 0.5 Ω that 6 W would actually need; and startup loss ½CU² into 24.36 µF. **Not executed here** — no shell, jobs, simulator or model call was made.

## Status

Arithmetic bounds and source lines only. Every numeric PASS threshold unchanged; manufacturing HOLD unchanged; no bypass hardware, no bypass model, **no max delay** claimed.
