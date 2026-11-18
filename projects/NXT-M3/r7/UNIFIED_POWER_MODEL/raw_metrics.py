"""Read declared LTspice transient points and compute time-weighted diagnostic metrics."""
import argparse
import bisect
from contextlib import contextmanager
import json
import math
import mmap
from pathlib import Path
import re
import struct


@contextmanager
def trace(path):
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        enc = "utf-16le" if raw[1:2] == b"\0" else "ascii"
        marker = "Binary:\n".encode(enc)
        location = raw.find(marker, 0, 65536)
        if location < 0:
            raise ValueError("No binary transient record")
        offset = location + len(marker)
        header = raw[:offset].decode(enc)
        names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+$", header, re.M)
        flags = re.search(r"^Flags:\s*([^\n]+)", header, re.M)[1].split()
        if "FastAccess" in flags or names[0] != "time" or "complex" in flags:
            raise ValueError("Unsupported raw layout")
        fmt = struct.Struct("<d" + ("d" if "double" in flags else "f") * (len(names) - 1))
        available = (len(raw) - offset) // fmt.size
        declared = int(re.search(r"No\. Points:\s*(\d+)", header)[1])
        if declared <= 0 or declared > available:
            raise ValueError(f"Invalid points: {declared} declared, {available} available")

        def datum(index):
            row = fmt.unpack_from(raw, offset + index * fmt.size)
            return (abs(row[0]), *row[1:])

        yield [name.lower() for name in names], datum, declared, available


def span(path):
    try:
        with trace(path) as (_, datum, declared, available):
            return dict(last_s=datum(declared-1)[0], points=declared, complete_records_present=available)
    except (ValueError, IndexError, AttributeError) as error:
        return dict(error=str(error))


def metrics(path, start, end):
    with trace(path) as (names, datum, n, _):
        if not datum(0)[0] <= start < end <= datum(n-1)[0]:
            raise ValueError("Requested window outside declared trace")
        a = bisect.bisect_left(range(n), start, key=lambda i: datum(i)[0])
        b = bisect.bisect_left(range(n), end, key=lambda i: datum(i)[0])
        idx = {name:i for i,name in enumerate(names)}
        wanted = {"hv_V":"v(hv)", "input_pin_V":"v(in)", "inductor_A":"i(lpower)",
                  "input_A":"i(vinput)", "pass_A":"i(vpasssense)",
                  "cap_A":"i(cout)", "diode_A":"i(drec)", "aux_V":"v(aux)"}
        transforms = {name: (lambda row, index=idx[signal], sign=-1 if name=="input_A" else 1: sign*row[index])
                      for name, signal in wanted.items() if signal in idx}
        for name, left, right in (("vds_V","v(sw)","v(src)"), ("vgs_V","v(gate)","v(src)"),
                                  ("diode_reverse_V","v(hv)","v(sw)")):
            if left in idx and right in idx:
                transforms[name] = lambda row, x=idx[left], y=idx[right]: row[x]-row[y]

        def at(time, index):
            right = datum(index)
            if time == right[0]:
                return right
            left = datum(index-1)
            weight = (time-left[0])/(right[0]-left[0])
            return (time, *(v+(w-v)*weight for v,w in zip(left[1:],right[1:])))

        first = at(start, a)
        last = at(end, b)
        last_t = start
        prev = [f(first) for f in transforms.values()]
        low, high = prev[:], prev[:]
        integral = [0.0]*len(prev)
        squares = integral[:]
        dt_min, fine, count = math.inf, 0, 0
        for index in range(a, b+1):
            row = last if index == b else datum(index)
            dt = row[0]-last_t
            if dt < 0:
                raise ValueError("Nonmonotonic timestamps")
            if dt:
                dt_min = min(dt_min, dt)
                fine += int(dt < 1e-9)
                count += 1
            values = [f(row) for f in transforms.values()]
            for j, (old, new) in enumerate(zip(prev, values)):
                integral[j] += dt*(old+new)/2
                squares[j] += dt*(old*old+old*new+new*new)/3
                low[j], high[j] = min(low[j], new), max(high[j], new)
            prev, last_t = values, row[0]
        return dict(start_s=start, end_s=end, intervals=count, dt_min_s=dt_min, steps_below_1ns=fine,
                    signals={key:dict(min=low[j], max=high[j], pp=high[j]-low[j],
                                      avg=integral[j]/(end-start), rms=(squares[j]/(end-start))**.5)
                             for j,key in enumerate(transforms)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("start", type=float)
    parser.add_argument("end", type=float)
    args = parser.parse_args()
    print(json.dumps(metrics(args.raw, args.start, args.end), indent=2))
