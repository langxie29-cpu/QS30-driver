"""Restore split gzip evidence, verifying SHA-256 before replacing a file."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'docs9/SIMULATION_ARCHIVE_PARTS.json').read_text())
    for entry in manifest:
        target = root / entry['path']
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError(f'Existing archive differs: {target}')
            print(f'Already verified: {entry["path"]}')
            continue
        temporary = target.with_name(target.name + '.restoring')
        try:
            digest = hashlib.sha256()
            size = 0
            with temporary.open('xb') as output:
                for part in entry['parts']:
                    data = (root / part['path']).read_bytes()
                    if len(data) != part['size'] or hashlib.sha256(data).hexdigest() != part['sha256']:
                        raise ValueError(f'Part verification failed: {part["path"]}')
                    output.write(data)
                    digest.update(data)
                    size += len(data)
            if size != entry['size'] or digest.hexdigest() != entry['sha256']:
                raise ValueError(f'Archive verification failed: {entry["path"]}')
            temporary.rename(target)
        finally:
            if temporary.exists():
                temporary.unlink()
        print(f'Restored and verified: {entry["path"]}')


if __name__ == '__main__':
    main()
