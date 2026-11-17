# QS30-9 power_loop_r1 — vendor model inventory (task `vendor_models`, role `model_registrar`)

**Status of this document: faithful inventory only.**
Worker: DeepSeek Flash. Output of this worker is **NOT** an independent design approval.
Every value below is either (a) a byte-level measurement produced by the scripts in this
directory, or (b) a quotation from a retained official document whose SHA-256 is given.
Nothing was simulated by this worker: **no waveform, log, metric or model execution is
claimed here.** No vendor model was rewritten, re-encoded or reformatted.

- Generated: 2026-11-17, scheduler run `20261117T051440Z`, round_01, wave 1.
- Output directory (all paths below are relative to it):
  `projects/QS30-9_24V/power_loop_r1/runs/20261117T051440Z/round_01/vendor_models/`
- Prospective repo: `D:/PROJECTS/dsharness/QS30-power-loop-r1` (worktree `nxt/qs30-power-loop-engineering-r1`).
- Historical read-only workspace: `D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V`
  (its S06C/D/E/F material is **uncommitted**; see §8).

---

## 0. Bottom line

| Question | Answer | Grade |
|---|---|---|
| Are exact vendor SPICE bytes registered with origin/version/license/solver? | Yes, for every artifact that exists locally (§2–§5). | **PASS (inventory)** |
| Is the LT3757A model a genuine ADI-signed native LTspice model? | Yes — extracted byte-identical from the signed `lib.zip`; it is a **binary/encoded** model, LTspice-native only. | PASS (inventory) / model qualification **INCONCLUSIVE** |
| Is a UCC28C43 vendor SPICE model available here, and can it be replayed unmodified? | A TI PSpice model exists in three forms (encrypted 2008, encrypted TINA, unencrypted 2008 library). **No PSpice or TINA simulator is installed locally**, so no unmodified native replay has ever been performed. | model qualification **INCONCLUSIVE** |
| Do the two controllers have *comparable* model fidelity? | **No.** LT3757A is vendor-native in the only native simulator present; UCC28C43 is not, and its unencrypted library contains PSpice-only behavioural sources. Any side-by-side numeric comparison is apples-to-oranges. | blocking (BI-03) |
| Are the MOS / diode / inductor candidates fully modelled by vendors? | MOS: yes for SiHP8N50D and STP9NK50Z, **no** vendor model for STP7N65M2 / IPP60R360P7. Diode: only an IS/N-based model for US1G with no reverse-recovery fit. Inductors: **no SPICE model at all** for MSS1260. | partial → **INCONCLUSIVE** |

---

## 1. Candidates in scope (exact MPN)

Exact MPN authority is `docs/S05_CIRCUIT_CANDIDATES.md` and `safety_r1/circuit/bom_candidates.csv`
(all entries `HOLD_UNVERIFIED / CANDIDATE_NO_ORDER`) in the prospective repo. The
"HV controller" role is contested between UCC28C43 and LT3757A; S05 picked UCC28C43DR and
S06C introduced LT3757A as a competing candidate. **They are not interchangeable netlists**
(`safety_r1/circuit/CIRCUIT_REVIEW.md`, `power_loop_r1/prompts/CODEX_DECISION.md`).

| Role | Exact MPN | Package | Vendor model available locally | Registered sha256 |
|---|---|---|---|---|
| HV PWM controller (S05 baseline) | **UCC28C43DR** | SOIC-8 (D) | PSpice zip + TINA zip + unencrypted PSpice lib | `546fab4c…`, `5eda3f5a…`, `05979bf1…`, `ab3cd5bb…` (§3) |
| HV PWM controller (S06C alternative) | **LT3757AIMSE#PBF** (datasheet family LT3757/LT3757A) | MSOP-10E | Native LTspice model inside signed ADI distribution | `c0328424…` (§2) |
| HV power MOSFET (S05) | **STP9NK50Z** | TO-220 | ST PSpice lib | `6ad61988…` (§4) |
| HV power MOSFET (S06C alt.) | **SiHP8N50D-GE3** | TO-220 | Vishay PSpice Rev B (3 files) | `70965ff7…`, `1980c0ed…`, `523fb2ac…` (§4) |
| HV power MOSFET (S06C alt.) | **STP7N65M2** | TO-220 | **none** (two ST URLs both HTTP 404) | n/a (§4.3) |
| HV power MOSFET (S06C alt.) | **IPP60R360P7** | PG-TO220-3 | **none** (datasheet only) | n/a (§4.4) |
| HV boost diode (S05) | **US1G-E3/61T** | SMA (DO-214AC) | Vishay `us1g.txt` model | `f8669a85…` (§5.1) |
| HV boost diode (alt.) | SS14 | SMA | Thomatronik-derived lib (**third-party, not Vishay**) | `3288afb6…` (§5.2) |
| HV inductor | **MSS1260-154KLD** | 12.3×12.3 mm | **no SPICE model** (datasheet only) | `78be0158…` PDF only (§6) |

