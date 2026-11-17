"""Use installed Harness in a private home, reuse existing bounded coordinator."""
import os, sys
import local_probe
os.environ.update(local_probe.setup())
if os.environ.get('QS30_R2_REVIEW_ONLY') == '1':
    patch = local_probe.LOCAL / 'flash.patch.yml'
    with patch.open('a', encoding='utf8') as f:
        f.write('\n- id: tool-pwsh\n  disabled: true\n- id: tool-bash\n  disabled: true\n- id: tool-jobs\n  disabled: true\n')
import orchestrate
if __name__ == '__main__':
    orchestrate.main()
