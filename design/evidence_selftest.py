# -*- coding: utf-8 -*-
"""证据校验框架自测：用**合成数据**验证 evidence_check 的判据逻辑是否有效。

注意：本脚本生成的是**合成测试数据**，仅用于验证校验器本身；不代表任何实物测试。
它不会写入 docs/evidence（真实证据目录），只在临时目录中操作。

输出：docs/evidence_selftest.md
运行：python design/evidence_selftest.py
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "docs", "evidence")
DOC = os.path.join(ROOT, "docs")


def read_rows(p):
    with open(p, encoding="utf-8-sig") as f:
        r = csv.reader(f)
        rows = list(r)
    return rows[0], rows[1:]


def write_rows(p, header, rows):
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def fill_ok(tmp):
    """把模板填成合法值（合成）。"""
    h, rows = read_rows(os.path.join(tmp, "H02_tube_pin_test.csv"))
    for r in rows:
        r[4] = r[3]           # glow = expect
        r[5] = "2.3"
    write_rows(os.path.join(tmp, "H02_tube_pin_test.csv"), h, rows)

    h, rows = read_rows(os.path.join(tmp, "H02_tube_operating_point.csv"))
    for i, r in enumerate(rows):
        r[1] = f"photo_T{i+1}.jpg"
        r[2], r[3], r[4], r[5] = "140", "102", "126", "2.36"
        r[6], r[7] = "ok", "tester"
    write_rows(os.path.join(tmp, "H02_tube_operating_point.csv"), h, rows)

    h, rows = read_rows(os.path.join(tmp, "H03_socket_measurement.csv"))
    for r in rows:
        for j in (2, 3, 4):
            r[j] = "12.30"
    write_rows(os.path.join(tmp, "H03_socket_measurement.csv"), h, rows)
    h, rows = read_rows(os.path.join(tmp, "H03_socket_views.csv"))
    for r in rows:
        r[2], r[3], r[4] = "top", "notch at 12 o'clock", "view.jpg"
    write_rows(os.path.join(tmp, "H03_socket_views.csv"), h, rows)
    h, rows = read_rows(os.path.join(tmp, "H03_socket_continuity.csv"))
    for r in rows:
        r[1], r[2], r[3] = r[0], "Y", "no"
    write_rows(os.path.join(tmp, "H03_socket_continuity.csv"), h, rows)

    h, rows = read_rows(os.path.join(tmp, "H04_walking_one.csv"))
    for r in rows:
        r[8], r[9] = r[6], r[7]      # observed = expected
    write_rows(os.path.join(tmp, "H04_walking_one.csv"), h, rows)

    for name in ("H05_power.csv", "H06_hv.csv"):
        h, rows = read_rows(os.path.join(tmp, name))
        for r in rows:
            lo, hi = float(r[4]), float(r[5])
            r[2] = f"{(lo + hi) / 2:.4g}"
        write_rows(os.path.join(tmp, name), h, rows)

    h, rows = read_rows(os.path.join(tmp, "H07_spacing.csv"))
    for r in rows:
        r[2] = str(float(r[3]) + 1.0)
        r[5] = "Y"
    write_rows(os.path.join(tmp, "H07_spacing.csv"), h, rows)

    h, rows = read_rows(os.path.join(tmp, "H08_rf.csv"))
    for r in rows:
        r[1], r[2], r[3], r[4] = "-52", "25", "2.0", "10"
    write_rows(os.path.join(tmp, "H08_rf.csv"), h, rows)


def run_check(evdir, outdir):
    env = dict(os.environ)
    env["QS30_EVIDENCE_DIR"] = evdir
    env["QS30_DOC_DIR"] = outdir
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, os.path.join(ROOT, "design",
                                                    "evidence_check.py")],
                       capture_output=True, text=True, env=env, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="qs30_ev_")
    ev = os.path.join(tmp, "evidence")
    out = os.path.join(tmp, "out")
    os.makedirs(ev)
    os.makedirs(out)
    for f in os.listdir(EV):
        if f.endswith(".csv"):
            shutil.copy(os.path.join(EV, f), os.path.join(ev, f))

    lines = ["# 证据校验框架自测（合成数据）", "",
             "> 本文件由 `design/evidence_selftest.py` 生成。所用数据为**合成数据**，"
             "唯一目的是证明校验器能识别「未提交/部分/完整/失败」四种状态，"
             "**不代表实物测试结果**。", ""]

    # 1) 未提交
    rc, log = run_check(ev, out)
    lines += ["## 1. 模板原样（未提交）", "", f"- 退出码：{rc}（期望 0，无失败项）"]
    lines.append("- 结论：" + ("正确识别为未提交" if rc == 0 else "异常"))

    # 2) 全部合法填写
    fill_ok(ev)
    rc, log = run_check(ev, out)
    lines += ["", "## 2. 合成数据全部合法", "",
              f"- 退出码：{rc}（期望 0）"]
    ok = "已提交·判据通过" in log and rc == 0
    lines.append("- 结论：" + ("7 项 HOLD 均判为已提交且通过" if ok else "异常！"))

    # 3) 注入非法值（OVP 超范围、H04 位序错、H02 发光错误）
    p = os.path.join(ev, "H06_hv.csv")
    h, rows = read_rows(p)
    for r in rows:
        if r[0] == "C5-OVPtrip":
            r[2] = "215"       # 超出 197.3..200.3
    write_rows(p, h, rows)
    p = os.path.join(ev, "H04_walking_one.csv")
    h, rows = read_rows(p)
    rows[0][8], rows[0][9] = "J_T2", "3"   # 故意错一位
    write_rows(p, h, rows)
    p = os.path.join(ev, "H02_tube_pin_test.csv")
    h, rows = read_rows(p)
    rows[0][4] = "Y" if rows[0][4] == "N" else "N"   # 故意反一个
    write_rows(p, h, rows)
    rc, log = run_check(ev, out)
    caught = ("判据失败" in log) and rc == 2
    lines += ["", "## 3. 注入 3 处非法值", "",
              f"- 退出码：{rc}（期望 2）",
              f"- 结论：{'校验器成功捕获（H02/H04/H06 判据失败）' if caught else '异常：未捕获！'}",
              "", "### 校验器输出摘录", "", "```", log.strip()[:1500], "```"]

    shutil.rmtree(tmp, ignore_errors=True)
    open(os.path.join(DOC, "evidence_selftest.md"), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    sys.exit(0 if (rc == 2 and caught) else 2)


if __name__ == "__main__":
    main()
