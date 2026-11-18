"""Read-only historical/experiment verification; no simulation, no API-model calls."""
from r4lib import *
import subprocess,unittest,io,os
from artifact_store import token,request,REPO
def main():
 old=json.loads((HERE/'evidence/preflight/historical_before.json').read_text(encoding='utf8'));bad=[]
 for r in old:
  p=Path(r['path'])
  if not p.exists() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:bad.append(r['path'])
 ledger=json.loads((HERE/'evidence/execution_ledger.json').read_text());checks=[]
 for r in ledger['records']:
  p=HERE/r['path'];pre=json.loads((p/'preregister.json').read_text());sealed=json.loads((p/'SHA256.json').read_text());diff=[]
  for item in sealed:
   if sha(p/item['path'])!=item['sha256']:diff.append(item['path'])
  assert sha(p/'circuit.cir')==pre['netlist_sha256']
  assert all(sha(p/n)==h for n,h in pre['model_hashes'].items())
  checks.append(dict(case=r['case'],sealed_files=len(sealed),mismatches=diff,raw_retained=(p/'circuit.raw').exists()))
 # Existing parser/byte-codec tests use temporary fixtures only.
 suite=unittest.TestSuite()
 for module in ['test_lab','test_raw_archive']:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 (HERE/'evidence/parser_codec_tests.txt').write_text(stream.getvalue(),encoding='utf8')
 state=json.loads((HERE/'evidence/github_artifacts.json').read_text());tok=token()
 release=request(f'https://api.github.com/repos/{REPO}/releases/{state["id"]}',tok)
 assets=request(f'https://api.github.com/repos/{REPO}/releases/{state["id"]}/assets?per_page=100',tok)
 manifest=json.loads((HERE/'evidence/raw_archive_manifest.json').read_text());expected={Path(p['path']).name:p for r in manifest['records']for p in r['parts']};found={a['name']:a for a in assets};remote=[]
 for name,p in expected.items():
  a=found.get(name,{});remote.append(dict(name=name,bytes=a.get('size'),digest=a.get('digest'),ok=a.get('size')==p['bytes'] and a.get('digest')=='sha256:'+p['sha256']))
 smoke=next(r for r in manifest['records']if 'sic_1ns_'in r['source']);restored=HERE/'.local/remote_restore_smoke'/smoke['source'];assert sha(restored)==smoke['original_sha256']
 receipt=dict(utc=utc(),historical_files=len(old),historical_bytes=sum(r['bytes']for r in old),historical_mismatches=bad,experiments=checks,tests=dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful()),remote=dict(draft=release['draft'],target=release['target_commitish'],tag=release['tag_name'],assets=remote,verified=len([r for r in remote if r['ok']])),remote_download_restore=dict(source=smoke['source'],bytes=restored.stat().st_size,sha256=sha(restored),status='EXACT_BYTE_RECONSTRUCTION'),R4_raw_deleted=0,historical_R2_raw_missing=2)
 dump(HERE/'evidence/final_verification.json',receipt)
 assert not bad and all(not r['mismatches']and r['raw_retained']for r in checks)and result.wasSuccessful()
 assert release['draft']and release['target_commitish']=='nxt/qs30-power-loop-engineering-r4'and len(remote)==21 and all(r['ok']for r in remote)
 print(json.dumps(dict(historical=len(old),mismatches=len(bad),tests=result.testsRun,remote_assets_verified=len(remote),download_restore='EXACT_BYTE_RECONSTRUCTION')))
if __name__=='__main__':main()
