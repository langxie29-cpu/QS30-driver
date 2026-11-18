"""Two bounded review calls. Prompts contain public specs and abstract calculations."""
import json
from pathlib import Path
import sys
import time
from urllib import request, error

HERE = Path(__file__).resolve().parent
AUTH_FILE = Path('D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml')
PROMPTS = {
    '1': (
        'Review independently three unrelated engineering scenarios using the supplied facts only. '
        'A: a CAD converter cannot execute under host application control and a separate CAD editor '
        'has an activation gate; identify what can be verified on source and what constitutes a pass. '
        'B: retail MOQ 1000, reported total stock 10000, validStockNumber 10, price and stock in '
        'server-rendered data; explain why an EVT quantity 5 basket is unresolved and how to price gates. '
        'C: hot-swap min current limit 48.5 mV, max breaker 130 mV, shunt 1%, normal peak 1.649202 A, '
        'cold indicative ceiling 3.1 A, hot unknown. Derive inequalities and architecture alternatives. '
        'Identify timing and downstream capacitor caveats.'),
    '2': (
        'Adversarially review hypothetical engineering decisions A/B/C. A: an independent KiCad netlist '
        'rerun agrees with a frozen baseline and vendor CAD has no target netlist. May a pass be claimed? '
        'What equivalence fields and bypass hazards should be checked? B: a public PCB form fails to return '
        'a price and SMT marketing gives 50 CNY setup and 0.01 CNY per point. Distinguish scenario '
        'estimates, missing fees, and current order quotes. C: reject a single-shunt direct swap, '
        'reduce guaranteed startup peak, research independent fast branch sensing and latched cutoff. '
        'Challenge using a 25 C linear FET SOA curve and constant-L discharge estimates as protection proof. '
        'Inputs: 135 uH sensitivity, 26.4 V, 1.649202 A initial, 2.5 A hypothetical ceiling.'),
}


def main(round_no):
    prompt = PROMPTS[round_no]
    receipt_path = HERE / 'evidence' / f'flash_round_{round_no}.json'
    if receipt_path.exists():
        raise SystemExit('Review already attempted; preserve the receipt and spending limit.')
    key = next(line.split(':',1)[1].strip().strip('\"\'') for line in
               AUTH_FILE.read_text(encoding='utf-8').splitlines()
               if line.startswith('DEEPSEEK_API_KEY:'))
    body = dict(model='deepseek-flash', stream=False, max_tokens=1500,
                thinking={'type':'disabled'},
                messages=[dict(role='system',content='Review pre-supplied facts only. No tools or new sources. Preserve all unresolved engineering gates.'),
                          dict(role='user',content=prompt)])
    req = request.Request('https://api.deepseek.com/chat/completions',
                          data=json.dumps(body).encode(),
                          headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    began = time.monotonic()
    receipt = dict(round=round_no, request_model=body['model'], prompt=prompt, max_output_tokens=1500)
    try:
        with request.urlopen(req, timeout=50) as resp:
            payload = json.load(resp)
        receipt.update(status='COMPLETED', provider_model=payload['model'], usage=payload.get('usage'),
                       review=payload['choices'][0]['message']['content'])
    except (error.URLError, TimeoutError, ValueError, KeyError) as exc:
        receipt.update(status='FAILED', error=type(exc).__name__, http_code=getattr(exc, 'code', None))
    receipt['seconds'] = round(time.monotonic() - began, 2)
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n', encoding='utf-8')
    print(receipt['status'], receipt.get('usage',{}))


if __name__ == '__main__':
    main(sys.argv[1])