Out of scope for this task but present for context: TPS26601RHFR eFuse, UCC27511 driver,
TPS3700/TPS3890/TPS3431 supervisors, LMR51610, TPS2116, TPS62162, HV5622. Their model
artifacts were touched only where a sim-time copy audit needed them (UCC27511, §7).

---

## 2. LT3757A — the only vendor-native model that can run here

### 2.1 Extraction (byte-exact, no rewrite)

Source: ADI signed distribution, downloaded to the historical toolchain folder.

| Item | Value |
|---|---|
| Installer | `LTspice64.msi`, 82 139 136 B, sha256 `62a9f20b630738e6ade20a37551baa91b20760bfb718807d8a2be4caa3421a36` |
| Distributor URL | `https://ltspice.analog.com/download/latest/LTspice64.msi` (from `toolchain/ltspice26/source.json`) |
| `lib.zip` | 39 443 916 B, sha256 `dd0028bb12e3f432ef022570cb7cf64d3c87288c35d1e8159658a4ff986ce094` |
| `examples.zip` | 3 549 504 B, sha256 `319ac0e9adcce7e156aa47050a659919dbd901f1e82ab42fdb156bcefcd54ad6` |
| `LTspice.exe` | 45 461 040 B, file version **24.0.12.0**, sha256 `17f5efb978c0df2e164328b7352801fdc1ed0225827e41669bd9da25893fe96d` |
| Licence | `License.txt`, 35 447 B, sha256 `a3c9a713f97ee80f5731b7f13b00ad87f69a17fe505a8ad837dc6ff66c391c4e`, agreement id **20230822-LTS-CTSLA** |

Extracted with Python `zipfile.read()` → `write_bytes()` and re-read to prove a
round-trip identical payload (`extract_and_hash.py`, field `roundtrip_identical: true`).

| Output copy | Archive / member | Bytes | ZIP CRC32 | ZIP mtime | **sha256 of payload** |
|---|---|---|---|---|---|
| `vendor_bytes/LT3757A.sub` | `lib.zip` : `lib/sub/LT3757A.sub` | 2 572 | `1d44a014` | 2022-05-03T14:36:04 | **`c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634`** |
| `vendor_bytes/LT3757A.asy` | `lib.zip` : `lib/sym/PowerProducts/LT3757A.asy` | 948 | `fbdb5582` | 2022-05-03T14:36:18 | **`4ed5078ebd77e5e697bc61b9124d34b350cdccc7be9a0d32e7def830660c9d76`** |
| `vendor_bytes/LT3757A.asc` | `examples.zip` : `examples/Applications/LT3757A.asc` | 2 890 | `3ae68b0d` | 2022-05-03T14:35:42 | **`867ea5d1f8f90aa56f4dacfadfa4108bfddf0e619c06941bb711d890dba40cb6`** |

The historical spring-06c workspace holds its own copies of `.sub`/`.asy` at
`QS30-1/.../sources/sprint06c/LT3757A_bundled/`; both hash to the same values
(`c0328424…`, `4ed5078e…`), so the historical bundle really is the same vendor bytes.

### 2.2 Model nature and limitations

- `LT3757A.sub` **is not text**: it begins with CRLF `<Binary File>` followed by an
  encoded payload (15 NUL bytes, 938 non-ASCII bytes, 21 lines). It is ADI's
  binary/encoded subcircuit. Its readable interface cannot be inspected from bytes;
  the port order must be taken from the `.asy` symbol.
- `LT3757A.asy` is plain `Version 4` ASCII text (41 CRLF lines) — the 10-pin symbol.
- The **only** simulator in this environment that can consume a binary LTspice
  subcircuit is **LTspice itself** (`LTspice.exe` 24.0.12.0). `ngspice-47` cannot read
  it. Therefore LT3757A replay is LTspice-native and nothing else.
- `LT3757A.asc` is the vendor's own **boost** reference and its own `.tran` directive is
  `.tran 1.5m startup`:
  - `V1 = 12 V` input, `L1 = 10 µH`, `Q1 = FDS6680A`, `D1 = MBR735`, `C1 = 47 µF` (`Rser=.1`, `x2`),
    `R1 = 41.2K`, `R2 = 16.2K`, `R3 = 226K`, `R4 = 22K`, `C2 = 6800p`, `C3 = 4.7 µF`,
    `C4 = .01 µF`, `R5 = 43.2K`, `R6 = 200K`, `Rload = 12 Ω`, `R7 = .01` (SENSE).
  - The reference's nominal output is **not** 170 V and its switch is a **50 V-class**
    FDS6680A; its output cap is a 47 µF low-voltage part, not the QS30 HV film/electrolytic
    stack. **This is a 12 V→low-voltage boost demo, not a 170 V workpoint.**
  - Consequence, stated as a hard rule: **an unchanged LT3757A reference replay can never be
    reinterpreted as 170 V QS30 success.** It can only evidence that the model runs.
