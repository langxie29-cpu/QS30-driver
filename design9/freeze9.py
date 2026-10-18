"""Generate only REV.A9.1 electrical CSVs; do not overwrite historical audit reports.

This is the authoritative electrical generation entry point for REV.A9.1.
Run this, kicad_gen.py, then reconcile9.py with a NEW --run name.
Legacy build9.main() is retained as historical report generation, not the A9.1 entry point.
"""
import csv
from pathlib import Path
from build9 import build, channel_map, PIN_DB

ROOT = Path(__file__).resolve().parents[1]


def main():
    d = build()
    path = ROOT/'netlist9/QS30-9_REV.A_netlist.csv'
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['ref','mpn','value','package','sheet','pin','pin_name','net','net_class','part_status','note'])
        for p in sorted(d.parts.values(), key=lambda p:p.ref):
            for pin, net in sorted(p.nets.items(), key=lambda kv:(len(kv[0]),kv[0])):
                w.writerow([p.ref,p.mpn,p.value,p.pkg,p.sheet,pin,PIN_DB[p.pin_key][pin],net,d.net_class[net],p.status,p.note])
    mapping = channel_map(d)
    with (ROOT/'docs9/channel_map9.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(mapping[0]))
        w.writeheader(); w.writerows(mapping)
    print(f'{len(d.parts)} parts, {sum(len(p.nets) for p in d.parts.values())} connected pins, {len(d.nets())} nets, {len(mapping)} cathodes')


if __name__ == '__main__':
    main()
