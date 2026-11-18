from archive import *
import collections
def main():
 statep=HERE/'evidence/github_artifacts.json';state=json.loads(statep.read_text());m=json.loads(MAN.read_text());tok=token();allremote=[];page=1
 while True:
  items=request(f'https://api.github.com/repos/langxie29-cpu/QS30-driver/releases/{state["id"]}/assets?per_page=100&page={page}',tok);allremote+=items
  if len(items)<100:break
  page+=1
 remote={x['name']:x for x in allremote};expected={p['path'].split('/')[-1]:p for r in m['records'] for p in r['parts']};verified=[]
 for name,p in expected.items():
  r=remote.get(name);assert r and r['state']=='uploaded' and r['size']==p['bytes'] and r.get('digest')=='sha256:'+p['sha256'],name
  state['assets'][name]=dict(id=r['id'],bytes=r['size'],local_sha256=p['sha256'],remote_digest=r['digest'],api_url=r['url'],browser_download_url=r['browser_download_url'],state=r['state'])
  verified.append(dict(name=name,bytes=r['size'],sha256=p['sha256'],remote_digest=r['digest']))
 assert len(expected)==78 and len(m['records'])==15
 dump(statep,state);dump(HERE/'evidence/remote_all_assets_verified.json',dict(utc=utc(),expected=len(expected),verified=len(verified),unexpected_assets=sorted(set(remote)-set(expected)),records=verified,status='ALL_REMOTE_SHA256_MATCH'))
 release=request(f'https://api.github.com/repos/langxie29-cpu/QS30-driver/releases/{state["id"]}',tok);assert release['draft'] and release['published_at'] is None
 usage=json.loads((HERE/'evidence/resource_usage.json').read_text());checks=json.loads((HERE/'evidence/regression_checks.json').read_text());ms=json.loads((HERE/'evidence/final_metrics_index.json').read_text())
 receipt=dict(utc=utc(),status='COMPLETE_SOFTWARE_EVIDENCE_DELIVERY',electrical='INCONCLUSIVE_HOLD',branch='nxt/qs30-power-loop-engineering-r3',baseline='bd1762f6b801a004b01de0f31ba5bbb8e2a60a3d',source_result_commit='d655c976325087907d3d7e439560330f3b56a6e1',final_commit_reference='Final branch HEAD reported in delivery response; receipt cannot self-reference its containing commit SHA.',Flash_sessions=usage['Flash_sessions'],Flash_tokens=usage['Flash_usage'],native_calls=usage['native_invocations'],native_wall_seconds=usage['native_wall_seconds'],raw_files=len(m['records']),raw_bytes=sum(x['original_bytes'] for x in m['records']),archive_parts=len(expected),archive_bytes=sum(x['bytes'] for x in expected.values()),remote_SHA256_verified=len(verified),failed_native_attempts=1,failed_raws=0,failed_logs_preserved=1,R3_deleted_raws=0,R2_permanently_missing_raws=2,qualified_model_status_counts=dict(collections.Counter(x['classification'] for x in ms)),unit_tests=7,evidence_checks=checks['checks'],release=dict(id=state['id'],html_url=release['html_url'],draft=True,published_at=None),hardware_actions=0,manufacturing='HOLD',main_merged=False)
 dump(HERE/'evidence/delivery_receipt.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
