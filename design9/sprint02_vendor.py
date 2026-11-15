"""Append-only vendor diode syntax probe. Original library stays unchanged."""
from pathlib import Path
import importlib.util,json,sys,argparse
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s02',ROOT/'design9/sprint02_hv.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--compat',action='store_true');a=ap.parse_args()
 assert Path(a.run).name==a.run
 dest=ROOT/'sim/sprint02'/a.run;dest.mkdir(exist_ok=False)
 original=ROOT/'sim/sprint02/source/diotec_uf4007_spice.lib'
 raw=original.read_bytes()
 if a.compat:
  raw=raw.replace(b' mfg=Diotec type=Rectifier',b'')
 model=dest/'diode.lib';model.write_bytes(raw)
 deck='Diotec UF4007 vendor model IV probe\n.include "'+str(model.resolve()).replace(chr(92),'/')+'"\n'+"""ITEST 0 a PWL(0 0 1u .003 1m .003)
XTEST a 0 UF4007
.control
set noaskquit
set wr_singlescale
set wr_vecnames
tran 1u 1m
meas tran end_time MAX time
meas tran diode_v FIND v(a) AT=.001
wrdata waves.txt v(a)
quit
.endc
.end
"""
 r=s.h.simulate(dest/'probe',deck,.001,{'model_url':'https://diotec.com/request/spice/uf4007.zip','source_sha256':s.sha(original),'compatibility_change':'remove LTspice mfg/type metadata only' if a.compat else 'none'},lambda t,v:{'vf_3mA_V':float(v('v(a)')[-1]),'status':'OBSERVATION'})
 (dest/'results.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf-8');main()
