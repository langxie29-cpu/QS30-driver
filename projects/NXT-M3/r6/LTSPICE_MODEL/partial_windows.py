"""Extract descriptive metrics from native raw files that terminated before their registered windows."""
import csv
import mmap
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
WINDOWS = {
    'p1c_full': (.035, .037),
    'surrogate_nominal': (.045, .055),
    'surrogate_low_line': (.045, .055),
    'surrogate_high_line': (.045, .055),
}

def parse(path, start, end):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        encoding = 'utf-16le' if raw[1:2] == b'\x00' else 'ascii'
        marker = 'Binary:\n'.encode(encoding)
        header_end = raw.find(marker,0,8192)+len(marker)
        header = raw[:header_end].decode(encoding)
        names = re.findall(r'^\s*\d+\s+(\S+)\s+\S+$',header,re.M)
        count = len(names)
        uniform_double = 'double' in re.search(r'Flags:\s*([^\n]+)',header)[1]
        sample = struct.Struct('<d'+('d' if uniform_double else 'f')*(count-1))
        n = int(re.search(r'No\. Points:\s*(\d+)',header)[1])
        assert 0 < n <= (len(raw)-header_end)//sample.size
        assert names[0] == 'time' and n>0
        def datum(i):
            row=sample.unpack_from(raw,header_end+i*sample.size)
            # LTspice stores flagged timesteps with negative time; axis uses magnitude.
            return (abs(row[0]),*row[1:])
        def lower_bound(time):
            low,high=0,n
            while low<high:
                mid=(low+high)//2
                if datum(mid)[0]<time:
                    low=mid+1
                else:
                    high=mid
            return low
        first, last=lower_bound(start),lower_bound(end)
        if last==n or first==0:
            raise ValueError(f'Window outside declared native records: {path}')
        channels = [names.index(name) for name in
                    ('V(hv)','V(gate)','V(src)','V(sw)','I(Lpower)','I(Drec)','I(Cout)','I(Vinput)','V(pwm)')]
        def transformed(d):
            hv,gate,source,sw,coil,diode,cap,supply,pwm=(d[k] for k in channels)
            return [hv,gate-source,sw-source,hv-sw,coil,diode,cap*cap,-supply,pwm]
        def between(a,b,t):
            fraction=(t-a[0])/(b[0]-a[0])
            return [t,*(x+(y-x)*fraction for x,y in zip(a[1:],b[1:]))]
        point = between(datum(first-1),datum(first),start) if datum(first)[0]>start else datum(first)
        finish = between(datum(last-1),datum(last),end) if datum(last)[0]>end else datum(last)
        prev = transformed(point)
        times = []
        integrated = [0.0]*8
        minimum = prev[:]
        maximum = prev[:]
        timestamp = start
        for index in range(first,last+1):
            p = finish if index==last else datum(index)
            v = transformed(p)
            width = p[0]-timestamp
            assert width >= 0, 'Time axis is not monotonic'
            for j in range(8):
                integrated[j] += (prev[j]+v[j])*width/2
                minimum[j] = min(minimum[j],v[j])
                maximum[j] = max(maximum[j],v[j])
            if prev[-1] < 3 <= v[-1]:
                times.append(p[0])
            prev,timestamp = v,p[0]
        scale=end-start
        return dict(start_s=start,end_s=end,samples=last-first,hv_avg_V=integrated[0]/scale,
                    hv_pp_V=maximum[0]-minimum[0],peak_IL_A=maximum[4],min_IL_A=minimum[4],
                    peak_VDS_V=maximum[2],min_VGS_V=minimum[1],max_VGS_V=maximum[1],
                    peak_diode_reverse_V=maximum[3],peak_diode_forward_A=maximum[5],
                    cap_RMS_A=(integrated[6]/scale)**.5,input_mean_A=integrated[7]/scale,
                    pwm_rising_Hz=(len(times)-1)/(times[-1]-times[0]) if len(times)>1 else None)

def main():
    out=HERE.parent/'evidence'/'partial_window_metrics.csv'
    rows=[]
    for name,(start,end) in WINDOWS.items():
        rows.append(dict(run=name,**parse(HERE/'runs'/name/'boost.raw',start,end),
                         scope='Post hoc description; original window incomplete'))
    with out.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

if __name__=='__main__':
    main()
