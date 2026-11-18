"""Upload large archived parts to an unpublished GitHub evidence draft; preserve local bytes."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib import error, parse, request

HERE = Path(__file__).resolve().parent
REPO = 'https://api.github.com/repos/langxie29-cpu/QS30-driver'
NAME = 'nxt-m3-r6-native-evidence-20261119'
STATE = HERE.parent/'evidence'/'large_raw_archive.json'
LARGE = ('p1_nominal', 'p1b_nominal', 'diagnostic_cold', 'p1c_full',
         'surrogate_nominal', 'surrogate_high_line', 'surrogate_low_line')

def git_token():
    req = subprocess.run(['git','credential','fill'], input='protocol=https\nhost=github.com\n\n',
                         capture_output=True, text=True, check=True, timeout=30)
    return dict(line.split('=',1) for line in req.stdout.splitlines() if '=' in line)['password']

def call(url, token, data=None, kind=None):
    headers = {'Authorization':'Bearer '+token, 'Accept':'application/vnd.github+json',
               'User-Agent':'NXT-M3-R6', 'X-GitHub-Api-Version':'2022-11-28'}
    if kind:
        headers['Content-Type'] = kind
    req = request.Request(url,data=data,headers=headers)
    with request.urlopen(req, timeout=180) as incoming:
        return json.load(incoming)

def bin_upload(target, tok, local, info):
    name = local.parent.name+'_'+local.name
    contents = local.read_bytes()
    if hashlib.sha256(contents).hexdigest() != info['sha256']:
        raise ValueError('source part hash mismatch: '+name)
    for wait in (0,3,12):
        time.sleep(wait)
        try:
            asset = call(target+'?'+parse.urlencode({'name':name}),tok,contents,'application/octet-stream')
            if asset['size'] != info['bytes'] or asset.get('digest') != 'sha256:'+info['sha256']:
                raise RuntimeError('GitHub size or digest mismatch: '+name)
            return name, dict(info, case=local.parent.name, asset_id=asset['id'],
                              api_url=asset['url'], digest=asset['digest'])
        except (error.URLError, TimeoutError):
            if wait == 12:
                raise

def main():
    tok = git_token()
    drafts = call(REPO+'/releases?per_page=100',tok)
    rel = next((r for r in drafts if r['tag_name']==NAME), None)
    if rel is None:
        body = dict(tag_name=NAME, target_commitish='5bc45db875b26dde9f1f4d8cf20fcd0f8943b5c0',
                    name='NXT-M3 R6 native simulation evidence (HOLD)',draft=True,prerelease=True,
                    body='Research archive of raw waveform parts only. Use the R6 reconstruction branch and SHA manifest. No manufacturing or high-voltage qualification.')
        rel = call(REPO+'/releases',tok,json.dumps(body).encode(),'application/json')
    if not rel['draft']:
        raise ValueError('Evidence archive must be a draft')
    state = dict(id=rel['id'], tag=NAME, draft=True, url=rel['html_url'], verified={}, failures={})
    listed = call(rel['url']+'/assets?per_page=100',tok)
    known = {a['name']:a for a in listed}
    def save():
        STATE.write_text(json.dumps(state, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    save()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as worker:
        jobs = {}
        for case in LARGE:
            directory = HERE/'runs'/case
            manifest = json.loads((directory/'result.json').read_text(encoding='utf-8'))
            for info in manifest['evidence']:
                if not info['file'].endswith('.gz'):
                    continue
                name = case+'_'+info['file']
                if name in known:
                    item = known[name]
                    if item.get('digest') == 'sha256:'+info['sha256'] and item['size'] == info['bytes']:
                        state['verified'][name] = dict(info, case=case, asset_id=item['id'],
                                                       api_url=item['url'], digest=item['digest'])
                    else:
                        state['failures'][name] = 'remote size/digest differs'
                    continue
                future = worker.submit(bin_upload, rel['upload_url'].split('{')[0], tok, directory/info['file'], info)
                jobs[future] = name
        for future in concurrent.futures.as_completed(jobs):
            try:
                name, result = future.result()
                state['verified'][name] = result
                print(name, 'verified', flush=True)
            except (error.URLError, TimeoutError, RuntimeError) as exc:
                state['failures'][jobs[future]] = f'{type(exc).__name__} {getattr(exc, "code","")}'
            save()
    if state['failures']:
        raise SystemExit('Some parts unavailable remotely; originals preserved locally.')

if __name__ == '__main__':
    main()
