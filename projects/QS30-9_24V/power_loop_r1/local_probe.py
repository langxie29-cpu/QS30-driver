"""Read-only/redacted environment probe and isolated Harness home bootstrap."""
from pathlib import Path
import os, json, subprocess, tomllib, zipfile

HERE = Path(__file__).resolve().parent
LOCAL = HERE / '.local'
DSH = Path('D:/PROJECTS/DeepSeekHarness')
NODE = DSH / 'runtime/node-v24.19.0-win-x64/node.exe'
CLI = DSH / 'app/node_modules/@deepseek-ai/dsh/lib/bin.js'
OLD = Path('D:/PROJECTS/dsharness/QS30-1/projects/QS30-9_24V')
LT = OLD / 'toolchain/ltspice26/extracted/LTspice.exe'
NG = Path('D:/PROJECTS/dsharness/QS30-1/tools/ngspice47/Spice64/bin/ngspice_con.exe')

def setup():
    import shutil
    LOCAL.mkdir(exist_ok=True)
    home = LOCAL / 'dsh_home'
    for rel in ['profiles/headless/package.json', 'profiles/headless/cordis.patch.yml', 'cordis.patch.yml', '.credentials.yaml']:
        src = DSH / 'data' / rel
        dst = home / rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    # Private copied configuration is deliberately ignored, never archived.
    env = dict(os.environ, DSH_HOME=str(home), DSH_TELEMETRY_DISABLED='1')
    overlay = LOCAL / 'flash.patch.yml'
    overlay.write_text('''- id: agent-default-model
  config:
    provider: deepseek-official
    model: deepseek-flash
- id: llm-deepseek
  config:
    baseURL: https://api.deepseek.com
    maxTokens: 12000
    thinking: disabled
    reasoningEffort: off
    models:
      - id: deepseek-flash
        contextWindow: 1000000
- id: session-title-llm
  disabled: true
- id: tool-subagent
  disabled: true
- id: tool-subagent-fork
  disabled: true
- id: tool-ralph
  disabled: true
- id: tool-workflow
  disabled: true
- id: tool-goal
  disabled: true
''', encoding='utf8')
    env['QS30_DSH_NODE'] = str(NODE)
    env['QS30_DSH_CLI'] = str(CLI)
    env['QS30_DSH_PATCH'] = str(overlay)
    env['QS30_DSH_HOME'] = str(home)
    return env

if __name__ == '__main__':
    env = setup()
    p = subprocess.run([str(NODE),str(CLI),'--profile','headless','--patch',str(LOCAL/'flash.patch.yml'),'--dump-config'],env=env,capture_output=True,text=True,encoding='utf8')
    (LOCAL/'dump.private.txt').write_text(p.stdout,encoding='utf8')
    print(json.dumps({'dump_rc':p.returncode,'flash_string': 'deepseek-flash' in p.stdout,'error':p.stderr[-1500:]},ensure_ascii=False))
    cfg = tomllib.loads((Path.home()/'.codex/config.toml').read_text(encoding='utf8'))
    def public(c):
        return {k:v for k,v in c.items() if k in ('model','model_provider','openai_base_url','base_url','wire_api')}
    print(json.dumps({'codex_defaults':public(cfg),'gpt_profile':public(cfg.get('profiles',{}).get('gpt',{})), 'providers':{k:public(v) for k,v in cfg.get('model_providers',{}).items()},'ltspice':str(LT),'ngspice':str(NG)},ensure_ascii=False))
    print(subprocess.run([str(NODE),str(CLI),'--profile','headless','--help'],env=env,capture_output=True,text=True,encoding='utf8').stdout[:10000])
    for name in ['lib.zip','examples.zip']:
        z=zipfile.ZipFile(LT.parent/name)
        print(name, [n for n in z.namelist() if '3757' in n.lower()])