- Limitations recorded for downstream users:
  1. encoded body ⇒ no inspection of internal equations, no independent parameter audit;
  2. the ADI licence (**§2.3**) forbids reverse engineering and redistribution;
  3. the model is bound to the LTspice solver; ngspice/PySpice replay would be a
     *conversion*, not vendor-native replay;
  4. the reference does not exercise QS30's HV node, HV MOSFET, HV diode or HV inductor.

### 2.3 Licence (ADI, quoted from the retained `License.txt`)

Agreement **20230822-LTS-CTSLA**. Section 1 grants a *"non-exclusive, non-transferable,
non-sublicensable license, to internally use and copy the PC Software to evaluate Analog
Devices products and also to perform general circuit simulation."* Section 4 states the
Licensee *"shall not modify, reverse engineer, decompile, disassemble or create derivative
works of the Licensed Software"* and *"may not distribute the PC Software under any
circumstances."* Section 5 also restricts publishing benchmark/comparison test results
without ADI's prior written consent.

Practical consequence for this repo: the extracted `vendor_bytes/LT3757A.*` copies are for
**internal** simulation evidence only; they must not be published or committed to a public
repository, and the binary model must not be de-encrypted or patched.

---

## 3. UCC28C43 — TI models, and why they cannot be replayed natively here

### 3.1 Artifacts (both workspaces; hashes are identical in both)

| Artifact | Path (prospective repo under `projects/QS30-9_24V/sources/sprint06/`) | Bytes | sha256 |
|---|---|---|---|
| PSpice package | `UCC28C43_pspice/UCC28C43_pspice.zip` | 103 944 | **`5eda3f5a976ed60ba206d264669d57b70ca1d443e4ede2ea80eb999c44e3b878`** |
| PSpice library (inside the package) | `…/UCC28C43_PSPICE_07NOV2008/UCC28C43_PSPICE_TRANS/ucc28c43.lib` | 43 796 | **`546fab4c7b9208394122f7f4e886496d15e2811af37b4e32cb9edff2eddeaadd`** |
| TINA package | `UCC28C43_startup/UCC28C43_startup.zip` | 10 985 | **`05979bf1f5bb7e99ae56b04686e440e459a4e9ff2b4eff422420def9c2b7e183`** |
| TINA library | `…/UCC28C43_TINA_TRANS/UCC28C43_START.LIB` | 4 846 | **`7b00c5326308d7203d75fa0e77870ed0dd2482305199f88eff67682827d9526a`** |
| Unencrypted PSpice package | `UCCx8C43_unencrypted/UCCx8C43_unencrypted.zip` | 5 008 | **`e246d10eb469cfc46d2fe5ffe19e4f304cfca19bf0ccab92934a0a8d2a456379`** |
| Unencrypted PSpice library | `…/UCC28C43_PSPICE_TRANS_UNENCR_18FEB2016/ucc28c43_trans_unencrypted.lib` | 13 956 | **`ab3cd5bb484570e3e719d7f1d1a5dcf9e0ef48161a9d00eaa84d34dcf5ec26b8`** |
| Datasheet (SLUS458I) | `sources/UCC28C43.pdf` / `.txt` | — | see `hash_manifest_raw.json` |

Distributor URLs, from `sources/sprint06/manifest.json` (recorded 2026-11-14):

- PSpice: `https://www.ti.com/lit/zip/slum033` → final
  `https://www.ti.com/lit/mo/slum033/slum033.zip?ts=1794671615769`, 103 944 B,
  sha256 `5eda3f5a…` — **matches the retained zip exactly**.
- TINA: `https://www.ti.com/lit/zip/slum178` → final
  `https://www.ti.com/lit/mo/slum178/slum178.zip?ts=1794671615768`, 10 985 B,
  sha256 `05979bf1…` — **matches the retained zip exactly**.
- TI product page cited by the runner: `https://www.ti.com/product/UCC28C43`. This worker
  could **not** re-fetch it (§9 BI-09); the slum### document numbers are the stable
  identifiers and are what the retained bytes are keyed on.

### 3.2 Model identity (read out of the clear-text headers)

All three TI models are the same AEi Systems model, released by TI's Analog e-Lab:

- `* Part: UCC28C43 (can be used for UCC38C43 also)`
- `* Date: 11/05/2008`
- `* Model Type: Transient Steady State`
- `* Simulator: PSpice`
- `* EVM Order Number: UCC38C44`, `* EVM Users Guide: slua274a, Oct 2008`
- `* Datasheet: slus458d, Rev Jan 2007` ← note: the model was validated against
  datasheet revision **D**, while the retained datasheet is **revision I (June 2024)**.
- `* Updates: Final 1.00 — Release to Web.`
- `* This model is subject to change without notice. Neither Texas Instruments Incorporated
  nor AEi Systems is responsible for updating this model.`
- Model built with `PSpice Model Editor - Version 16.0.0`.

Public subcircuit interface (identical in all forms):
`.SUBCKT UCC28C43_STEADY COMP FB CS RTCT GND OUT VDD VREF` and
`.SUBCKT UCC28C43_START COMP FB CS RTCT GND OUT VDD VREF`.
Note the **pin order is not the datasheet pin order** — a wrapper `X` line must map it.

