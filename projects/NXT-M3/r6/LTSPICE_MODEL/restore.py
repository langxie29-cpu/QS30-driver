"""Restore an LTspice raw file from local or downloaded verified gzip parts."""
import argparse
import json
from pathlib import Path
from summarize import restore_verify

parser=argparse.ArgumentParser()
parser.add_argument('run',type=Path,help='directory containing original result.json and gzip parts')
parser.add_argument('new_raw',type=Path,help='new destination file')
args=parser.parse_args()
manifest=json.loads((args.run/'result.json').read_text(encoding='utf-8'))
if manifest['raw'] is None:
    raise SystemExit('The simulator produced no raw file for this attempt')
with args.new_raw.open('xb') as target:
    restore_verify(args.run,manifest,{},target)
print(manifest['raw']['sha256'],args.new_raw)
