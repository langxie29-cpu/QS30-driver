"""Append-only KiCad 10 evidence capture; never replaces an existing run directory.

python design9/reconcile9.py --run before_a9_1
python design9/reconcile9.py --run after_a9_1 --publish
Exit 1 means reconciliation failed; native ERC/DRC failures are separately retained.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from kiutils.board import Board
from build9 import build, PIN_DB

ROOT = Path(__file__).resolve().parents[1]
KC = Path.home() / 'AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe'
BOARDS = {'QS30-9_DISPLAY': ('MOD_L',), 'QS30-9_MAIN': ('MB_', 'MOD_C')}


def read_csv():
    return list(csv.DictReader((ROOT / 'netlist9/QS30-9_REV.A_netlist.csv').open(encoding='utf-8-sig')))


def xml_nets(path):
    tree = ET.parse(path)
    refs = {}
    for c in tree.findall('./components/comp'):
        refs[c.attrib['ref']] = next((f.text for f in c.findall('./fields/field')
                                      if f.attrib.get('name') == 'DesignRef'), c.attrib['ref'])
    result, groups = {}, {}
    for n in tree.findall('./nets/net'):
        name = n.attrib['name']
        groups[name] = set()
        for node in n.findall('node'):
            key = refs[node.attrib['ref']], node.attrib['pin']
            if key in result:
                raise ValueError(f'duplicate native node {key}')
            result[key] = name
            groups[name].add(key)
    return result, groups, refs


def report_counts(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    # Both KiCad JSON schemas contain violation arrays, ERC nested under sheets.
    items = []
    def visit(obj):
        if isinstance(obj, dict):
            if 'severity' in obj and 'type' in obj:
                items.append(obj)
            else:
                for value in obj.values():
                    visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    visit(data)
    return dict(total=len(items), severity=dict(collections.Counter(i['severity'] for i in items)),
                by_type=dict(collections.Counter(i['type'] for i in items)))


def capture(run, publish=False):
    folder = ROOT / 'kicad/logs' / run
    folder.mkdir(exist_ok=False)
    rows = read_csv()
    model = build()
    version = subprocess.run([str(KC), 'version'], capture_output=True, text=True, check=True).stdout.strip()
    result = {'revision': 'REV.A9.2', 'kicad_version': version, 'run': run, 'boards': {}, 'commands': []}
    for board, prefixes in BOARDS.items():
        base = ROOT / 'kicad/projects' / board / board
        expected = {(r['ref'], r['pin']): r['net'] for r in rows if r['sheet'].startswith(prefixes)}
        if len(expected) != sum(r['sheet'].startswith(prefixes) for r in rows):
            raise ValueError(f'{board}: duplicate CSV ref/pin rows')
        def invoke(tail):
            args = [str(KC)] + list(map(str, tail))
            proc = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
            result['commands'].append({'argv': args, 'rc': proc.returncode,
                                       'stdout': proc.stdout, 'stderr': proc.stderr})
            (folder/'commands.log').write_text('\n'.join(json.dumps(c, ensure_ascii=False) for c in result['commands'])+'\n', encoding='utf-8')
            return proc.returncode
        rc = invoke(['sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', folder / f'{board}.net', base.with_suffix('.kicad_sch')])
        rcxml = invoke(['sch', 'export', 'netlist', '--format', 'kicadxml', '-o', folder / f'{board}.xml', base.with_suffix('.kicad_sch')])
        for kind, category, suffix in [('erc', 'sch', '.kicad_sch'), ('drc', 'pcb', '.kicad_pcb')]:
            for fmt, ext in [('report', 'rpt'), ('json', 'json')]:
                invoke([category, kind] + (['--schematic-parity'] if kind=='drc' else []) + ['--format', fmt, '--severity-all', '--exit-code-violations',
                        '-o', folder / f'{board}.{kind}.{ext}', base.with_suffix(suffix)])
        actual, groups, refs = xml_nets(folder / f'{board}.xml')
        mismatches = [{'ref': k[0], 'pin': k[1], 'expected': v, 'actual': actual.get(k)}
                      for k, v in expected.items() if actual.get(k) != v]
        expected_groups = collections.defaultdict(set)
        for key, net in expected.items():
            expected_groups[net].add(key)
        merges = {name: sorted({expected[k] for k in nodes if k in expected}) for name, nodes in groups.items()
                  if len({expected[k] for k in nodes if k in expected}) > 1}
        splits = {name: sorted({actual.get(k, '<missing>') for k in nodes}) for name, nodes in expected_groups.items()
                  if len({actual.get(k, '<missing>') for k in nodes}) > 1}
        pcb = Board.from_file(str(base.with_suffix('.kicad_pcb')), encoding='utf-8')
        pads = {}
        for fp in pcb.footprints:
            props = fp.properties
            ref = props.get('DesignRef', props.get('Reference'))
            for pad in fp.pads:
                if pad.net:
                    pads[(ref, pad.number)] = pad.net.name
        pad_mismatches = [{'ref': k[0], 'pin': k[1], 'expected': v, 'actual': pads.get(k)}
                          for k, v in expected.items() if pads.get(k) != v]
        unexpected = {f'{k[0]}.{k[1]}':v for k,v in actual.items() if k not in expected and not v.startswith('unconnected-')}
        nc_groups = {n: nodes for n, nodes in groups.items() if n.startswith('unconnected-')}
        expected_nc = {(p.ref,pin) for p in model.parts.values() if p.sheet.startswith(prefixes)
                       for pin in PIN_DB[p.pin_key] if pin not in p.nets}
        actual_nc = {k for k,n in actual.items() if n.startswith('unconnected-')}
        nc_inventory_matches = expected_nc == actual_nc and all(len(nodes)==1 for nodes in nc_groups.values())
        entry = dict(netlist_rc=rc, xml_rc=rcxml, expected_nodes=len(expected), actual_nodes=len(actual),
                     expected_nets=len(expected_groups), actual_nets=len(groups),
                     explicit_nc_nets=len(nc_groups), connected_actual_nets=len(groups)-len(nc_groups),
                     expected_nc_nodes=len(expected_nc), nc_inventory_matches=nc_inventory_matches,
                     matched_nodes=len(expected)-len(mismatches), mismatches=mismatches,
                     merges=merges, splits=splits, unexpected_nodes=unexpected,
                     pcb_pad_mismatches=pad_mismatches,
                     erc=report_counts(folder / f'{board}.erc.json'),
                     drc=report_counts(folder / f'{board}.drc.json'))
        entry['reconciliation'] = 'PASS' if rc == rcxml == 0 and nc_inventory_matches and not (mismatches or merges or splits or pad_mismatches or unexpected) else 'FAIL'
        result['boards'][board] = entry
        print(board, json.dumps({k: v for k, v in entry.items() if k not in ('mismatches', 'merges', 'splits', 'pcb_pad_mismatches', 'unexpected_nodes')}, ensure_ascii=False))
    result['input_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [ROOT/'netlist9/QS30-9_REV.A_netlist.csv'] +
                              sorted((ROOT/'kicad/projects').glob('*/*.kicad_sch')) +
                              sorted((ROOT/'kicad/projects').glob('*/*.kicad_pcb')) +
                              [ROOT/'design9'/n for n in ('build9.py','freeze9.py','kicad_gen.py','reconcile9.py','validate_freeze9.py','kicad_check.py')]}
    (folder/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (folder/'commands.log').write_text('\n'.join(json.dumps(c, ensure_ascii=False) for c in result['commands'])+'\n', encoding='utf-8')
    if publish:
        (ROOT/'kicad/eda_check_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in ('.', '..'):
        parser.error('run must be a single new directory name')
    evidence = capture(args.run, args.publish)
    raise SystemExit(0 if all(b['reconciliation'] == 'PASS' for b in evidence['boards'].values()) else 1)
