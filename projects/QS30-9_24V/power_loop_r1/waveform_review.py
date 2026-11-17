"""Independent LTspice ASCII reader and quantitative checks on actual raw data.

No generation of waveforms. Bounds, integration and sustained recovery use time,
not an unweighted average of adaptive SPICE sample points.
"""
from pathlib import Path
import math, re, bisect, json, argparse, struct

def read_native(path):
    """Read uncompressed normal-order real LT raw (ASCII or binary)."""
    b=Path(path).read_bytes()
    utf16=b.startswith(b'T\0') or b.startswith(b'\xff\xfe')
    enc='utf-16-le' if utf16 else 'utf-8-sig'
    marker='Binary:\n'.encode(enc) if utf16 else b'Binary:\n'
    marker_cr='Binary:\r\n'.encode(enc) if utf16 else b'Binary:\r\n'
    pos=b.find(marker_cr);m=marker_cr
    if pos<0:pos=b.find(marker);m=marker
    if pos<0:return read_ascii(path)
    head=b[:pos].decode(enc)
    flags=re.search(r'Flags:\s*([^\r\n]+)',head)[1].lower().split()
    if 'complex' in flags or 'fastaccess' in flags:raise ValueError('Unsupported raw layout')
    n=int(re.search(r'No\. Variables:\s*(\d+)',head)[1]);count=int(re.search(r'No\. Points:\s*(\d+)',head)[1])
    names=[l.split()[1].lower() for l in head.rsplit('Variables:',1)[1].splitlines() if l.strip()]
    if len(names)!=n or count<2:raise ValueError('Invalid binary header')
    data=memoryview(b)[pos+len(m):]
    # Some LT versions omit a double flag. Accept only an EXACT byte-size match.
    double_size=count*n*8; mixed_size=count*(8+(n-1)*4)
    if len(data)==double_size:fmt='<'+('d'*n)
    elif len(data)==mixed_size and 'double' not in flags:fmt='<d'+('f'*(n-1))
    else:raise ValueError('Incomplete/unknown binary data length')
    columns=[[] for _ in range(n)]
    for row in struct.iter_unpack(fmt,data):
        if not all(math.isfinite(v) for v in row):raise ValueError('Nonfinite binary value')
        if columns[0] and row[0]<=columns[0][-1]:raise ValueError('Nonmonotonic binary time')
        for col,value in zip(columns,row):col.append(value)
    return dict(zip(names,columns))

def read_ascii(path):
    b=Path(path).read_bytes()
    encoding='utf-16-le' if b.startswith(b'T\0') or b.startswith(b'\xff\xfe') else 'utf-8-sig'
    s=b.decode(encoding, errors='strict')
    if 'Binary:' in s:
        raise ValueError('Expected ASCII raw; preserve binary and export with native solver')
    head, body=s.split('Values:',1)
    n=int(re.search(r'No\. Variables:\s*(\d+)',head)[1])
    count=int(re.search(r'No\. Points:\s*(\d+)',head)[1])
    names=[l.split()[1].lower() for l in head.rsplit('Variables:',1)[1].splitlines() if l.strip()]
    if len(names)!=n: raise ValueError('Variable count mismatch')
    lines=iter(body.splitlines())
    rows=[]
    for line in lines:
        if not line.strip(): continue
        first=line.split()
        if int(first[0])!=len(rows): raise ValueError('Nonsequential point index')
        row=[float(first[1])]+[float(next(lines).strip()) for _ in range(n-1)]
        if not all(math.isfinite(v) for v in row): raise ValueError('Nonfinite raw value')
        if rows and row[0]<=rows[-1][0]: raise ValueError('Nonmonotonic time')
        rows.append(row)
    if len(rows)!=count or count<2: raise ValueError('Incomplete raw point count')
    return {name:[r[i] for r in rows] for i,name in enumerate(names)}

def interp(t,y,x):
    if x<t[0] or x>t[-1]: raise ValueError('Window outside actual data')
    i=bisect.bisect_left(t,x)
    if i<len(t) and t[i]==x: return y[i]
    f=(x-t[i-1])/(t[i]-t[i-1])
    return y[i-1]*(1-f)+y[i]*f

def window(t,y,a,b):
    if b<=a: raise ValueError('Empty window')
    lo,hi=bisect.bisect_right(t,a),bisect.bisect_left(t,b)
    tt=[a]+t[lo:hi]+[b]; yy=[interp(t,y,a)]+y[lo:hi]+[interp(t,y,b)]
    return tt,yy

def stats(t,y,a,b):
    tt,yy=window(t,y,a,b)
    area=sum((tt[i+1]-tt[i])*(yy[i+1]+yy[i])/2 for i in range(len(tt)-1))
    return dict(mean=area/(b-a),minimum=min(yy),maximum=max(yy),pp=max(yy)-min(yy))

def sustained_entry(t,y,lower,upper,after=0):
    """Earliest sampled in-band time after the last out-of-band sample.

    Conservative sampling bound; returns None if final point is out of band.
    A finite trace cannot establish indefinite future regulation.
    """
    if not lower<=y[-1]<=upper: return None
    bad=[i for i,(x,v) in enumerate(zip(t,y)) if x>=after and not lower<=v<=upper]
    i=bad[-1]+1 if bad else bisect.bisect_left(t,after)
    return t[i] if i<len(t) else None

def review(path, output='v(hv)', current='i(lpower)', steady_start=None):
    c=read_native(path); t=c['time']; v=c[output.lower()]
    start=steady_start if steady_start is not None else .8*t[-1]
    steady=stats(t,v,start,t[-1]); entry=sustained_entry(t,v,164.9,175.1)
    initial=v[0]; end=t[-1]
    result=dict(source=str(Path(path).resolve()),samples=len(t),initial_V=initial,endpoint_s=end,
        steady_window_s=[start,end],steady_V=steady,whole_trace_peak_V=max(v),sustained_entry_s=entry,
        assertions={'Cout_initial_0V':abs(initial)<1e-6,'normal_mean':164.9<=steady['mean']<=175.1,
            'ripple':steady['pp']<=1,'normal_peak':max(v)<=180,'startup':entry is not None and entry<=1},
        limitations=['Netlist/controller provenance and absence of forced PWM require separate review.',
            'No load/input disturbance, hot magnetics or specified fault coverage inferred from nominal trace.',
            'Ripple is unfiltered raw peak-to-peak; no invented 20MHz instrument filter.'])
    if current.lower() in c:
        il=c[current.lower()]
        result['inductor_A']=dict(minimum=min(il),maximum=max(il),negative_samples=sum(x<-.001 for x in il))
    result['evaluation_status']='LIMITED_PASS' if all(result['assertions'].values()) else 'ELECTRICAL_FAIL'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('raw');p.add_argument('--output',default='v(hv)');p.add_argument('--current',default='i(lpower)');p.add_argument('--steady-start',type=float);p.add_argument('--json')
    a=p.parse_args(); r=review(a.raw,a.output,a.current,a.steady_start)
    s=json.dumps(r,indent=2)+'\n'
    if a.json: Path(a.json).write_text(s,encoding='utf8')
    print(s)