### 3.3 Encodings actually present

| Form | Encoding evidence | Can ngspice-47 read it? | Can LTspice read it natively? |
|---|---|---|---|
| TI PSpice `ucc28c43.lib` | `**$ENCRYPTED_LIB`, **23** `$CDNENCSTART` blocks (Cadence CDN encryption) | **No** | **No** |
| TI TINA `UCC28C43_START.LIB` | starts with `<Encrypted Library>`, 37 % printable, no `.subckt` text | **No** | **No** |
| TI "unencrypted" `ucc28c43_trans_unencrypted.lib` | plain ASCII, no encryption markers | Parseable only after transliteration (§3.4) | Parseable only after transliteration (§3.4) |

### 3.4 Why "unencrypted" still is not native replay

The unencrypted library uses **PSpice-only behavioural sources**, for which LTspice has no
native form: `E<name> n+ n- VALUE = { … }` and `G<name> n+ n- VALUE = { … }`.
Measured counts in `ucc28c43_trans_unencrypted.lib`: **20** `E … VALUE=` lines and **9**
`G … VALUE=` lines (0 `POLY`, 0 `TABLE{}`). The complete list is in
`model_index.json → parsed.UCC28C43_pspice_only_constructs.lines`.

Of these, the ones inside the controller core `UCC28C43_STEADY` / `UCC28C43_START`
(line numbers 45–79 and 129–165) are decisive, because they implement the controller's
actual logic: brown-out/UVLO reference (`EBREF`), oscillator discharge switch (`GBDISCH`),
`VDD` clamp (`GB6`), current-limit comparator (`EB3`), reference buffer (`EB2`), and the
output-driver gate (`EOut`). The remaining lines belong to the EVM-flyback helper
subcircuits (`FLYBACK_UCC28C4x`, `XFMR`, `XFMRAUX`).

Consequently a working LTspice/ngspice run of this library requires **rewriting `E`/`G
VALUE` sources into B-sources** — that is an *edit of the vendor model*, and any result from
it must be labelled a **conversion**, never "original vendor-native replay".

### 3.5 Is PSpice / TINA installed?

| Simulator | Present? | Evidence |
|---|---|---|
| OrCAD/PSpice | **No** | no `Cadence`/`OrCAD`/`PSpice` directory under `C:\Program Files` or `C:\Program Files (x86)` |
| TINA-TI / DesignSoft TINA | **No** | no `TINA`/`DesignSoft` directory |
| LTspice | **Yes** | `LTspice.exe` 24.0.12.0 (sha256 `17f5efb9…`) |
| ngspice | **Yes** | `ngspice_con.exe`, **ngspice-47**, KLU, build 2026-08-11, sha256 `22d5cae2…` |

⇒ **Native UCC28C43 replay is impossible in this environment.** Any UCC28C43 result in
this repo is, by construction, either a conversion (edge-case: syntax patch) or absent.

### 3.6 Model limitations to carry downstream

1. Behavioural/functional model, not a transistor-level IC; switching thresholds are
   nominal, **not temperature or silicon-corner guaranteed**.
2. Calibrated to datasheet rev **D** (2007), not the current rev **I** (2024).
3. `SOSC` switch threshold comment (`VT=1.45 set to match 53k @ 3.3n/10k`) shows the
   oscillator was fitted to a **specific RT/CT point**; QS30 uses RT 15.4 k / CT 1 n
   (`S05_CIRCUIT_CANDIDATES.md`). Frequency fidelity at that point is **not** demonstrated
   by the model's own documentation and must be checked, not assumed.
4. The library also ships several unrelated EVM devices (FQB6N80, MTD1N60E, MBR140, MUR160,
   XFMR, MOC8101 …). Those are **not** QS30 parts and must never be treated as such.
5. TI licence/disclaimer text in the library header, verbatim: *"This product is designed as
   an aid for customers of Texas Instruments. No warranties, either expressed or implied,
   with respect to this third party software (if any) or with respect to its fitness for any
   particular purpose is claimed by Texas Instruments or the author. The software (if any)
   is provided solely on an 'as is' basis. The entire risk as to its quality and performance
   is with the customer."* The file contains **no explicit grant, no redistribution clause
   and no reverse-engineering clause** (measured: 0 occurrences of `licen*`, `redistribut*`,
   `resale`, `reverse engineer`). The terms are therefore *unstated beyond "as an aid for
   customers"*, which is weaker than ADI's explicit prohibition — but it is also **not** a
   redistribution permission. Recommended disposition: treat all TI model bytes as
   non-redistributable by default and keep them out of any public commit (BI-08).

---

## 4. HV power MOSFETs

