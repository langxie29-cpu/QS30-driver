"""R3 API-only Harness workflow; remote textual workers receive no local tools."""
from r4lib import *
import urllib.request,urllib.error,time,argparse,concurrent.futures
def run(task,prompt):
 root=HERE/'drafts'/task;root.mkdir(parents=True,exist_ok=False)
 if len(list((HERE/'drafts').glob('*/preregister.json')))>=6:raise RuntimeError('Six Flash session ceiling')
 (root/'prompt.txt').write_text(prompt,encoding='utf8')
 dump(root/'preregister.json',dict(utc=utc(),model='deepseek-flash',max_output_tokens=4500,max_runtime_s=180,tools=[],filesystem_access=False,generated_code_execution=False,max_sessions_R4=6,rounds_R4=2,estimated_input_tokens=len(prompt)//3,billed_cost='UNKNOWN'))
 creds=Path('D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml').read_text(encoding='utf8')
 key=next(x for x in creds.splitlines()if x.startswith('DEEPSEEK_API_KEY:')).split(':',1)[1].strip().strip('"\'')
 body=dict(model='deepseek-flash',messages=[dict(role='system',content='Bounded engineering research/review worker. No browsing, shell, filesystem, tools or execution. Do not claim you obtained new sources. Review supplied facts; mark unsupported recollections and values UNKNOWN. Never release safety/manufacturing HOLD. English concise engineering output. No more than 3500 words.'),dict(role='user',content=prompt)],max_tokens=4500,stream=False,thinking={'type':'disabled'})
 request=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(request,timeout=180)as response:data=json.loads(response.read())
  dump(root/'response.json',data);(root/'draft.md').write_text(data['choices'][0]['message']['content'],encoding='utf8')
  result=dict(status='COMPLETED_UNREVIEWED',usage=data.get('usage'),provider_model=data.get('model'),elapsed_s=time.monotonic()-start,finish_reason=data['choices'][0].get('finish_reason'))
 except Exception as ex:result=dict(status='EXECUTION_FAIL',elapsed_s=time.monotonic()-start,error=type(ex).__name__+': '+str(ex))
 dump(root/'execution.json',result);return dict(task=task,**result)
def main(roundno):
 files=sorted((HERE/'prompts'/f'round_{roundno}').glob('*.txt'))
 if len(files)!=3:raise RuntimeError('Exactly three bounded workers per round')
 if len(list((HERE/'drafts').glob('*/preregister.json')))+3>6:raise RuntimeError('Budget exhausted')
 with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
  futures=[pool.submit(run,p.stem,p.read_text(encoding='utf8'))for p in files]
  for f in concurrent.futures.as_completed(futures):print(json.dumps(f.result()),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('round',choices=['1','2']);main(a.parse_args().round)
