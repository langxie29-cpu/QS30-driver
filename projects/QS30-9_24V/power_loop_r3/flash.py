"""No agent runtime. API-only textual worker. No tools/shell/filesystem given to model."""
from r3lib import *
import urllib.request,urllib.error,time,re,argparse
def run(task,prompt):
 root=HERE/'drafts'/task;root.mkdir(parents=True,exist_ok=False)
 (root/'prompt.txt').write_text(prompt,encoding='utf8')
 dump(root/'preregister.json',dict(utc=utc(),model='deepseek-flash',max_output_tokens=7000,max_runtime_s=180,tools=[],filesystem_access=False,generated_code_execution=False,estimated_input_tokens=len(prompt)//3,estimated_cost_USD=None,cost_note='Paid API authorized by user; actual billed amount not supplied. Record provider usage independently.'))
 creds=Path('D:/PROJECTS/DeepSeekHarness/data/.credentials.yaml').read_text(encoding='utf8')
 line=next(x for x in creds.splitlines() if x.startswith('DEEPSEEK_API_KEY:'))
 key=line.split(':',1)[1].strip().strip('"\'')
 body=dict(model='deepseek-flash',messages=[dict(role='system',content='You are a bounded engineering drafting/review worker. No tools are available. Do not claim to have browsed or simulated. Use provided evidence and explicit assumptions. Never grant manufacturing approval. Answer in concise technical English. Distinguish guaranteed values from typical.'),dict(role='user',content=prompt)],max_tokens=7000,stream=False,thinking={'type':'disabled'})
 req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=180) as r: data=json.loads(r.read())
  dump(root/'response.json',data)
  text=data['choices'][0]['message']['content'];(root/'draft.md').write_text(text,encoding='utf8')
  result=dict(status='COMPLETED_UNREVIEWED',usage=data.get('usage'),provider_model=data.get('model'),elapsed_s=time.monotonic()-start,finish_reason=data['choices'][0]['finish_reason'])
 except Exception as ex:
  detail=ex.read().decode(errors='replace')[:3000] if isinstance(ex,urllib.error.HTTPError) else str(ex)
  result=dict(status='EXECUTION_FAIL',elapsed_s=time.monotonic()-start,error=detail)
 dump(root/'execution.json',result);print(json.dumps(dict(task=task,**result)),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('task');a.add_argument('prompt_file');v=a.parse_args();run(v.task,Path(v.prompt_file).read_text(encoding='utf8'))
