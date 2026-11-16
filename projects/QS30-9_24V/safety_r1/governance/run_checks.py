"""Run all finite software/data suites and keep an auditable summary. No SPICE."""
import argparse, datetime, json, pathlib, re, subprocess, sys
HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[2]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Refusing to overwrite prior check evidence')
    rows=[]
    for directory in ['verification','review','governance']:
        cmd=[sys.executable,'-m','unittest','discover','-s',str(BASE/directory),'-p','test_*.py','-v']
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        log=p.stdout+p.stderr
        match=re.search(r'Ran (\d+) tests?',log)
        count=int(match[1]) if match else 0
        rows.append(dict(suite=directory,argv=cmd,returncode=p.returncode,tests=count,
                         status='PASS' if p.returncode==0 and count>0 else 'FAIL',log=log))
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,
                suites=rows,tests=sum(r['tests'] for r in rows),
                status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
                scope='Finite specification and candidate data checks only; no new simulation or hardware validation',manufacturing='HOLD')
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='suites'},ensure_ascii=False))
    return result['status']!='PASS'
if __name__=='__main__':sys.exit(main())