| MPN | Vendor model | Encoding | Native-solver status | sha256 |
|---|---|---|---|---|
| **STP9NK50Z** | ST PSpice, `* Model Generated by STMicroelectronics`, `* Commercial Use or Resale Restricted` | plain ASCII text, `.SUBCKT` | readable by ngspice/LTspice **only** if the contained level-3 MOS syntax is accepted; several historical copies ran (see §7) | **`6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4`** |
| **SiHP8N50D** | Vishay `SiHP8N50D_PS_Rev_B.LIB` | plain ASCII, `S17-0112-Rev. B, 23-Jan-17`, ECN S17-0112 | same | **`70965ff71abeddd7ee57957baddd3f9d6a74738465632470e21a9d41e36959bd`** |
| **SiHP8N50D** (Coss / thermal variant) | `SiHP8N50D_PS_RC_Rev_B.lib` | plain ASCII, same Rev. B | same | **`1980c0ed2aef9bc5740acc9a9548a4e7e15422fb8e0daa9769c2c96f0fb3a40f`** |
| **SiHP8N50D** (annotated variant) | `SiHP8N50D_HS_Rev_B.TXT` (1 687 B) | plain ASCII; hash `523fb2ac…` is recorded in `safety_r1/governance/history_snapshot.json`, **not** re-verified by this worker — see `hash_manifest_raw.json` | same | recorded, not re-measured |
| SiHP8N50D package | `SiHP8N50D_model/original.zip`, 65 110 B, `https://www.vishay.com/docs/91533/sihp8n50d_ps_revb.zip` | zip | — | **`92375b97b278a5cfc2b2ea5aafc041d72e336c8bf82c6c6fc40f5bb5da957d79`** |

### 4.1 Vishay SiHP8N50D model limitations (quoted from the retained model guide, doc 91532, Rev. B)

- *"The subcircuit model is extracted and optimized over 25 °C to 150 °C temperature ranges
  under the pulsed 0 V to 15 V gate drive."*
- *"The saturated output impedance is best fit at the gate bias near the threshold voltage."*
- *"All model parameter values are optimized to provide a best fit to the measured electrical
  data and are not intended as an exact physical interpretation of the device."*
- *"This document is intended as a SPICE modeling guideline and does not constitute a
  commercial product datasheet… refer to the appropriate datasheet for guaranteed
  specification limits."*
- Documented model-vs-measured deltas worth noting: `trr` 260 ns simulated vs **308 ns**
  measured; `Qrr` **3.1 nC** simulated vs **1.8 nC** measured. The model is therefore
  pessimistic on Qrr and optimistic on trr at the documented point.
- Consequence for QS30: this is a **typical-part** model. It cannot bound part-to-part or
  corner behaviour, and its Coss/thermal companion files must be used deliberately.

### 4.2 ST STP9NK50Z model limitations
Third-party-generated (ST-branded) `.SUBCKT` using built-in MOS levels; header restricts
commercial use/resale. No published model-vs-measured table was retained, so **its accuracy
at 170 V switching is unquantified** (BI-06).

### 4.3 STP7N65M2 — **no vendor SPICE model obtained**
Both ST endpoints recorded on 2026-11-15 returned HTTP 404
(`https://www.st.com.cn/resource/en/spice_model/stp7n65m2.zip`,
`https://www.st.com.cn/resource/en/spice_model/stp7n65m2_spice.zip`;
`source.json` in `sources/sprint06c/STP7N65M2_model_url{1,2}/`). Only the datasheet
(897 037 B, `9d02d61e…`) is retained.

### 4.4 IPP60R360P7 — **no vendor SPICE model obtained**
Only the Infineon datasheet is retained (1 730 429 B, `a2aa2f49…`).
`sources/sprint06c/Infineon_product.html` is a **0-byte** file — it proves nothing.
Any Infineon claim about this part in this repo would be **unevidenced**.

---

## 5. Rectifier / diode

### 5.1 Vishay US1G — the S05 candidate
| Item | Value |
|---|---|
| Model file | `sources/sprint06b/Vishay_US1G/us1g.txt`, 510 B |
| sha256 | **`f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3`** |
| Distributor URL | `https://www.vishay.com/docs/88194/us1g.txt` |
| Header provenance | `* (c)1999 Thomatronik GmbH … Author: Arpad Buermen` — i.e. **a vendor-hosted third-party model file, not a Vishay-authored compact model** |
| Form | `.MODEL US1G D (N=2.79019 IS=2.71097E-006 RS=0.0145165 EG=1.11 XTI=3 CJO=3.71999E-011 VJ=3.63462 M=0.834381 FC=0.5 TT=1.23315E-007 BV=400 IBV=0.1 KF=0 AF=1)` |
| Datasheet | `sources/US1.pdf`, `https://www.vishay.com/docs/88768/us1_test_dcicons.pdf`, `b515f5339da631a3fc59493afa1bb3cc4fb6ec77d0b12b1a5fb613074be22dc5` (trr 50 ns/75 ns, VRRM to 1000 V, SMA) |

**Limitation (important):** it is a plain diode `D` model fitted for forward conduction plus
`TT = 123.3 ns`. It carries **no** reverse-recovery charge/shape beyond the single
long-lifetime `TT`, no `trr`/`Qrr` fit to the 88768 test conditions, and no thermal/magnetic
coupling. A 170 V, ~200 ns switching-diode loss/recovery estimate from this model is
**not** qualified. Also, `BV=400` with `IBV=0.1` will avalanche-clamp somewhere near 400 V —
any simulation whose node exceeds that is being limited by the model, not the part.

