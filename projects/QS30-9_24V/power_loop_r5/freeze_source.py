"""Freeze R4 native source and build the independent KiCad pin inventory."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
R4 = HERE.parent / 'power_loop_r4'
SOURCE = R4 / 'EVT01'
EVIDENCE = HERE / 'evidence'
KICAD = Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
BASE = 'ff6af65b557905308f7c3fcb318848eaca1a1d0b'
ROOT_SHEET = 'NXT-PWR-EVT01.kicad_sch'


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, label):
    result = subprocess.run(argv, capture_output=True, timeout=120)
    (EVIDENCE / f'{label}.log').write_bytes(
        f'exit={result.returncode}\n'.encode() + result.stdout + result.stderr)
    if result.returncode and label != 'kicad_erc':
        result.check_returncode()


def pin_inventory(xml_path):
    root = ET.parse(xml_path)
    libraries = {(p.get('lib'), p.get('part')): p for p in root.findall('./libparts/libpart')}
    nets = {}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            key = (node.get('ref'), node.get('pin'))
            if key in nets:
                raise ValueError(f'Pin on multiple nets: {key}')
            nets[key] = net.get('name')
    rows = {}
    references = []
    for c in root.findall('./components/comp'):
        ref = c.get('ref')
        source = c.find('libsource')
        symbol = (source.get('lib'), source.get('part'))
        props = {p.get('name'): p.get('value') for p in c.findall('property')}
        sheet = c.find('sheetpath').get('names').strip('/')
        library_pins = libraries[symbol].findall('./pins/pin')
        groups = c.findall('./units/unit')
        if len(groups) != 1 or groups[0].get('name') != 'A':
            raise ValueError(f'Check unit mapping at {ref}')
        instance_pins = {p.get('num') for p in groups[0].findall('./pins/pin')}
        if instance_pins != {p.get('num') for p in library_pins}:
            raise ValueError(f'Check library vs instance pins at {ref}')
        part = dict(reference=ref, unit='1', sheet=sheet, symbol=':'.join(symbol),
                    value=c.findtext('value'), mpn=props.get('MPN', ''),
                    footprint=c.findtext('footprint', ''),
                    population='DNP' if 'dnp' in props else 'FIT',
                    status=props.get('Status', ''))
        references.append(part)
        for pin in library_pins:
            num = pin.get('num')
            net = nets.pop((ref, num))
            rows[(ref, num)] = dict(**part, physical_pin=num, pin_name=pin.get('name'),
                                    pin_type=pin.get('type'), raw_net=net,
                                    net='' if net.startswith('unconnected-') else net)
    if nets:
        raise ValueError(f'Unaccounted native net nodes: {nets}')
    return root.findall('./design/sheet'), references, rows


def archive_source(paths, label):
    with zipfile.ZipFile(EVIDENCE / f'{label}.zip', 'w', zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(paths):
            zipped.writestr(zipfile.ZipInfo(p.name), p.read_bytes(), zipfile.ZIP_DEFLATED)


def main():
    review = json.loads((SOURCE / 'latest_review.json').read_text(encoding='utf-8'))
    snapshot = R4 / Path(review['run'].replace(chr(92), '/')) / 'snapshot'
    archived_only = {'SAFETY_3.kicad_sch'}
    historical = {name: file_hash(snapshot / name) for name in review['snapshot_sha256']}
    if historical != review['snapshot_sha256']:
        raise ValueError('R4 historical snapshot hash mismatch')
    hashes = {name: file_hash(SOURCE / name) for name in historical if name not in archived_only}
    mismatches = {name for name in hashes if hashes[name] != historical[name]}
    if mismatches != {'latest_review.json'}:
        raise ValueError(f'Unexpected R4 frozen source change: {mismatches}')
    for label, manifest in [('R4_SOURCE', hashes), ('R4_HISTORICAL_SNAPSHOT', historical)]:
        (EVIDENCE / f'{label}.sha256').write_text(
            ''.join(f'{sha}  {name}\n' for name, sha in sorted(manifest.items())), encoding='utf-8')
    native = [SOURCE / name for name in hashes if name not in archived_only and (Path(name).suffix in
              {'.kicad_pro', '.kicad_sch', '.kicad_sym'} or name.endswith('-lib-table'))]
    archive_source(native, 'R4_FULL_INPUT')
    archive_source([SOURCE / 'POWER_1.kicad_sch', SOURCE / 'NXT.kicad_sym',
                    SOURCE / 'sym-lib-table'], 'R4_POWER_1_INPUT')
    run([str(KICAD), 'version'], 'kicad_version')
    with tempfile.TemporaryDirectory(prefix='qs30-r5-kicad-') as temp:
        clone = Path(temp)
        for path in native:
            shutil.copy2(path, clone / path.name)
        run([str(KICAD), 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o',
             str(EVIDENCE / 'kicad_full.xml'), str(clone / ROOT_SHEET)], 'kicad_full')
        run([str(KICAD), 'sch', 'erc', '--format', 'json', '--severity-all',
             '--exit-code-violations', '-o', str(EVIDENCE / 'kicad_erc.json'),
             str(clone / ROOT_SHEET)], 'kicad_erc')
        run([str(KICAD), 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o',
             str(EVIDENCE / 'kicad_power_1.xml'), str(clone / 'POWER_1.kicad_sch')],
            'kicad_power_1')
    sheets, refs, pins = pin_inventory(EVIDENCE / 'kicad_full.xml')
    old_path = R4 / review['run'].replace('\\', '/') / 'native.net'
    old_sheets, old_refs, old_pins = pin_inventory(old_path)
    if [s.get('name') for s in sheets] != [s.get('name') for s in old_sheets]:
        raise ValueError('Native sheet set or order changed')
    if refs != old_refs or pins != old_pins:
        raise ValueError('Frozen vs fresh native export mismatch')
    with (SOURCE / 'pin_connections.csv').open(newline='', encoding='utf-8-sig') as stream:
        design = {(r['ref'], r['pin']): r for r in csv.DictReader(stream)}
    assert design.keys() == pins.keys()
    for key, actual in pins.items():
        declared = design[key]
        for native_key, design_key in [('pin_name','pin_name'), ('net','net'), ('mpn','MPN'),
                                       ('footprint','footprint'), ('pin_type','pin_type')]:
            expected = declared[design_key]
            if native_key == 'net' and expected == 'NC':
                expected = ''
            if actual[native_key] != expected:
                raise ValueError((key, native_key, actual[native_key], declared[design_key]))
    sample_sheets, sample_refs, sample_pins = pin_inventory(EVIDENCE / 'kicad_power_1.xml')
    sample_baseline = {k: v for k, v in pins.items() if v['sheet'] == 'POWER_1'}
    assert sample_pins.keys() == sample_baseline.keys()
    assert all(r['net'] == sample_baseline[k]['net'] for k, r in sample_pins.items())
    write_csv(HERE / 'MIGRATION_PIN_NET_DIFF.csv', [
        dict(**p, easyeda_reference='', easyeda_unit='', easyeda_physical_pin='',
             easyeda_pin_name='', easyeda_net='', easyeda_mpn='', easyeda_footprint='',
             easyeda_population='', result='UNOBSERVED_TARGET') for p in pins.values()])
    footprint_audit = json.loads((SOURCE / 'footprint_audit.json').read_text(encoding='utf-8'))
    footprints = {r['ref']: r for r in footprint_audit['records']}
    installed = KICAD.parents[1] / 'share' / 'kicad' / 'footprints'
    verified_footprints = {}
    for item in footprints.values():
        if item['footprint'] not in verified_footprints:
            library, name = item['footprint'].split(':', 1)
            verified_footprints[item['footprint']] = file_hash(
                installed / f'{library}.pretty' / f'{name}.kicad_mod')
        if verified_footprints[item['footprint']] != item['sha256']:
            raise ValueError(f'Installed footprint changed: {item["footprint"]}')
    library_rows = []
    for part in refs:
        footprint = footprints.get(part['reference'], {})
        library_rows.append(dict(**part, r4_pad_set=' '.join(footprint.get('pads', [])),
                                 r4_pad_match=footprint.get('padset_matches', 'UNASSIGNED'),
                                 r4_footprint_sha256=footprint.get('sha256', ''),
                                 target_symbol='', target_footprint='', target_pad_set='',
                                 result='UNOBSERVED_TARGET'))
    write_csv(HERE / 'MIGRATION_LIBRARY_AUDIT.csv', library_rows)
    erc = json.loads((EVIDENCE / 'kicad_erc.json').read_text(encoding='utf-8'))
    violations = [v for s in erc['sheets'] for v in s['violations']]
    report = dict(base=BASE, verified_hashes=len(hashes), historical_only=sorted(archived_only), pages=len(sheets), references=len(refs),
                  library_symbols=len({r['symbol'] for r in refs}), footprint_records=len(footprints),
                  installed_footprints_verified=len(verified_footprints),
                  connected=sum(bool(p['net']) for p in pins.values()), physical_pins=len(pins),
                  population=Counter(r['population'] for r in refs),
                  sample_pages=len(sample_sheets), sample_parts=len(sample_refs),
                  sample_pins=len(sample_pins), sample_connected=sum(bool(p['net']) for p in sample_pins.values()),
                  erc_severity=Counter(v['severity'] for v in violations),
                  erc_types=Counter(v['type'] for v in violations))
    (EVIDENCE / 'source_audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
