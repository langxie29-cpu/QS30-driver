# QS30-9: DeepSeek Flash + Codex 6.1 Sol power-loop orchestrator R1

**2026-11-17 state: two real DeepSeek Flash waves/six worker sessions executed, current OpenAI gpt-6.1-sol review, zero child Codex calls. Actual LT3757A/zero-COUT nominal simulation completed60ms and reached170V vicinity. Candidate ELECTRICAL_FAIL: SENSE0.524V vs0.3V absolute rating; late-window2.431Vpp. 24V-07/08 qualification and manufacturing remain HOLD.**

Read the [engineering report](ENGINEERING_REPORT.md), [model matrix](MODEL_MATRIX.md) and [controller decision](CONTROLLER_REVIEW.md) first. New exact raw archives and the original failed experiments are indexed under `evidence/`. The earlier implementation notes below describe the starting infrastructure; claims of no local access/no real runs are historical and superseded by this report.

Current local entry points (private Harness configuration and credentials stay in ignored `.local/`):

    python projects/QS30-9_24V/power_loop_r1/local_live.py --doctor
    python -m unittest discover -s projects/QS30-9_24V/power_loop_r1 -p test_*.py -v

The completed run is `runs/20261117T051440Z`; its last decision is HOLD and it cannot schedule a third wave. Do not restart it as a new billable run just to reproduce measurements. Use the archived netlists/commands/raw hashes and analysis scripts. See [reproduction instructions](REPRODUCE.md). Native model/executable acquisition remains separate from evidence delivery.

Purpose: coordinate cheap bulk DeepSeek Harness sessions and expensive Codex engineering decisions to qualify vendor models and establish a real-controller 24V -> 170V Boost simulation from 0V COUT.

## Design

- DeepSeek Harness headless profile + deepseek-flash: document checks, source/model registry, vendor reference replay, cell fixtures and bulk simulation evidence.
- Codex CLI + gpt-6.1-sol (OpenAI provider): decisions after each wave, controller/architecture selection and independent negative review.
- Python stdlib: bounded job catalog, minimum artifact checks, separate output folders, deterministic dependency control, decision schema and HOLD enforcement.
- GitHub Actions: OFFLINE tests of the coordinator only. It does not run the real models, Windows LTspice, vendor simulators or high voltage.

The original vendor models and failing waveforms are never modified by the orchestration code. Worker PASS is a file-audited CLAIM, not electrical qualification. Hardware remains forbidden.

## Windows PowerShell: bootstrap in local cloned QS30-driver root

1. Verify the commands: dsh --help, dsh --profile headless --dump-config, codex --version, codex login status.
2. In the local DSH headless profile ensure the effective backend model is named deepseek-flash; the orchestrator rejects an undetectable model setting. A profile string is a weak preflight, NOT a guarantee about actual billing. Keep API keys in the provider configuration, never in the repo.
3. Keep the user's existing defaults. Current-session external review prevents recursion. Optional standalone DECISION calls explicitly choose OpenAI provider and --model gpt-6.1-sol; they no longer require the nonexistent gpt profile. The legacy decision_profile config field is not used.
4. Install/verify the intended Windows LTspice and NGspice, and ensure vendor SPICE model redistribution/licensing rules are followed. Do not run unreviewed download scripts.

From repository root:

    python projects/QS30-9_24V/power_loop_r1/orchestrate.py
    python -m unittest discover -s projects/QS30-9_24V/power_loop_r1 -p test_*.py -v
    python projects/QS30-9_24V/power_loop_r1/orchestrate.py --doctor

First command is the no-cost DRY RUN. Tests and doctor make no model requests. Doctor inspects local CLIs/profile only.

## Explicit paid live activation

After local sandbox and model/profile inspection:

    python projects/QS30-9_24V/power_loop_r1/orchestrate.py --live --accept-model-costs --rounds 2

Live execution performs model requests. Current config permits up to7 Flash task sessions and2 waves (each with timeouts), but **does not limit actual API token billing**. Inside Codex, `--external-decisions` is mandatory and uses the current principal rather than launching Codex again. The final decision selects only fixed catalog IDs. Missing proof results in INCONCLUSIVE/HOLD. This initial integration already used its two-wave limit.

Each run writes ignored LOCAL output into power_loop_r1/runs/<UTC>/ with prompts, worker output, result files, hashes, stderr, Codex decision input/output and a summary. Review/redact before any deliberate Git commit. No automatic commits/pushes or purchases.

**Security:** The Python coordinator does not enable physical hardware. However, the local DeepSeek Harness plugin may have broader shell/network access than the coordinator can enforce. Use a dedicated OS user/sandbox and separate clone, restrict its filesystem/network/instruments, avoid secrets, and review its permissions before a live run. This is not a secure remote-execution boundary.

## Research gates

- **0:** Existing baseline (including safety_r1), exact vendor model registry, reconcile power/bleeder budget and acceptance.
- **1:** Native reference runs (LT3757A and UCC28C43) and exact device-cell qualification; retain model/solver failures.
- **2:** Codex-approved candidate, valid hardware current limit, real-model starting at zero output.
- **3:** 170V closed-loop waveform, load and input corners, independent challenge. Store netlists, logs, raw waves, exact MPN/model hashes and quantitative metrics.

Task manifest uses a list of authorized IDs. A model decision cannot override dependency gates or retroactively rewrite failed evidence. Missing or untrusted model tools result in HOLD, not fabricated PASS.

## Files

- **prompts/MASTER_PROMPT.md:** governing instructions for future Codex full engineering sprint.
- **prompts/FLASH_WORKER.md:** task execution contract for bulk workers.
- **prompts/CODEX_DECISION.md:** high-effort selective decision reviewer.
- **tasks.json / config.json / decision.schema.json:** fixed task queue, staged policy and decision output schema.
- **orchestrate.py:** local bounded execution engine and evidence auditor.
- **test_orchestrate.py:** deterministic provider-free contract tests.

## Historical infrastructure limitations (superseded where noted above)

1. The current conversation cannot access the user's live Windows desktop/installed Harness, local simulator or model credentials; there have been **no real DSH or Codex paid calls from this ChatGPT session**. This implementation is committed and CI-tested, not locally integrated with your machine.
2. A file-existence audit is not a numerical SPICE/electrical truth oracle. It can detect missing files but cannot certify waveforms. Independent deterministic waveform analyzers for startup/170V/overshoot/current are the next code milestone.
3. Vendor original reference decks are not bundled or executed here. Some newer S06D–F materials referenced by earlier reports were not present in the committed branch at initial check; report missing baselines instead of inventing test runs.
4. Exact local DSH headless tool permissions, native Windows CLI behavior, profile configuration and model availability require an initial on-PC smoke test.
5. No restoration of manufacturing release. 24V-07 NOT_PASSED, 08 NOT_ENTERED, 09/10 partial, unchanged historical electrical HOLD.