### 5.2 Diodes-Inc. "US1G" — **different manufacturer, do not mix**
`sources/sprint06b/Diodes_US1G/Diodes_US1G.txt`, sha256 `18a58e53…`, carries
`*SRC=US1G;DI_US1G;Diodes;Si; 400V 1.00A 50.0ns` and the Diodes "SM DATA" disclaimer
(*"AS IS … won't be error free"*). It is a **different vendor's** part with the same
base type number. `Vishay_US1G/source.json` explicitly scopes *"Vishay US1G only, not
Diodes US1G"*. Using the Diodes numbers as Vishay behaviour is an evidence error.

### 5.3 SS14 — third-party model, not a Vishay model
`QS30-1/.../sources/sprint06c/SS14/original.lib`, 510 B,
sha256 `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2`,
`(c)1999 Thomatronik GmbH`, source `https://www.vishay.com/docs/89656/ss14.txt`.
Again a **Vishay-hosted third-party** model; `BV=44` in the `legd` model means it is
a 40 V-class part and **must not** be placed on the 170 V HV node.

---

## 6. HV inductor MSS1260-154KLD — **no vendor SPICE model exists**

| Item | Value |
|---|---|
| Datasheet | `https://www.coilcraft.com/getmedia/febefb9b-60f9-4a2c-8525-9c396f34e363/mss1260.pdf`, 303 467 B |
| sha256 | **`78be0158e52b6834be22069ec39c756967553e80eb89e5fa268b2c05352d13bf`** (text extract `285fe8b9…`) |
| Row `MSS1260-154KL_` | `150 µH ±10 %`, `DCR typ 209 mΩ / max 216 mΩ`, `SRF 6.1 MHz`, `Isat(10 % drop) 1.58 A`, `Isat(20 %) 1.80 A`, `Isat(30 %) 1.98 A`, `Irms(20 °C rise) 1.20 A`, `Irms(40 °C rise) 1.66 A` |
| Ambient / part temp | `-40 °C to +85 °C` with 40 °C rise; max part temp `+125 °C` (cores saturate and DCR rises — the `L(I)` used in any loop model must be hot and biased, not the cold nominal) |

**Vendor SPICE/loss model: absent.** Coilcraft does not publish a SPICE model for MSS1260
in this repo, and no `.asc`/`.lib`/magnetic model file is registered for it. Any simulation
of the HV inductor is therefore a **GSI/ideal or hand-made behavioural inductor** (the
historical runs used an ideal `L` with series `R`). Core-loss, `L(I)` roll-off, winding
capacitance, and thermal rise are **not** modelled by any vendor artifact. This is a
standing qualification gap, not a defect of this inventory.

---

## 7. Model-integrity audit — what "vendor model" really ran in the past

188 library copies exist under `projects/QS30-9_24V/sim/**/<case>/` named
`vendor.lib` (62), `st.lib` (39), `diode.lib` (23), `driver.lib` (12),
`driver_compat.lib` (18), `original_vendor.lib` (18), `uc.lib` (16).
Audited in `sim_copy_audit.json` against the six registered originals, and diffed in
`sim_model_mutations.md`.

| Outcome | Count | Detail |
|---|---|---|
| **Byte-identical** to a registered original | **146** | `uc.lib` 16 + `vendor.lib` 35 = **UCC28C43 unencrypted** `ab3cd5bb…`; `st.lib` 24 + `original_vendor.lib` 18 = **STP9NK50Z** `6ad61988…`; `vendor.lib` 22 = **SiHP8N50D** `70965ff7…`; `st.lib` 8 = **SiHP8N50D** `70965ff7…`; `diode.lib` 23 = **Vishay US1G** `f8669a85…` |
| **Not identical** to any registered original | **42** | three distinct mutations, below |

1. **UCC27511 driver — 15-byte syntax repair, 30 copies.** `driver.lib` (12) and
   `driver_compat.lib` (18) all hash `bf3e1b7599f1c7cca0643312f5a65ed703dcd747e5cad1f744eebf72a51183ff`
   against the registered `UCC27511_TRANS.LIB` `8e17d92edd68786189ad99439f4db06b8726fbf911c1282a85027e998c36e9f6`.
   The single changed line (57) turns the unbalanced `…(5,52m)6,58m)(8,63m)…` into
   `…(5,52m)(6,58m)(8,63m)…`. This confirms the **TI-shipped UCC27511 library is
   syntactically broken** and had to be repaired before any simulator could parse it.
   Every UCC27511 driver result in this repo therefore rests on an **edited** library.
