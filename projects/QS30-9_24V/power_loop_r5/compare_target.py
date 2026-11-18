"""Compare a normalized export from a real EasyEDA target to the frozen source."""
import argparse
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = ('reference', 'unit', 'physical_pin')
FIELDS = ('pin_name', 'net', 'mpn', 'footprint', 'population')


def index(rows):
    pins = {}
    for row in rows:
        key = tuple(row[field] for field in KEY)
        if not all(key) or key in pins:
            raise ValueError(f'Invalid or duplicate pin key: {key}')
        if any(row[field] is None for field in FIELDS):
            raise ValueError(f'Incomplete pin row: {key}')
        pins[key] = row
    return pins


def compare(baseline, converted):
    differences = []
    for key in sorted(baseline.keys() | converted.keys()):
        source, target = baseline.get(key), converted.get(key)
        if not source or not target:
            differences.append(dict(pin=key, state='EXTRA_PIN' if target else 'MISSING_PIN'))
            continue
        values = {name: [source[name], target[name]] for name in FIELDS if source[name] != target[name]}
        if values:
            differences.append(dict(pin=key, state='CHANGED_FIELDS', fields=values))
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path, help='Normalized export (one row per physical pin)')
    parser.add_argument('output', type=Path, help='New JSON comparison path')
    args = parser.parse_args()
    with (HERE / 'MIGRATION_PIN_NET_DIFF.csv').open(newline='', encoding='utf-8') as f:
        baseline = index(csv.DictReader(f))
    with args.target.open(newline='', encoding='utf-8-sig') as f:
        target = index(csv.DictReader(f))
    differences = compare(baseline, target)
    result = dict(source_pins=len(baseline), target_pins=len(target),
                  status='DIFFERENCES' if differences else 'NORMALIZED_FIELDS_MATCH',
                  differences=differences)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write('\n')
    return int(bool(differences))


if __name__ == '__main__':
    raise SystemExit(main())
