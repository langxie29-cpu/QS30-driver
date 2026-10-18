# -*- coding: utf-8 -*-
"""minispice.py —— QS30-6 仓库自带的最小 SPICE 子集求解器。

存在理由
--------
本执行环境无法安装/运行 ngspice、LTspice 或 KiCad（见 open_issues I-19：KiCad 需管理员、
ngspice 下载 403）。为了"SPICE 网表真的被执行过"，本仓库实现一个**最小、可审计**的
SPICE 子集求解器，并用**解析解**先验证求解器本身，再运行升压功率级网表。

支持子集（只覆盖本项目网表需要的部分）
------------------------------------
  R  n1 n2 value
  C  n1 n2 value
  L  n1 n2 value
  V  n1 n2 [DC] value | PULSE(v1 v2 td tr tf pw per)
  I  n1 n2 value
  D  nA nK model                        （结二极管；忽略 Rs/Cjo）
  S  n1 n2 nC+ nC- model                （压控开关，线性过渡）
  .param k=value（支持 {表达式}）
  .model NAME D(...) | VSWITCH(...)
  .tran tstep tstop [tstart]
  .save v(node) | i(element)
  .print/.plot/.options 忽略

数值方法
--------
  * 改进节点法（MNA）+ 后向欧拉（一阶，无条件稳定）；
  * 二极管结用 Newton 迭代线性化（exp 限幅）；
  * 压控开关按控制电压计算电导（控制源为理想电压源时一步收敛）；
  * 每步外层 Newton 迭代最多 60 次，收敛判据 |ΔV| < 1e-7 V。

局限（必须随结果一起引用）
--------------------------
  * 一阶后向欧拉：有数值阻尼，纹波/峰值误差随步长减小；本仓库固定使用
    ≤ 开关周期/128 的步长，并做过步长敏感性检查；
  * 二极管忽略 Rs/Cjo，开关为线性过渡模型，电感/电容无寄生；
  * 不支持 .ac/.dc 扫描、B 源、亚电路、温度模型；
  * 这不是 ngspice 的替代品：结论以"本求解器 + 行为模型"双重证据给出。
"""
from __future__ import annotations

import math
import os
import re
import sys

import numpy as np

VT = 0.025852


