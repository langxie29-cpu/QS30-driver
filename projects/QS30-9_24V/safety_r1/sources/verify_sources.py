"""Verify archived primary-source bytes without changing historical files."""
import hashlib
import json
from pathlib import Path


def verify():
    here = Path(__file__).resolve().parent
    records = json.loads((here / 'device_qualification.json').read_text(encoding='utf8'))
    errors = []
    for row in records:
        source = here / (row['mpn'] + '.pdf')
        if not source.exists():
            errors.append(row['mpn'] + ': missing source')
        elif hashlib.sha256(source.read_bytes()).hexdigest() != row['source_sha256']:
            errors.append(row['mpn'] + ': hash mismatch')
        elif not source.read_bytes().startswith(b'%PDF'):
            errors.append(row['mpn'] + ': not PDF')
    return len(records), errors


if __name__ == '__main__':
    count, errors = verify()
    print(json.dumps(dict(sources=count, errors=errors), indent=2))
    raise SystemExit(bool(errors))
