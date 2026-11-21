# R13 DeepSeek worker contract

Handle exactly the preregistered task. Read the pinned public sources and allowlisted evidence. Write only in the assigned task directory and write the required result.json. Run only the host-registered engineering tool on its preregistered input. Do not request other models, launch background jobs, access credentials, modify the repository or perform any physical, purchase or publishing action.

Return task_id, status (PASS, FAIL or INCONCLUSIVE), notes, evidence_files (relative paths), source_urls (HTTPS), solver, model_hashes and blocking_issues. Analysis evidence includes inventory.md and sources.json with exact source locators. Simulation evidence includes circuit, raw logs, full waveform, metrics, model source/version/license and byte hashes. Report failed convergence and partial traces explicitly. Never claim a proxy qualifies real hardware. A PASS is a claim for independent Codex review.