2. **UCC28C43 unencrypted — `GB6` transliteration, 5 copies.**
   `ace0948d814c42209c08263f456b15a4107c0823e549f66329916cb77a444342` in
   `s06b_input_filter_v1/nativeGB6_{2.5ns,5ns}/vendor.lib` and
   `s06b_native_abm_v1/{controller_nativeGB6,integrated_nativeGB6_2p5ns,integrated_nativeGB6_5ns}/vendor.lib`:
   two lines rewritten from `GB6 19 GND Value = { … }` to `BGB6 19 GND I = { … }`.
   A syntax conversion rather than a physics change — but still an edit, so the
   "nativeGB6"/"native_abm" case names are **misleading**.
3. **`s06c_st_compat_v1` / `s06c_st_precision_v1` — NOT a controller model, 7 copies.**
   `90907f750855…` (5 copies: `s06c_st_compat_v1/native_E123_{1,2}ns` and
   `s06c_st_precision_v1/native_E123_{0.5,1,2}ns`) and `166bff3bf7cd…` (2 copies:
   `s06c_st_compat_v1/native_POLY_{1,2}ns`) are ~11 kB *smaller* than the 13 956 B
   UCC28C43 library: the TI header is gone and the body is an **STMicroelectronics level-3
   POWER MOSFET model**. These are named `st.lib`, which here means the MOS — but they sit
   in a directory tree whose sibling waves use the same basename for the controller. Any
   number derived from them is **not** UCC28C43 controller evidence (BI-05).

Note the naming hazard that makes this audit necessary: the same file basename means
different things in different waves (`vendor.lib` is the UCC28C43 controller in
`s06_buffered_gate_v1` and the SiHP8N50D MOSFET in `s06c_gate_charge_v1`; `st.lib` is the
controller in `s06b_input_filter_v1` but the MOSFET in `s06c_st_compat_v1`).
**Hashes, not filenames, decide identity.**

**Rule derived and adopted here:** a result may be called "vendor-native" only if the
library actually consumed hashes to the registered original. Everything else is labelled a
conversion, and no conversion may be presented as an unmodified vendor replay.

---

## 8. What the LT3757A model *has* demonstrably done (quoted, not reproduced)

This worker ran no simulation. For completeness the following **uncommitted historical**
results are quoted only to show the model is executable, with their own caveats:

- `QS30-1/.../sim/s06c_lt3757_units_v3/` (uncommitted; `safety_r1/governance/git_before.txt`
  lists it as `??`): 4 cases `ST_AUX12{,_p6}_{2,1}ns`, all `rc:0`, `finite:true`,
  `end_s: 1.2e-4`, `frequency_Hz ≈ 100.74 kHz`, `peak_gate_current ≈ 0.38–0.40 A`,
  `VGS_max 11.898 / 12.497 V`, CS→VGS(3 V) ≈ **229.9–233.5 ns**. Its `controller.sub`
  hashes to `c0328424…` — the **same** registered LT3757A bytes.
  Its own log shows `Direct Newton iteration failed to find .op point … Gmin stepping
  succeeded`, `Heightened Def Con` on many steps, and a ST-model warning
  `Instance "m:q:os": Width narrower than recommended for a level 3 MOSFET`.
  Its own preregister scopes it to a **forced-CS, resistor-load device cell** with
  `VC`/`SS` commanded through 1 k test resistors — **it is not autonomous startup, not a
  boost, and not a 170 V workpoint**, and it declares `"24V_07": "NOT_PASSED"`.
- `QS30-1/.../sim/s06c_lt_initial_v1/` (uncommitted): all 4 cases `execution: FAIL`
  (two 20 s timeouts, two `parsed_error`).
- `QS30-1/.../sim/s06c_lt_smoke_v1/` contains only `appdata/` and `localappdata/`
  directories — **no result file**; it proves nothing.

**No run anywhere in either workspace replays the unmodified `LT3757A.asc` reference.**
The reference `.asc` is registered here (`867ea5d1…`) but has never been executed in the
evidence inspected. That replay belongs to the follow-on `lt3757a_reference` task.

---

## 9. Register of artifacts and hashes (authoritative machine copies)

| File | Contents |
|---|---|
| `hash_manifest_raw.json` | 70 records: every inventoried file with absolute `source_path`, `sha256`, `bytes`; plus `lt3757a_extracted` (archive, member, CRC32, mtime, round-trip proof) and 101 historical sim `vendor.lib`/`st.lib` hashes |
| `model_index.json` | per-model byte statistics (CRLF/LF/NUL/non-ASCII/encryption markers), public `.SUBCKT` pin lists, TINA container probe, PSpice-only construct counts + the 29 exact lines, and licence text extracts |
| `sim_copy_audit.json` | 188 historical sim-library copies vs registered originals |
| `sim_model_mutations.md` | unified diffs of every non-identical sim copy |
| `vendor_bytes/LT3757A.sub`, `.asy`, `.asc` | the three byte-exact ADI extracts |

Reproduce with:
`extract_and_hash.py` → `parse_models.py` → `audit_sim_copies.py`
(run with `D:/PROJECTS/dsharness/QS30-1/tools/review_venv/Scripts/python.exe`, the only
working interpreter found; the `python` on `PATH` is blocked in this sandbox).

---

## 10. Blocking issues (things this inventory does NOT prove)

