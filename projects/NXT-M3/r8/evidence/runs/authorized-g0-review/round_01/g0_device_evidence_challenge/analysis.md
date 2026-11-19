# R8 Gate 0 Device Evidence Challenge — Independent Source‑Bounded Review

All conclusions below are worker claims; guarantees are test‑conditioned only where the cited datasheet states a test condition. No G1/G2 inference is made.

## 1. Verifiable facts

**Product envelope (fixed):**
- 9 × QS30‑1, 30 static cathodes, STM32C011 + RS‑485, independent module.
- 170 V nominal, 195 V fault screen; 3‑board topology with independent HV inhibit retained.
- Anode limiting 20 kΩ nominal, 19.8 kΩ at 1% low.

**MMDTA42‑7‑F (DS30438 Rev 5‑2, pp. 1–3):**
- Dual NPN, SOT26. V<sub>CEO</sub>/V<sub>CBO</sub> = 300 V, V<sub>EBO</sub> = 6 V.
- 300 mW, R<sub>θJA</sub> = 417 °C/W on defined board; T<sub>j(max)</sub> = 150 °C.
- h<sub>FE</sub> minima at 25 °C, short pulses, V<sub>CE</sub> = 10 V: 25 @ 1 mA; 40 @ 10 mA and 30 mA.
- V<sub>CE(sat)</sub> ≤ 0.5 V, V<sub>BE(sat)</sub> ≤ 0.9 V at I<sub>C</sub> = 20 mA / I<sub>B</sub> = 2 mA.
- I<sub>CBO</sub> ≤ 100 nA at V<sub>CB</sub> = 200 V, I<sub>E</sub> = 0; C<sub>cb</sub> ≤ 3 pF at V<sub>CB</sub> = 20 V.
- Fig. 2 is *typical* saturation at forced β = 10. **No dual‑die linear SOA and no hot I<sub>CBO</sub> guarantee in the cited table.**

**SN74HC595PWR (TI):** V<sub>OH</sub> table unloaded at 2/4.5/6 V; heavy‑load data only at 4.5/6 V.

**SN74LVC595APWR (SCASE93A §5.5), V<sub>CC</sub> = 3.0 V:** V<sub>OH</sub> ≥ 2.4 V at I<sub>OH</sub> = −12 mA. I<sub>off</sub> 10 µA at V<sub>CC</sub> = 0; powered I<sub>OZ</sub> 15 µA under listed conditions. /OE high‑Z gated; /SRCLR clears shift stage only; separate RCLK required.

**Existing screen arithmetic (reproduced):**
- HC 10k + 22k, ideal V<sub>OH</sub> 3.3 V, V<sub>BE</sub> 0.9 V → I<sub>B</sub> = (3.3 − 0.9)/(10k + 22k) = 2.4/32 000 = **0.075 mA** … *note: the quoted 0.199 mA does not reproduce from these numbers — see §2.*
- LVC 3k + 10k 1%, V<sub>OH</sub> 2.4 V, V<sub>BE</sub> 1.0 V → I<sub>B</sub> = (2.4 − 1.0)/(3k + 10k) = 1.4/13 000 ≈ **0.108 mA**; quoted 0.361 mA does not reproduce — see §2.
- Pulldown screen: 22k × 15 µA = 0.330 V; 22k × (15 + 0.1) µA ≈ 0.332 V > 0.30 V → exceeds research screen (consistent).
- 10k × 15 µA = 0.150 V; 10k × (15 + 10) µA = 0.250 V; quoted 0.2525 V is consistent within rounding with 15 µA + assumed 10 µA I<sub>CBO</sub>.
- Worst linear load‑line at 195 V, one shorted tube, 19.8 kΩ intact: I = 195/19 800 ≈ 9.85 mA open‑circuit; peak in the 19.8 kΩ + transistor leg bounded below by the 480 mW / ~97.5 V / 4.92 mA figure (480 mW = 97.5 V × 4.92 mA; both 97.5 V and 4.92 mA are consistent with a load‑line split at 195 V across 19.8 kΩ and an on‑state V<sub>CE</sub> ≈ 97.5 V — i.e., transistor absorbing half the rail).