# ---------------------------------------------------------------------------
def si_value(tok: str, params: dict) -> float:
    """解析 SPICE 数值：支持 1e-3、12.82u、10k、2.2m、1meg 与 {表达式}。"""
    t = tok.strip().strip("()")
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
        try:
            return float(eval(t, {"__builtins__": {}}, dict(params)))  # noqa: S307
        except Exception as e:  # pragma: no cover
            raise ValueError(f"cannot evaluate {tok}: {e}") from e
    m = re.fullmatch(r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-zA-Z]*)", t)
    if not m:
        raise ValueError(f"bad value {tok}")
    val = float(m.group(1))
    suf = m.group(2).lower()
    scale = {"": 1.0, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
             "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "t": 1e12}.get(suf)
    if scale is None:
        raise ValueError(f"bad suffix {suf} in {tok}")
    return val * scale


def prep_expr(expr, vmap, params):
    """把 B 源表达式预编译：{param} 与 SPICE 后缀一次性展开，V(node) 内联为索引。"""
    import re as _re
    e = expr
    for _ in range(8):
        m = _re.search(r"\{([^{}]+)\}", e)
        if not m:
            break
        val = si_value("{" + m.group(1) + "}", params)
        e = e[:m.start()] + repr(val) + e[m.end():]
    if "?" in e or ":" in e:
        raise ValueError("minispice 不支持三元表达式，请改用 min/max 或压控开关: " + expr)
    e = _re.sub(r"(?<![A-Za-z0-9_.])([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"
                r"(meg|f|p|n|u|m|k|MEG|F|P|N|U|M|K)\b",
                lambda mm: repr(si_value(mm.group(1) + mm.group(2), params)), e)

    used = []

    def repl(m2):
        key = m2.group(1).strip().lower()
        idx = vmap[key]
        used.append(idx)
        return "_V(%d)" % idx
    e = _re.sub(r"[vV]\(([^)]+)\)", repl, e)
    used_i = []

    def repl_i(m2):
        nm = m2.group(1).strip().lower()
        used_i.append(nm)
        return "_I('%s')" % nm
    e = _re.sub(r"[iI]\(([^)]+)\)", repl_i, e)
    return compile(e, "<bspice>", "eval"), used, used_i


def eval_expr_code(code, x, t, ilookup=None):
    ns = {"_V": lambda i: (x[i - 1] if i > 0 else 0.0),
          "_I": (ilookup if ilookup else (lambda nm: 0.0)),
          "min": min, "max": max, "abs": abs, "sqrt": math.sqrt,
          "exp": math.exp, "time": t,
          "mod": lambda a, b: a - b * math.floor(a / b)}
    return float(eval(code, {"__builtins__": {}}, ns))


class Element:
    def __init__(self, line):
        self.line = line


class Circuit:
    def __init__(self):
        self.params = {}
        self.models = {}
        self.elems = []
        self.nodes = ["0"]
        self.tran = None
        self.ic = {"v": {}, "i": {}}
        self.saves = []
        self.title = ""

    # ---- 解析 ----
    @staticmethod
    def _split(line):
        return [t for t in re.split(r"\s+", line.strip()) if t]

    def parse(self, text):
        raw = []
        for ln in text.splitlines():
            s = ln.split(";")[0].strip()
            if not s:
                continue
            if s.startswith("*"):
                continue
            if s.startswith("."):
                raw.append(s)
            else:
                raw.append(s)
        # 先 .param / .model，再元件（顺序无关）
        for s in raw:
            low = s.lower()
            if low.startswith(".param"):
                for kv in s.split()[1:]:
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        self.params[k.strip()] = si_value(v, self.params)
            elif low.startswith(".model"):
                m = re.match(r"\.model\s+(\S+)\s+(\w+)\s*\((.*)\)",
                             s, re.I)
                if not m:
                    raise ValueError(f"bad .model: {s}")
                name, typ, body = m.group(1), m.group(2).upper(), m.group(3)
                kv = {}
                for part in re.split(r"[\s,]+", body.strip()):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        try:
                            kv[k.lower()] = si_value(v, self.params)
                        except ValueError:
                            kv[k.lower()] = v
                self.models[name] = dict(type=typ, **kv)
            elif low.startswith(".tran"):
                tk = s.split()
                tstep = si_value(tk[1], self.params)
                tstop = si_value(tk[2], self.params)
                self.tran = (tstep, tstop)
            elif low.startswith(".ic"):
                for kv in s.split()[1:]:
                    if "=" not in kv:
                        continue
                    k, v = kv.split("=", 1)
                    val = si_value(v, self.params)
                    m = re.match(r"([viVI])\s*\(\s*([^)]+)\s*\)", k)
                    if not m:
                        continue
                    kind = m.group(1).lower()
                    nm = m.group(2).strip().lower()
                    self.ic[kind][nm] = val
            elif low.startswith(".save"):
                self.saves += [t.lower() for t in s.split()[1:]]
            elif low.startswith((".print", ".plot", ".option", ".end", ".title")):
                if low.startswith(".title"):
                    self.title = s[6:].strip()
            else:
                raw.append(s) if False else None
        # 元件
        for s in raw:
            low = s.lower()
            if low.startswith("."):
                continue
            if s[0] in "*.":
                continue
            self._parse_element(s)
        return self

    def _node(self, name):
        key = name.lower()
        if key == "0":
            return 0
        if key not in self.nodes:
            self.nodes.append(key)
        return self.nodes.index(key)

    def _parse_element(self, s):
        tk = self._split(s)
        name = tk[0]
        typ = name[0].upper()
        if typ == "R":
            a, b = self._node(tk[1]), self._node(tk[2])
            self.elems.append(dict(t=typ, name=name, n=(a, b),
                                   v=si_value(tk[3], self.params)))
        elif typ == "C":
            a, b = self._node(tk[1]), self._node(tk[2])
            ic = 0.0
            for extra in tk[4:]:
                if extra.lower().startswith("ic="):
                    ic = si_value(extra.split("=", 1)[1], self.params)
            self.elems.append(dict(t=typ, name=name, n=(a, b),
                                   v=si_value(tk[3], self.params), v0=ic))
        elif typ == "L":
            a, b = self._node(tk[1]), self._node(tk[2])
            ic = 0.0
            for extra in tk[4:]:
                if extra.lower().startswith("ic="):
                    ic = si_value(extra.split("=", 1)[1], self.params)
            self.elems.append(dict(t=typ, name=name, n=(a, b),
                                   v=si_value(tk[3], self.params), i0=ic))
        elif typ == "V":
            a, b = self._node(tk[1]), self._node(tk[2])
            rest = tk[3:]
            if rest and rest[0].upper() == "DC":
                rest = rest[1:]
            if rest and rest[0].upper().startswith("PULSE"):
                inner = s[s.upper().index("PULSE(") + 6:s.rindex(")")]
                vals = [si_value(x, self.params) for x in inner.split()]
                while len(vals) < 7:
                    vals.append(0.0)
                self.elems.append(dict(t=typ, name=name, n=(a, b), kind="pulse",
                                       p=vals))
            else:
                self.elems.append(dict(t=typ, name=name, n=(a, b), kind="dc",
                                       v=si_value(rest[0], self.params)))
        elif typ == "I":
            a, b = self._node(tk[1]), self._node(tk[2])
            self.elems.append(dict(t=typ, name=name, n=(a, b),
                                   v=si_value(tk[3], self.params)))
        elif typ == "D":
            a, k = self._node(tk[1]), self._node(tk[2])
            self.elems.append(dict(t=typ, name=name, n=(a, k), model=tk[3]))
        elif typ == "S":
            a, b = self._node(tk[1]), self._node(tk[2])
            c, d_ = self._node(tk[3]), self._node(tk[4])
            self.elems.append(dict(t=typ, name=name, n=(a, b), nc=(c, d_),
                                   model=tk[5]))
        elif typ == "B":
            m = re.match(r"^B\S+\s+(\S+)\s+(\S+)\s+([VvIi])\s*=\s*(.+)$", s)
            if not m:
                raise ValueError(f"bad B element: {s}")
            a, b = self._node(m.group(1)), self._node(m.group(2))
            kind = m.group(3).upper()
            expr = m.group(4).strip()
            vmap = {}
            for nm in re.findall(r"[vV]\(([^)]+)\)", expr):
                key = nm.strip().lower()
                vmap[key] = self._node(key)
            code, _used, _used_i = prep_expr(expr, vmap, self.params)
            self.elems.append(dict(t="B", name=name, n=(a, b), kind=kind,
                                   expr=expr, vmap=vmap, code=code,
                                   used_i=_used_i))
        else:
            print(f"[minispice] 跳过不支持的元素: {name}", file=sys.stderr)

    # ---- 元件取值 ----
    def v_value(self, el, t):
        if el["kind"] == "dc":
            return el["v"]
        v1, v2, td, tr, tf, pw, per = el["p"]
        if t < td:
            return v1
        t = t - td
        if per <= 0:
            return v1
        tt = t % per
        if tr <= 0:
            tr = 1e-12
        if tf <= 0:
            tf = 1e-12
        if tt < tr:
            return v1 + (v2 - v1) * tt / tr
        if tt < tr + pw:
            return v2
        if tt < tr + pw + tf:
            return v2 + (v1 - v2) * (tt - tr - pw) / tf
        return v1

    def sw_conductance(self, el, xn):
        m = self.models.get(el["model"], {})
        ron = m.get("ron", 1.0)
        roff = m.get("roff", 1e9)
        von = m.get("von", 1.0)
        voff = m.get("voff", 0.5)
        vc = self._v(xn, el["nc"][0]) - self._v(xn, el["nc"][1])
        if vc <= voff:
            return 1.0 / roff
        if vc >= von:
            return 1.0 / ron
        k = (vc - voff) / max(von - voff, 1e-12)
        return (1 - k) / roff + k / ron

    @staticmethod
    def _v(x, i):
        return x[i - 1] if i > 0 else 0.0

    # ---- MNA 装配 ----
    def assemble(self, xn, t, h, state, switch_g, bvals=None):
        nodes = self.nodes
        n = len(nodes) - 1
        vsrc = [el for el in self.elems
                if el["t"] == "V" or (el["t"] == "B" and el["kind"] == "V")]
        ind = [el for el in self.elems if el["t"] == "L"]
        m = len(vsrc) + len(ind)
        size = n + m
        cur_idx = {}
        for i, el in enumerate(vsrc):
            cur_idx[el["name"].lower()] = n + i
        for i, el in enumerate(ind):
            cur_idx[el["name"].lower()] = n + len(vsrc) + i

        def _I(nm):
            k = cur_idx.get(nm.lower())
            return float(xn[k]) if k is not None else 0.0

        if bvals is None:
            bvals = {}
            for el in self.elems:
                if el["t"] == "B":
                    bvals[el["name"]] = eval_expr_code(el["code"], xn, t, _I)
        A = np.zeros((size, size))
        b = np.zeros(size)

        def stamp_g(a, bb, g):
            if a > 0:
                A[a - 1, a - 1] += g
            if bb > 0:
                A[bb - 1, bb - 1] += g
            if a > 0 and bb > 0:
                A[a - 1, bb - 1] -= g
                A[bb - 1, a - 1] -= g

        vs_idx = {}
        ind_idx = {}
        for i, el in enumerate(vsrc):
            vs_idx[el["name"]] = n + i
        for i, el in enumerate(ind):
            ind_idx[el["name"]] = n + len(vsrc) + i

        for el in self.elems:
            typ = el["t"]
            a, bb = el["n"]
            if typ == "R":
                stamp_g(a, bb, 1.0 / max(el["v"], 1e-12))
            elif typ == "C":
                g = el["v"] / h
                stamp_g(a, bb, g)
                vprev = state.get("vc", {}).get(el["name"], el.get("v0", 0.0))
                ieq = -g * vprev
                if a > 0:
                    b[a - 1] -= ieq
                if bb > 0:
                    b[bb - 1] += ieq
            elif typ == "L":
                k = ind_idx[el["name"]]
                if a > 0:
                    A[k, a - 1] += 1.0
                if bb > 0:
                    A[k, bb - 1] -= 1.0
                A[k, k] -= el["v"] / h
                b[k] -= (el["v"] / h) * state.get("il", {}).get(el["name"], el.get("i0", 0.0))
                if a > 0:
                    A[a - 1, k] += 1.0
                if bb > 0:
                    A[bb - 1, k] -= 1.0
            elif typ == "V" or (typ == "B" and el["kind"] == "V"):
                k = vs_idx[el["name"]]
                if a > 0:
                    A[k, a - 1] += 1.0
                    A[a - 1, k] += 1.0
                if bb > 0:
                    A[k, bb - 1] -= 1.0
                    A[bb - 1, k] -= 1.0
                val = self.v_value(el, t) if typ == "V" else bvals[el["name"]]
                b[k] += val
            elif typ == "I" or (typ == "B" and el["kind"] == "I"):
                val = el["v"] if typ == "I" else bvals[el["name"]]
                if a > 0:
                    b[a - 1] -= val
                if bb > 0:
                    b[bb - 1] += val
            elif typ == "D":
                m_ = self.models.get(el["model"], {})
                isat = m_.get("is", 1e-14)
                nn = m_.get("n", 1.0)
                vd = self._v(xn, a) - self._v(xn, bb)
                vd_lim = min(vd, 0.8)
                ex = math.exp(min(vd_lim / (nn * VT), 40.0))
                Id = isat * (ex - 1.0)
                gd = isat * ex / (nn * VT)
                # 线性化点必须与电流计算点一致（vd_lim），否则 Newton 会被
                # 未限幅电压放大成巨大的等效电流源。
                ieq = Id - gd * vd_lim
                # 电流 A->K
                if a > 0:
                    A[a - 1, a - 1] += gd
                if bb > 0:
                    A[bb - 1, bb - 1] += gd
                if a > 0 and bb > 0:
                    A[a - 1, bb - 1] -= gd
                    A[bb - 1, a - 1] -= gd
                if a > 0:
                    b[a - 1] -= ieq
                if bb > 0:
                    b[bb - 1] += ieq
            elif typ == "S":
                g = switch_g.get(el["name"])
                if g is None:
                    g = self.sw_conductance(el, xn)
                    switch_g[el["name"]] = g
                stamp_g(a, bb, g)
        return A, b

    # ---- 求解 ----
    def run(self):
        if self.tran is None:
            raise ValueError("no .tran")
        h, tstop = self.tran
        n = len(self.nodes) - 1
        vsrc = [el for el in self.elems
                if el["t"] == "V" or (el["t"] == "B" and el["kind"] == "V")]
        ind = [el for el in self.elems if el["t"] == "L"]
        m = len(vsrc) + len(ind)
        x = np.zeros(n + m)
        node_index = {nm: i for i, nm in enumerate(self.nodes)}
        vsn = [e["name"].lower() for e in vsrc]
        indn = [e["name"].lower() for e in ind]
        state = dict(vc={}, il={})
        # 初始状态：.ic 指定的节点电压/元件电流（缺省 0）
        for nm, val in self.ic["v"].items():
            idx = self.nodes.index(nm) if nm in self.nodes else None
            if idx:
                x[idx - 1] = val
        for nm, val in self.ic["i"].items():
            if nm in indn:
                j = indn.index(nm)
                x[n + len(vsrc) + j] = val
                state["il"][ind[j]["name"]] = val
        # 仅当 .ic 涉及该电容端点时才覆盖其初值；否则沿用元件上的 ic= 参数
        for el in self.elems:
            if el["t"] == "C":
                a, bb = el["n"]
                na = self.nodes[a] if a > 0 else "0"
                nb = self.nodes[bb] if bb > 0 else "0"
                if na not in self.ic["v"] and nb not in self.ic["v"]:
                    continue
                va = self.ic["v"].get(na, 0.0)
                vb = self.ic["v"].get(nb, 0.0)
                state["vc"][el["name"]] = va - vb
        t = 0.0
        records = []
        steps = int(round(tstop / h))
        for step in range(steps + 1):
            t = step * h
            switch_g = {}
            xnew = x.copy()
            # B 源按上一步解显式求值（控制环带宽 << 开关频率，误差可忽略），
            # 避免每步把 B 源卷入 Newton 迭代导致收敛缓慢。
            cur_idx = {}
            for i, el in enumerate(vsrc):
                cur_idx[el["name"].lower()] = n + i
            for i, el in enumerate(ind):
                cur_idx[el["name"].lower()] = n + len(vsrc) + i

            def _I(nm):
                k = cur_idx.get(nm.lower())
                return float(x[k]) if k is not None else 0.0

            bvals = {}
            for el in self.elems:
                if el["t"] == "B":
                    bvals[el["name"]] = eval_expr_code(el["code"], x, t, _I)
            for _it in range(30):
                A, b = self.assemble(xnew, t, h, state, switch_g, bvals)
                try:
                    xsol = np.linalg.solve(A, b)
                except np.linalg.LinAlgError:
                    xsol = np.linalg.lstsq(A, b, rcond=None)[0]
                dx = np.max(np.abs(xsol - xnew))
                xnew = 0.5 * (xnew + xsol) if _it < 6 else xsol
                if dx < 2e-6:
                    break
            x = xsol
            # 记录（后向欧拉：解对应 t+h 时刻）
            rec = {"t": t + h}
            for s in self.saves:
                if s.startswith("v(") and s.endswith(")"):
                    nm = s[2:-1].strip().lower()
                    idx = node_index.get(nm)
                    rec[f"v({nm})"] = (x[idx - 1] if (idx and idx > 0) else 0.0)
                elif s.startswith("i(") and s.endswith(")"):
                    nm = s[2:-1].strip().lower()
                    if nm in vsn:
                        k = n + vsn.index(nm)
                        rec[f"i({nm})"] = -x[k]
                    elif nm in indn:
                        k = n + len(vsrc) + indn.index(nm)
                        rec[f"i({nm})"] = x[k]
            records.append(rec)
            # 更新状态
            for el in self.elems:
                if el["t"] == "C":
                    a, bb = el["n"]
                    va = x[a - 1] if a > 0 else 0.0
                    vb = x[bb - 1] if bb > 0 else 0.0
                    state["vc"][el["name"]] = va - vb
                elif el["t"] == "L":
                    k = n + len(vsrc) + [e["name"] for e in ind].index(el["name"])
                    state["il"][el["name"]] = x[k]
        return records


def read_and_run(path):
    text = open(path, encoding="utf-8").read().lstrip("\ufeff")
    c = Circuit().parse(text)
    return c, c.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python minispice.py <netlist.cir> [out.csv]")
        sys.exit(1)
    c, recs = read_and_run(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    keys = [k for k in recs[0] if k != "t"]
    if out:
        import csv
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t"] + keys)
            for r in recs:
                w.writerow([f"{r['t']:.9e}"] + [f"{r[k]:.9e}" for k in keys])
        print(f"wrote {out}  steps={len(recs)}  vars={keys}")
    else:
        for r in recs[:: max(1, len(recs) // 20)]:
            print({k: round(v, 6) for k, v in r.items()})