- **BI-01** No simulator has been run by this worker; no waveform, log or metric is produced
  here. Model *qualification* is therefore INCONCLUSIVE.
- **BI-02** LT3757A's model body is binary/encoded; its internal equations are unauditable
  and it is usable **only** in LTspice 24.0.12.0.
- **BI-03** UCC28C43 cannot be replayed unmodified here: no PSpice, no TINA, CDN-encrypted
  for LTspice, and the "unencrypted" copy needs 29 PSpice-only `E/G VALUE` transliterations.
  **LT3757A and UCC28C43 results are not comparable at equal fidelity.**
- **BI-04** The UCC28C43 model was validated against **datasheet rev D (2007)**; the retained
  datasheet is **rev I (2024)**. No change-control evidence that the model still matches.
- **BI-05** `s06c_st_compat_v1/native_{E123,POLY}_{1,2}ns/st.lib` and
  `s06c_st_precision_v1/native_E123_{0.5,1,2}ns/st.lib` (7 copies, hashes `90907f75…` /
  `166bff3b…`) hold an **ST level-3 MOSFET model, not the UCC28C43 controller**. In those
  waves the file is named for the MOS, so the content is plausible; the hazard is that the
  same basename carries the controller elsewhere. Any downstream reuse must be keyed on the
  hash, and the owner should rename these slots before the next wave.
- **BI-06** No vendor SPICE model exists locally for **STP7N65M2** (both ST URLs 404),
  **IPP60R360P7** (datasheet only, 0-byte product HTML), or **MSS1260-154KLD** (datasheet
  only). Those three roles have *no* vendor-model basis at all.
- **BI-07** The US1G model is a vendor-hosted **third-party** diode model with a single `TT`
  and no reverse-recovery/`Qrr` fit; the MSS1260 has no core-loss model. HV diode/inductor
  loss and recovery are unqualified.
- **BI-08** The ADI licence (**20230822-LTS-CTSLA**) explicitly forbids reverse engineering
  and states the Licensed Software *"may not distribute the PC Software under any
  circumstances"*, so the registered `vendor_bytes/LT3757A.*` must stay internal. The TI
  model headers grant no redistribution right either (they are silent). Treat both as
  non-redistributable; do not commit them to a public repository or publish them.
- **BI-09** The TI product page `https://www.ti.com/product/UCC28C43` could not be re-fetched
  by this worker (`web_search` returned no TI page content; only public search hits).
  The PSpice/TINA availability claim therefore rests on the **retained zip bytes and the
  TI document numbers slum033/slum178**, not on a live product-page check.
- **BI-10** No page-1 byte comparison against a *fresh* ADI download was performed; the
  `lib.zip`/`examples.zip` SHA-256 values are taken from the local toolchain and reconciled
  with `baseline_audit` (`dd0028bb…`, `319ac0e9…` agree).
- **BI-11** The two LT3757A `sim` runs that did produce numbers are **uncommitted** and are
  device cells (forced CS, resistor load), not autonomous-startup or 170 V results.
- **BI-12** This inventory does **not** change any safety_r1 HOLD, the manufacturing HOLD, or
  any electrical acceptance threshold. 5.71642 W → ≥5.88985 W HV budget and all S06C/D/E/F
  caveats remain exactly as they were.

---

## 11. URL register (official sources)

- ADI LTspice distribution: <https://ltspice.analog.com/download/latest/LTspice64.msi>
- ADI LT3757/LT3757A datasheet: <https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf>
- TI UCC28C43 product page (cited by runner; not re-fetched, BI-09): <https://www.ti.com/product/UCC28C43>
- TI UCC28C43 datasheet (SLUS458I): <https://www.ti.com/lit/ds/symlink/ucc28c43.pdf>
- TI UCC28C43 PSpice model: <https://www.ti.com/lit/zip/slum033>
- TI UCC28C43 TINA model: <https://www.ti.com/lit/zip/slum178>
- Vishay SiHP8N50D model zip (doc 91533): <https://www.vishay.com/docs/91533/sihp8n50d_ps_revb.zip>
- Vishay SiHP8N50D model guide (doc 91532): <https://www.vishay.com/docs/91532/sihp8n50d_ps_revb.pdf>
- Vishay SiHP8N50D datasheet (doc 91488): <https://www.vishay.com/docs/91488/sihp8n50d.pdf>
- Vishay US1 family datasheet (doc 88768): <https://www.vishay.com/docs/88768/us1_test_dcicons.pdf>
- Vishay US1G SPICE model text (doc 88194): <https://www.vishay.com/docs/88194/us1g.txt>
- Coilcraft MSS1260 datasheet: <https://www.coilcraft.com/getmedia/febefb9b-60f9-4a2c-8525-9c396f34e363/mss1260.pdf>
- ST STP7N65M2 datasheet: <https://www.st.com.cn/resource/en/datasheet/stp7n65m2.pdf>
- Infineon IPP60R360P7 datasheet: <https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipp60r360p7-datasheet-en.pdf>
