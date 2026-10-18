# REV.A9.1 evidence execution notes

2026-10-18, Asia/Shanghai. Git baseline b6a9082; initial worktree clean.
Created branch rev-a9-1-electrical-freeze, without reset/clean/force push.

- `before_a9_1`: initial append-only capture completed DISPLAY sexpr/XML/ERC report+JSON/DRC report+JSON, then Python failed on `fp.properties` (dict, not a list of key/value objects). The traceback was `AttributeError: 'str' object has no attribute 'key'`, runner rc=1. These six outputs are retained. That early implementation wrote commands at end, so no commands.log was created for the failed attempt; do not infer it was a complete two-board audit.
- `before_a9_1_complete`: after correcting kiutils dict access and writing commands after every invocation, both boards captured; runner rc=1 because actual networks failed reconciliation. Twelve native invocations logged, export rc=0, ERC/DRC rc=5 with violation flag.
- `after_a9_1`: first revised electrical source; two-board connected-net reconciliation PASS; raw outputs retained. No schematic-parity flag in this intermediate run.
- `after_a9_1_final`: stable schematic-to-board paths added, full DRC schematic parity enabled; raw outputs retained.
- `rev_a9_1_20261018`: final source revision, full NC inventory also checked; safe `kicad_check.py` entry point, native exports/ERC/DRC/parity all actually executed. Input SHA256 and exact argv/return codes in results.json/commands.log. `validate_freeze9.py` rc=0, 12/12 structural checks. `report_freeze9.py` rc=0. This is the authoritative run.

The historical root logs, EDA_CHECK_RESULTS.md, GENERATED_STATUS.md and legacy FAIL/HOLD reports are retained. Additional byte-for-byte Git-b6a9082 snapshots and SHA256 are in b6a9082_evidence/. `kicad/eda_check_results.json` is the updated derived index; raw run/results.json remains immutable.

No SPICE simulation, Gerber export, drill export, order, push, or hardware experiment was performed. New run folders reject existing names; every subsequent run must use a new name. Command logs are explicitly added to Git despite the existing `*.log` ignore rule.
