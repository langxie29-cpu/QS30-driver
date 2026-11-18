from pathlib import Path
import json
import os
import sys
import time
from urllib import request, error
root = Path(__file__).resolve().parent
prompts = {
 1: [
 'Assess an abstract autonomous three-digit static glow tube module with own 12V source, 170V boost, 32-channel sink (30 used), MCU and 2-wire RS-485. Assess independent/shared inputs, display coherence and safe mechanical boundaries.',
 'Independently derive ideal DCM peak current, duty and boundary power for L=150uH, 100kHz, output 170V, input 10.8/12/13.2V and output 1.15/1.53/2/2.5W. Address loss sensitivity and cold start.',
 'Compare UCC28C43 and LT3757A current-mode boost controllers at 100kHz for 10.8–13.2V to 170V 2W and a 24V control case. Identify which specs must be confirmed and possible DCM lightweight topologies.',
 'Adversarial review of three independent 170V sources versus a centralized nine digit supply. Address unpowered RS485, common ground, EMC, peak startup load, connector safety, module loss and fair cost comparisons.'
 ],
 2: ['Audit a 150uH 100kHz LT3757A candidate with 0.30 ohm shunt, typical 100mV sense limit and 0.70 efficiency sensitivity, 12V to 170V 2W. Check peak-current headroom and cold start into CCM.',
 'Audit an abstract safety chain using TPS26600 latch mode, separate hardware OVP latch, two bleeders, 4.7uF 250V output cap and small downstream input ceramic. Look for passive boost paths, energy sources and loss of bias.'],
 3: ['Adversarially audit model scope for a vendor LT3757A macro and vendor FET/diode, behavioral gate driver, linear L and resistive load. Assess timestep, startup, junction temperature, and input-switch abstraction.'],
 4: ['Audit low voltage RS485 host-controlled same-firmware modules using static local addresses, staged 3-digit slices, broadcast commit, CRC, sequence checks and timeout blanking. Identify stale/hybrid displays and pin/sequencing errors.'],
 5: ['Review independent static 3-digit modules with 12V local LT3757A boost, 12V gate/display auxiliary supply, HV5622PG and RS485. Typical models stalled near 165V at 33ms; diagnostic isolation confirmed ~11.14V passive feedthrough; ideal OVP picked up; KiCad 0 ERC with tube socket geometry open; native host tests pass. Compare equal-safety centralized and 24V modular costs. Challenge required protection, auxiliary startup and bias-loss, independent behavior and coherent display, alternative controllers/inductors/diodes, and exact first-board exits. Identify what evidence can and cannot be claimed.']
}
n = int(sys.argv[1])
for index, prompt in enumerate(prompts[n], 1):
    path = root / 'evidence' / f'flash_r{n}_{index}.json'
    if path.exists():
        continue
    start = time.monotonic()
    model = 'deepseek-flash'
    item = dict(round=n, session=index, request_model=model, prompt=prompt, charge='UNKNOWN')
    key = os.getenv('DEEPSEEK_API_KEY')
    auth = Path('D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml')
    if not key and auth.is_file():
        key = next((line.split(':',1)[1].strip().strip('"\x27') for line in auth.read_text(encoding='utf-8').splitlines() if line.startswith('DEEPSEEK_API_KEY:')), None)
    if not key:
        item.update(status='NO_AUTH', called=False)
    else:
        body = dict(model=model, stream=False, max_tokens=1200,
                    thinking={'type':'disabled'}, messages=[dict(role='system', content='Independent review of supplied public engineering facts. No tools. State all uncertainties.'), dict(role='user',content=prompt)])
        req = request.Request('https://api.deepseek.com/chat/completions', data=json.dumps(body).encode(),
                              headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        item['called'] = True
        try:
            with request.urlopen(req, timeout=40) as response:
                result = json.load(response)
            item.update(status='COMPLETED', provider_model=result['model'], usage=result.get('usage'),
                        finish=result['choices'][0]['finish_reason'], review=result['choices'][0]['message']['content'])
        except (error.URLError, TimeoutError, ValueError, KeyError) as exc:
            item.update(status='FAILED', error=type(exc).__name__, http_code=getattr(exc, 'code', None))
    item['seconds'] = round(time.monotonic()-start, 2)
    with path.open('x', encoding='utf-8') as output:
        json.dump(item, output, indent=2, ensure_ascii=False)
    print(n, index, item['status'], item.get('http_code'), item.get('usage'), flush=True)
