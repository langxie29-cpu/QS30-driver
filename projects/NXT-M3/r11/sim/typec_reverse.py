"""Reproduce the isolated Type-C input fault proxies."""
from pathlib import Path

import run

HERE = Path(__file__).resolve().parent
run.CASE_DIR = HERE.parent/"evidence/typec/runs"
if __name__=="__main__":
    cases = ("reverse_u1_fault","typec_reverse.cir","U1 leakage and failed low-ohmic bypass bounds"), (
        "front_ovlo_5p5","typec_front_ovlo.cir","TPS259474L OVLO thresholds with ideal hysteresis")
    for case, file, model in cases:
        result = run.run(case,(HERE/file).read_text(),model)
        if result["exit"] != 0:
            raise SystemExit(1)
