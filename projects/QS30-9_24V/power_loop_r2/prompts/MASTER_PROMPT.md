# QS30-9 power-loop multientity orchestration — governing prompt

This is a *software-only*, evidence-gated architecture for the existing private QS30-driver repository.
Primary objective is a repeatable *real-controller* SPICE waveform demonstrating 24V->170V,
0V autonomous startup and subsequent regulated steady state. This is NOT a fabrication
authorization. Do not silently repurpose safety_r1 numerical logic tests as proof of a
nonlinear HV power stage.

Use DeepSeek Harness / deepseek-flash for high-volume execution (source inventory,
model checks, reference replay, native simulations, wave analysis, regression). Use
Codex CLI / GPT-6.1 Sol for *every* material decision (controller, model acceptance,
experiment prioritization, topology tradeoffs, fault interpretation, stage progression).

Decision loop:
  0. read committed baseline and safety R1, register HOLD and acceptance;
  1. fan out Flash tasks within explicit catalog, with one isolated output folder each;
  2. deterministic validator: check task results, evidence existence/hash/path,
     logs, simulator input, metrics and provenance. Reject fake/missing evidence;
  3. separate Codex read-only JSON decision: CONTINUE with allowed task IDs,
     or HOLD/STOP. Never let model text become executable shell commands;
  4. repeat bounded rounds and save all raw results, failures, review reasoning,
     and eventual "cannot prove" conclusions. No silent threshold changes.
Important: the worker pass is a claim, NOT a qualified electrical pass.
Do not launch another expensive high-effort model to summarize a trivial deterministic PASS.
No key in repository. No automatic Git push, merge, manufacturing approval or physical HV.

Each stage must be justified: S0 model provenance and vendor native replay,
S1 device/driver and true peak-current cell,
S2 output capacitor from 0V and no forced PWM or 170V initialization,
S3 feedback 170V regulation/corners with saved waveforms and independent critique.
Failure is a valid deliverable if accompanied by precise reproducible traces.

Special risks: eFuse RTN leakage/backfeed, 24V passive L-D recharge, MOS D-S short,
real hot L(I,T) and core loss, model opacity and nonlinear solver behavior,
unproven original S06F LT3757A/UCC integration, revised bleeder load and
OVP peak energy. Keep 24V-07/08/09/10 and manufacture HOLD until evidence is
confirmed by subsequent circuit-level and physical reviews.
