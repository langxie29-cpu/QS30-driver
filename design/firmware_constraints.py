# -*- coding: utf-8 -*-
"""生成固件约束清单（从设计数据库派生，不手写 GPIO/网络名）。

输出：
  docs/firmware_constraints.md   人读约束清单（H06/固件交接用）
  docs/firmware_constraints.json 机读（固件仓库可直接消费）
并校验：所有引用的网络名必须存在于 netlist/QS30-6_REV.A_netlist.csv，否则退出码 2。

运行：python design/firmware_constraints.py
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs")
NETLIST = os.path.join(ROOT, "netlist", "QS30-6_REV.A_netlist.csv")
MAPPING = os.path.join(DOC, "channel_mapping.csv")

# 固件关心的网络（名字必须在网表中存在，脚本会校验）
FW_NETS = ["HV_EN_REQ", "HV_EN", "FAULT_OK", "DRV_BL", "DRV_DIN", "DRV_CLK",
           "DRV_LAT", "DISP_ALLOW", "OVP_RST", "HV_SENSE_ADC", "DRV_VDD_EN",
           "EXT12_PG", "P3V3_PG", "DRV_PG"]


def _netlist():
    with open(NETLIST, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


_NL = _netlist()
PIN_NAME = {(r["ref"], r["pin"]): r["pin_name"] for r in _NL if r["pin_name"]}


def net_pins(net):
    return [f"{r['ref']}.{r['pin']}" for r in _NL if r["net"] == net]


def pin_label(ref_pin):
    ref, _, pin = ref_pin.partition(".")
    n = PIN_NAME.get((ref, pin), "")
    return f"{ref}.{pin}" + (f"（{n}）" if n else "")


def main():
    sys.path.insert(0, os.path.join(ROOT, "design"))
    import sheet_lv, sheet_hv
    sheet_lv.build()
    sheet_hv.build()

    rows = []
    with open(MAPPING, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # 1) MCU 侧控制引脚（MCU 网络 → ESP32 引脚；经 CD40109B 后为 DRV_*）
    MCU_SIDE = {"DRV_DIN": "DISP_DIN", "DRV_CLK": "DISP_CLK",
                "DRV_LAT": "DISP_LAT", "DRV_BL": "DISP_ALLOW"}
    ctrl = {}
    for drv, mcu_net in MCU_SIDE.items():
        pins = [p for p in net_pins(mcu_net) if p.startswith("U10.")]
        ctrl[f"{mcu_net} → {drv}"] = pin_label(pins[0]) if pins else None
    for net in ("HV_EN_REQ", "OVP_RST", "HV_SENSE_ADC", "HVF_NODE"):
        pins = [p for p in net_pins(net) if p.startswith("U10.")]
        ctrl[net] = pin_label(pins[0]) if pins else None
    # 2) 帧/位序（以映射表为准：64 位中 60 路已用、4 路备用）
    bit_vals = sorted({int(r["serial_bit_index"]) for r in rows})
    devices = sorted({r["driver"] for r in rows})
    used = sum(1 for r in rows if r["status"].startswith("PROVISIONAL"))
    frame = dict(bits=bit_vals[-1] + 1, n_devices=len(devices), devices=devices,
                 bit_order="MSB-first（bit63 先发），ch → bit = 63-ch（H04 待实测确认）",
                 used_channels=used, spare_channels=len(rows) - used)
    # 3) 约束项
    constraints = [
        dict(id="F01", title="帧长度 64 位", value="64",
             detail="2×HV5622（32 位/片），60 路已用、4 路备用；不得按 96 位或 60 位发送"),
        dict(id="F02", title="位序", value="MSB-first，bit=63-ch",
             detail="PROVISIONAL：必须由 B3 walking-one 实测回填 docs/channel_mapping.csv 后冻结"),
        dict(id="F03", title="SPI 时钟", value="≤200 kHz，起始 100 kHz",
             detail="CD40109B 电平转换 + 长线；先 100 kHz 验证，逐级提高"),
        dict(id="F04", title="时钟/锁存极性", value="CLK 下降沿移位；LE 高装载",
             detail="对应 HV5622 真值表（S15）；POL 硬接 DRV_VDD，固件不得控制 POL"),
        dict(id="F05", title="消隐", value="MCU DISP_ALLOW(IO15) → CD40109B → DRV_BL；BL=0 → 全关",
             detail="更新序列：BL=0 → 移位 → LE 脉冲 → BL=1；DRV_BL 有 10 kΩ 下拉，复位期间为安全态"),
        dict(id="F06", title="上电顺序依赖", value="HV_EN_REQ 只在自检通过后置 1",
             detail="HV_EN = DRV_PG·FAULT_OK·HV_EN_REQ；DRV_VDD_EN = EXT12_PG·3V3_PG·HV_EN_REQ；"
                    "HV_EN_REQ/DISP_ALLOW 均有下拉，复位期间不得为高"),
        dict(id="F07", title="故障响应", value="HVF_NODE 高 → 锁存故障；FAULT_OK=0 → 硬件立即关 HV",
             detail="HVF_NODE 经 R31/R32/C29/D7/D8 到 U8 比较器与 MCU IO7；固件读 IO7 判故障，不得自动反复复位"),
        dict(id="F08", title="OVP 复位", value="脉宽 ≥0.2 ms，且仅当 HV<198.8 V",
             detail="OVP 有效时复位无效（等价 SCR 不可关断）；建议先读 HV_SENSE_ADC 确认 <190 V 再复位"),
        dict(id="F09", title="USB-only 供电", value="总电流 ≤500 mA",
             detail="USB-C 默认电流；固件应在仅 USB 供电时禁止点亮或大幅降占空比"),
        dict(id="F10", title="显示范围", value="000000–999999，静态驱动",
             detail="每管恒有 1 路阴极导通，无扫描；六位数字分别对应 J_T1..J_T6"),
        dict(id="F13", title="备用通道", value="ch60–63 不使用（NC），发送时填 0",
             detail="映射表 64 行中 60 路接 QS30-1、4 路预留；帧仍需发满 64 位"),
        dict(id="F11", title="恢复通道", value="USB 原生下载 + UART0",
             detail="Boot/复位时序见测试计划 A4/A5；TXD0 无过冲"),
        dict(id="F12", title="版本与位序冻结", value="映射表 + 固件 LUT 同一版本号",
             detail="H04 通过后同时冻结 docs/channel_mapping.csv 与固件 LUT 哈希"),
    ]

    # 校验网络存在
    missing = [n for n in FW_NETS if not net_pins(n)]
    if missing:
        print("固件约束引用了网表中不存在的网络:", missing)
        sys.exit(2)

    md = ["# 固件约束清单（从设计数据库派生）", "",
          "由 `design/firmware_constraints.py` 自动生成；网络名/GPIO 从 "
          "`netlist/QS30-6_REV.A_netlist.csv` 与 `docs/channel_mapping.csv` 反查。", "",
          "## 控制引脚（ESP32-S3 侧）", "",
          "| 网络 | ESP32 引脚 |", "|---|---|"]
    for k, v in ctrl.items():
        md.append(f"| {k} | {v or '未找到'} |")
    md += ["", "## 帧与位序", "",
           f"- 帧长 **{frame['bits']} bit**（{frame['n_devices']}×HV5622，器件 {', '.join(frame['devices'])}）",
           f"- 已用通道 **{frame['used_channels']}** 路；位序：{frame['bit_order']}", "",
           "## 约束项", "",
           "| 编号 | 约束 | 值 | 说明 |", "|---|---|---|---|"]
    for c in constraints:
        md.append(f"| {c['id']} | {c['title']} | {c['value']} | {c['detail']} |")
    md += ["", "## 与设计/HOLD 的对应", "",
           "- F05/F06 对应 `design_decisions.md` 门控与下拉设计（ER-14/ER-16）；",
           "- F08 对应 `docs/ovp_timing.md`（复位脉宽 ≥0.2 ms、仅 HV<阈值）；",
           "- F02 冻结依赖 H04（walking-one）；F09 依赖 H05（USB 电流实测）；",
           "- 本清单不替代固件测试计划（`docs/test_plan.md` 阶段 A/B/E）。"]
    open(os.path.join(DOC, "firmware_constraints.md"), "w",
         encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(dict(control_pins=ctrl, frame=frame, constraints=constraints,
                   networks=FW_NETS),
              open(os.path.join(DOC, "firmware_constraints.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"firmware constraints: {len(constraints)} 项，控制引脚 {len(ctrl)} 个，"
          f"帧 {frame['bits']} bit / {frame['used_channels']} 通道")
    print("wrote docs/firmware_constraints.md/.json")


if __name__ == "__main__":
    main()