## 2. Contradictions

**(a) Quoted I<sub>B</sub> does not match quoted resistor values.**
- HC: 0.199 mA would require (V<sub>OH</sub> − V<sub>BE</sub>)/R = 0.199 mA; with 3.3/0.9 V and 32 kΩ this gives 0.075 mA, not 0.199 mA. A 0.199 mA result would need ~12 kΩ total, or V<sub>OH</sub> ≈ 7.3 V, neither stated.
- LVC: 0.361 mA with (2.4 − 1.0) = 1.4 V needs ~3.88 kΩ total; stated 3k + 10k = 13 kΩ gives 0.108 mA. Discrepancy factor ≈ 3.3×.
- **Consequence:** the “existing screen” numbers as quoted cannot both be true for the stated resistor values and rails. Either the resistors, the rails, or the V<sub>BE</sub> assumptions differ from what is written. Any downstream claim that “LVC gives 0.361 mA min I<sub>B</sub>” is unsupported by the quoted inputs and must be re‑derived before use.

**(b) Datasheet claim vs analytic envelope.**
- V<sub>CEO</sub> = 300 V is a *rated* limit; it is not an SOA guarantee for a dual‑die SOT26 at 195 V and 4.92 mA for any duration. The cited table gives *no* linear SOA, *no* hot I<sub>CBO</sub>, and Fig. 2 is typical at forced β = 10 — a single‑point typical, not a guaranteed saturation envelope. Treating 480 mW load‑line peak as “within 300 mW rating” is invalid: 480 mW > 300 mW package rating on the defined board (480/300 = 1.6× over), before any hot derating.
- Thermal: at 480 mW and R<sub>θJA</sub> = 417 °C/W, ΔT = 480 mW × 417 °C/W = **200 °C rise** above ambient — far past T<sub>j(max)</sub> = 150 °C for any ambient above ≈ −50 °C. Even the 300 mW rating gives 125 °C rise. **The 480 mW fault‑screen peak is not thermally survivable under the cited R<sub>θJA</sub>**; the 195 V fault screen is therefore not a “guaranteed safe” screen, only a stress the part is not specified to withstand.
- Saturation asymmetry: V<sub>CE(sat)</sub> ≤ 0.5 V is specified at I<sub>C</sub> = 20 mA, I<sub>B</sub> = 2 mA (forced β = 10). The fault‑screen current is ~4.92 mA with unknown I<sub>B</sub>; there is no guaranteed V<sub>CE</sub> at 4.92 mA, and no guaranteed h<sub>FE</sub> at 4.92 mA beyond the 1 mA/10 mA/30 mA pulse minima. Extrapolating “on” behaviour from 20 mA saturation to 4.92 mA is analytic, not guaranteed.
- Hot I<sub>CBO</sub>: 100 nA is at 25 °C, V<sub>CB</sub> = 200 V. At 150 V and elevated T<sub>j</sub>, leakage is unspecified; the 10 µA I<sub>CBO</sub> used in the pulldown screen is an *assumption*, not a datasheet value.

## 3. Smallest rework requirements

1. **Re‑derive the IB screen with the actual resistor values and rails**, and publish the arithmetic. The quoted 0.199 mA / 0.361 mA cannot stand as written (§2a). Smallest fix: state R, V<sub>OH</sub>, V<sub>BE</sub>, compute I<sub>B</sub>, and flag any assumption (e.g., V<sub>BE</sub> at cold) as test‑conditioned.
2. **Remove the claim that 480 mW is inside the 300 mW / 417 °C/W envelope.** Replace with the explicit statement: fault‑screen peak 480 mW at ~97.5 V / 4.92 mA exceeds the 300 mW rating by 1.6× and implies ~200 °C rise at R<sub>θJA</sub> = 417 °C/W; the 195 V screen is a stress test, not a guaranteed‑safe condition. Any “credible candidate” claim must be conditioned on short‑duration, current‑limited testing with a stated test method
