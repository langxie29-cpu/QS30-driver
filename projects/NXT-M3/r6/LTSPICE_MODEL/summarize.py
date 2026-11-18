"""Recompute a run census and raw file fidelity; do not mutate historical run evidence."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
from run import readlog
from archive import LARGE

HERE = Path(__file__).resolve().parent

def endpoints(raw):
    with raw.open('rb') as source:
        prefix = source.read(8192)
        encoding = 'utf-16le' if prefix[1:2]==b'\x00' else 'ascii'
        marker = 'Binary:\n'.encode(encoding)
        start = prefix.index(marker)+len(marker)
        head = prefix[:start].decode(encoding)
        count = int(re.search(r'No\. Variables:\s*(\d+)',head)[1])
        flags = re.search(r'Flags:\s*([^\n]+)',head)[1]
        layout = struct.Struct('<d'+('d' if 'double' in flags else 'f')*(count-1))
        whole, tail = divmod(raw.stat().st_size-start,layout.size)
        if whole == 0:
            return {}
        source.seek(start+(whole-1)*layout.size)
        values = layout.unpack(source.read(layout.size))
        names = re.findall(r'^\s*\d+\s+(\S+)\s+\S+$',head,re.M)
        if len(names)!=count:
            raise ValueError(raw)
        return dict(zip(names,values), samples=whole, trailing_bytes=tail)

def restore_verify(directory, result, archive, write_to=None):
    raw = result['raw']
    if raw is None:
        return
    original = hashlib.sha256()
    size = 0
    for record in result['evidence']:
        if not record['file'].endswith('.gz'):
            continue
        path = directory/record['file']
        part = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024**2), b''):
                part.update(chunk)
        assert part.hexdigest()==record['sha256']
        key = directory.name+'_'+path.name
        if directory.name in LARGE and archive:
            assert archive[key]['digest']=='sha256:'+record['sha256']
        with gzip.open(path,'rb') as stream:
            for chunk in iter(lambda: stream.read(1024**2), b''):
                original.update(chunk)
                size += len(chunk)
                if write_to:
                    write_to.write(chunk)
    assert original.hexdigest()==raw['sha256'] and size==raw['bytes'], directory

def main(verify):
    rows = []
    manifest = HERE.parent/'evidence'/'large_raw_archive.json'
    archive = json.loads(manifest.read_text(encoding='utf-8'))['verified'] if manifest.exists() else {}
    for path in sorted((HERE/'runs').glob('*/result.json')):
        r = json.loads(path.read_text(encoding='utf-8'))
        directory = path.parent
        classification = r['classification']
        vals = r['measures'].copy()
        log = readlog(directory/'boost.log')
        for key in ('start_160','fault_time','dual_60','single_60'):
            vals.pop(key,None)
            t = re.search('^'+key+r':.*?\bAT\s+([0-9.eE+-]+)',log,re.I|re.M)
            if t:
                vals[key]=float(t[1])
        if 'unknown subcircuit' in log.lower():
            classification = 'MODEL_FAIL'
        if directory.name=='diagnostic_decay':
            classification = 'INCONCLUSIVE'
        if verify:
            restore_verify(directory,r,archive)
        raw = directory/'boost.raw'
        ep = endpoints(raw) if raw.exists() else {}
        rows.append(dict(run=directory.name,input_case=r['case'],classification=classification,
                         elapsed_s=r['seconds'],actual_endpoint_s=ep.get('time',''),raw_endpoint_hv=ep.get('V(hv)',''),
                         raw_samples=ep.get('samples',''),raw_sha256=(r['raw'] or {}).get('sha256',''),
                         evidence=str(directory.relative_to(HERE.parent)).replace('\\','/'),**vals))
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (HERE.parent/'SIMULATION_RESULTS.csv').open('w',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f'{len(rows)} native attempts; archive byte verification={verify}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    main(parser.parse_args().verify)
