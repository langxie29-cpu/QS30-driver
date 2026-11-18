"""Send one narrowly scoped review per R7 round and retain the provider receipt."""
import argparse
import json
import os
from pathlib import Path
from time import monotonic
from urllib.error import URLError
from urllib.request import Request, urlopen

PROMPTS = {
    1: "Review a public LT3757A 12 V to 170 V, 150 uH 100 kHz power cell. Native transient at 37.47 ms had 170.42 V, but timed out before its tail. Logs show repeated LTspice Def Con near switching instants. Distinguish partial windows, waveform I/O and numerical model pathologies. Assess how to use 1 uF after a 0.6 A eFuse against 0.786 A inductor pulses. Give falsifiable diagnostics.",
    2: "Review a 170 V protected boost with TPS26600 shutoff, 0.6 A nominal limit, TPS3700 184 V OVP, D latch, UCC27511 gate inhibit, 5.5 uF maximum output and two independent 498 kohm bleeders. Compare single-point faults, passive boost diode feed, brownout, fresh ARM and residual-voltage lockout. Identify independent acceptance events.",
    3: "Assess source and footprint risks for replacing grounded-return TMR 1-1212 with TPS552872RYQR, MSS1583-154KED with MSS1260-154KLD, STPSC4H065D with STPSC2H065B-TR or STTH1R06U, and HV5622PG-G with HV5622PJ-G. Identify added BOM, conditional losses, and which ratings matter.",
    4: "Compare LT3757A with external 12 V gate drive, TPS40210 with external or direct drive, and UCC28C43 on a three-digit 170 V / 2 W autonomous module. 10.8–13.2 V or 21.6–26.4 V inputs. Offer pitfalls for minimum line startup, slope/ramp/limits, compensation, 12 V bias and independent fault chain. Do not infer equivalence from incomplete cases.",
    5: "Audit a no-build 3-digit single-board R7 candidate. Keep 12 V interim reference, hardware OVP and step-up fault isolation, native KiCad ERC, exact BOM but unverified prices and passive replacements. Give concrete release-blocking evidence requirements, especially input current, output energy, shared low-voltage bus and fault reset.",
}


def main(round_no):
    dest = Path(__file__).resolve().parent / "evidence" / f"flash_r{round_no}.json"
    if dest.exists():
        raise SystemExit("Round already has a receipt")
    secret = os.getenv("DEEPSEEK_API_KEY")
    path = Path("D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml")
    if not secret and path.is_file():
        secret = next((line.split(":", 1)[1].strip().strip("\"'") for line in
                       path.read_text(encoding="utf-8").splitlines() if line.startswith("DEEPSEEK_API_KEY:")), None)
    model = "deepseek-flash"
    prompt = PROMPTS[round_no]
    receipt = dict(round=round_no, requested_model=model, prompt=prompt, called=bool(secret), charge="UNKNOWN")
    started = monotonic()
    if secret:
        body = dict(model=model, max_tokens=850, stream=False, thinking={"type":"disabled"},
                    messages=[dict(role="system", content="Independently review the supplied public facts. Mark uncertainties."),
                              dict(role="user", content=prompt)])
        request = Request("https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(),
                          headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=40) as response:
                data = json.load(response)
            choice = data["choices"][0]
            receipt.update(status="COMPLETED", provider_model=data["model"], usage=data.get("usage"),
                           finish=choice["finish_reason"], review=choice["message"]["content"])
        except (URLError, TimeoutError, KeyError, ValueError) as error:
            receipt.update(status="FAILED", error=type(error).__name__, http=getattr(error, "code", None))
    else:
        receipt["status"] = "NO_AUTH"
    receipt["seconds"] = round(monotonic()-started, 3)
    with dest.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
    print(round_no, receipt["status"], receipt.get("usage"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("round", type=int, choices=PROMPTS)
    main(parser.parse_args().round)
