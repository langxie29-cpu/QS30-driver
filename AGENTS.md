# QS30-driver · Agent Rules

This repository contains a historical QS30-6 six-tube engineering baseline. Read `README.md`, `docs/HANDOVER.md`, `HOLD_REGISTER.md`, `open_issues.md`, netlist, BOM, and verification reports before proposing an edit.

## Specific safeguards
1. Existing engineering status is HOLD / **no board order or production release**. PASS of structural consistency checks is not proof of high-voltage safety, board-level ERC/DRC, electrical simulations, or manufacturing readiness.
2. Keep the six-tube QS30-6 baseline distinct from the newer proposed nine-tube architecture. Do not silently transform six-tube netlists/BOM into nine-tube facts.
3. High-voltage safety, output off-state, power-down, overcurrent and reset are explicit release gates. Any bypass, undocumented HV operation, or production release requires verified evidence and explicit authorization.
4. Protect original files and test data. Report evidence, unsatisfied checks, and unresolved design issues instead of suppressing errors.
5. Never assert ordered or received parts from a planned BOM; physical inventory belongs in Σ.

## Cross-repository protocol
- The user owns design decisions. Do not place orders, alter production hardware, deploy, release, flash, or rewrite other repositories without explicit task authorization.
- Before editing, inspect this repository's README, current documents, commit state, and existing design evidence. Use small traceable changes. No force pushes, silent mass renames, or destructive edits.
- Distinguish [CONFIRMED] (source or reproduced test), [REPORTED] (user statement), [CANDIDATE], and [UNVERIFIED]. Never invent device specifications, costs, test outcomes, or procurement status.
- The authoritative register of actual lab assets, physical stock, transactions, and maintenance is the private Obsidian Vault repo `langxie29-cpu/obsidiandatabase` under `Σ/`. Engineering design files, code and test evidence remain authoritative here. Project repo updates may link to Vault records, but should not create conflicting financial ledgers.
- The laboratory's official visual name is **Σ** (U+03A3). Preserve historical labels and prior commits; do not introduce XLab or spell out a replacement English brand.
- Do not copy receipts, identifying personal details, tokens, private addresses, or raw financial statements between repositories; especially never write private information into public repositories.
- User descriptions do not imply hardware tests. Record what was observed and what remains unverified. The agent must state file paths actually changed and checks actually run.
- Never generate images without the user's explicit instruction “生成图片”.
