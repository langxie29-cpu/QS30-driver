# -*- coding: utf-8 -*-
"""G1：机械参数化草案（OpenSCAD）+ M1/M2 比较 + 三位模块装配/布线 + 成本拆分 + E 复审。

输出：
  cad/QS30_DISPLAY_MODULE.scad     参数化 OpenSCAD（可编辑；未做 CAD 验证）
  cad/QS30_parameters.json         参数表（H03 实测后改这里即可重建）
  docs9/MECH9_G1.md                M1/M2 比较与推荐
  docs9/ASSEMBLY_WIRING9.md        三位模块装配与短布线规范
  docs9/COST9_SPLIT.md             MAIN/DISPLAY/机械/线束成本拆分
  docs9/E_REVIEW9.md               E01-E05 复审状态
运行：python design9/mech9.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC9 = os.path.join(ROOT, "docs9")
CAD = os.path.join(ROOT, "cad")
os.makedirs(DOC9, exist_ok=True)
os.makedirs(CAD, exist_ok=True)

PARAMS = {
    "tube_dia_mm": 30.2,          # QS30-1 外径（原厂资料）
    "tube_body_h_mm": 26.0,       # 管身高度（原厂 26±0.5）
    "tube_total_h_mm": 34.0,      # 总高（原厂 34±1.5）
    "socket_hole_dia_mm": None,   # H03 TBD
    "socket_pitch_mm": None,      # H03 TBD（管座中心距）
    "socket_body_mm": None,       # H03 TBD
    "tubes_per_module": 3,
    "panel_t_mm": 2.0,            # 面板厚度（假设，待结构确认）
    "pcb_t_mm": 1.6,
    "standoff_mm": 12.0,          # PCB-面板间距（可调）
    "pcb_w_mm": 100.0,            # DISPLAY 板框（初布局）
    "pcb_h_mm": 100.0,
    "mount_hole_dia_mm": 3.2,
    "status": "PROVISIONAL — socket_pitch/socket_body 待 H03 实测",
}


def scad():
    p = PARAMS
    return f"""// QS30-9 REV.A9 — 三位显示模块（方案 B：独立金属管座支架 + 背置驱动 PCB）
// 参数化 OpenSCAD；所有尺寸来自 cad/QS30_parameters.json，H03 实测后改参数即可重建。
// 状态：PROVISIONAL，未在 CAD 中打开验证；不得据此加工。
tube_dia = {p['tube_dia_mm']};
tube_h = {p['tube_total_h_mm']};
panel_t = {p['panel_t_mm']};
pcb_t = {p['pcb_t_mm']};
standoff = {p['standoff_mm']};
pcb_w = {p['pcb_w_mm']};
pcb_h = {p['pcb_h_mm']};
socket_pitch = 38;   // TBD：H03 实测前用 38 mm 占位（禁止用于加工）
module_w = socket_pitch * 2 + tube_dia + 20;

module tube(i) {{
  translate([i * socket_pitch, 0, panel_t + standoff])
    cylinder(d = tube_dia, h = tube_h, $fn = 64);
}}
module metal_bracket() {{
  // 金属承力支架（M1/M2 待定），仅示意：底部托板 + 两侧折边
  color("silver") difference() {{
    union() {{
      translate([-module_w/2, -40, 0]) cube([module_w, 80, 2]);
      translate([-module_w/2, -40, 0]) cube([2, 80, 40]);
      translate([module_w/2 - 2, -40, 0]) cube([2, 80, 40]);
    }}
    for (i = [-1, 0, 1]) translate([i * socket_pitch, 0, -1])
      cylinder(d = tube_dia + 4, h = 60, $fn = 64);
  }}
}}
module pcb() {{
  color("darkgreen") translate([-pcb_w/2, -pcb_h/2, -standoff - pcb_t])
    cube([pcb_w, pcb_h, pcb_t]);
}}
module module_3tube() {{
  metal_bracket();
  for (i = [-1, 0, 1]) tube(i);
  pcb();
}}
module_3tube();
"""


def main():
    open(os.path.join(CAD, "QS30_parameters.json"), "w", encoding="utf-8").write(
        json.dumps(PARAMS, ensure_ascii=False, indent=1))
    open(os.path.join(CAD, "QS30_DISPLAY_MODULE.scad"), "w", encoding="utf-8").write(scad())

    mech = """# M1/M2 机械方案比较（方案 B 已锁定）

方案 B = 独立金属管座支架 + 背置小型驱动 PCB。二手六位管座组件（约 15 元/六位，
两组约 30 元，用户提供，未验证适配性）计划拆用 9 只、留 3 只备用。

| 比较项 | M1 保留金属排架、切割/重打孔成三位 | M2 拆独立管座、装定制金属支架 |
|---|---|---|
| 可拆卸性 | 差：切割后整体刚性/孔位改变，单管不可独立拆 | 好：单管座独立固定，可单独更换 |
| 切割与强度 | 需切 2 处、补强；折边可能失效 | 无需切割，支架按 3 孔设计 |
| 螺孔/尺寸 | 依赖原件孔位，可能无法三等分 | 可按实测孔距重新设计 |
| 中心距 | 由原件孔位决定（不可控） | 由支架设计决定（需 H03 得管座外形） |
| 装配精度 | 切割公差累积，重复性差 | 定位销/基准孔，重复性好 |
| 表面处理 | 切割面需打磨防锈 | 新支架可统一喷涂/阳极氧化 |
| 成本 | 低（复用原件） | 中（3 支架 + 加工） |
| 安全绝缘 | 切割边缘毛刺易划伤线束 | 可做圆角/绝缘衬垫 |
| 维修 | 拆整组 | 单管更换 |

**推荐：M2（拆独立管座 + 定制支架）**，仅在"原件螺孔恰好可三等分且切割成本极低"
时才退回 M1。两者都必须等 H03 实测管座外形/孔距后冻结。

## 参数化模型
- `cad/QS30_DISPLAY_MODULE.scad`（OpenSCAD，文本可编辑，参数集中）；
- `cad/QS30_parameters.json`（H03 实测后改此文件重建）；
- 未做 CAD 内核验证，PROVISIONAL，禁止据此加工。

## 待实测（H03）
管座外形/螺孔位置/孔径、管座安装面到焊脚高度、管体到管座间隙、13 脚中心圆直径、
管座与 PCB 的固定方式、金属件厚度。上述任一项缺失 → 参数保持 TBD。
"""
    open(os.path.join(DOC9, "MECH9_G1.md"), "w", encoding="utf-8").write(mech)

    wire = """# 三位模块装配与短布线规范（方案 B）

## 1. 电气连接数量（每模块）
- 3 只 QS30-1 × (1 阳极 + 10 阴极) = **33 路**；其中阴极 30 路、阳极 3 路；
- 9 位总计 **99 路**（90 阴极 + 9 阳极）；
- QS30-1 的 1、8 脚**不连接**（原厂内部电极）；
- 模块对主板：LV 16P（3V3/GND/DRV_VDD/DIN/DOUT/CLK/LAT/BL/SAFETY×2）+ HV 2P。

## 2. 降低布线成本与错误率的措施（推荐顺序）
1. **PCB 贴背安装**：驱动 PCB 用 4 个 M3 铜柱固定在金属支架背面，管座焊脚朝 PCB，
   走线长度最短；PCB 与金属支架之间加绝缘垫（≥1 mm，材料待定）。
2. **适配转接板（可选）**：若管座焊脚排列与 PCB 焊盘无法直接对齐，做一块 1.6 mm
   转接小板把 13 脚转成 2.54 mm 排针/焊盘，再由短排线接驱动板；转接板必须固定，
   不允许悬空走线。
3. **编号线束**：单根 13 芯排线（或 11 芯有效）按管号编号（T1/T2/T3），
   两端压接/焊接后用热缩管+编号套管；线束用线夹固定在支架上，不承力。
4. **避免可触及高压焊点**：所有 HV 焊点/端子加绝缘罩，HV 线束与 LV 线束分槽走线，
   间距按 H07 定稿后的规则执行（当前 1.0 mm 仅为占位，不是安全值）。
5. **可检查/可替换**：每个模块的 33 路焊点可单独测量；预留阴极测试点（每管 10 个）。

## 3. 装配顺序
1. 金属支架定位 → 装 3 只管座 → 检查 13 脚通断（万用表逐脚）；
2. 装绝缘柱 → 固定驱动 PCB → 目视检查焊脚与 PCB 间距/绝缘；
3. 焊接/压接短排线（编号）→ 逐路导通与绝缘测试（LV 仅 3.3 V 测试）；
4. 模块单独上低压（3.3 V/12 V，不接 HV）验证移位/锁存/消隐；
5. HV 接入前必须通过 G2 低压测试与 H06 高压台架。

## 4. 禁止
- 不得用普通杜邦线/裸排线承载 172 V；
- 不得在未验证额定值的连接器上接 HV；
- 不得带电插拔模块（当前不支持热插拔）。
"""
    open(os.path.join(DOC9, "ASSEMBLY_WIRING9.md"), "w", encoding="utf-8").write(wire)

    cost = """# 成本拆分（MAIN / DISPLAY / 机械 / 线束）

> 只有 HV5622 有用户零售报价（32.15 元/颗，UNVERIFIED）；其余价格 UNKNOWN，**不估算、不编造**。
> 9 只 QS30-1 为已有库存（历史 160 元），不计入本次现金支出。

| 项目 | 数量 | 已知价格 | 状态 |
|---|---|---|---|
| MAIN 板 BOM（ESP32-S3/电源/升压/OVP/中心 3 位驱动） | 1 块 | UNKNOWN | 询价 |
| DISPLAY 板 BOM（HV5622×1 + 3 管座接口 + 阳极电阻 + 连接器） | 2 块 | HV5622 2×32.15=64.30 元（UNVERIFIED） | 其余询价 |
| 中心模块 HV5622 | 1 颗 | 32.15 元（UNVERIFIED） | — |
| 六位管座组件（拆 9 用 3 备） | 2 组 | 30 元（用户提供，未验证适配性） | — |
| 金属支架（三位 ×3，M2 定制） | 3 套 | UNKNOWN | 待 H03 后加工报价 |
| 低压线束/连接器（LV 16P×2 套 + 板端） | 2 套 | UNKNOWN | 询价 |
| HV 连接器+线束（≥300 V DC，H9-07） | 2 套 | UNKNOWN | 选型后询价 |
| PCB 打样（MAIN 120×90 + DISPLAY 100×100×2） | 3 块 | UNKNOWN | 询价（可拼板） |
| 整机总成本 | — | **无法给出** | 需完成询价 |

## 省钱来源（真实可解释）
1. 左右 DISPLAY 同板（2 块共用同一 Gerber/BOM）→ 摊薄打样与备料；
2. 管座与 PCB 分离（方案 B）→ DISPLAY 板可做小，不再为 3×Φ30.2 管体让出整板面积；
3. 3×HV5622 替代 90 路分立 → 焊点/面积/维修成本显著下降（见 DRIVER_COMPARE.md）；
4. 二手六位管座拆用 → 9 只座约 30 元（未验证），比单独采购 13 脚管座可能更省，但需 H03 确认。
"""
    open(os.path.join(DOC9, "COST9_SPLIT.md"), "w", encoding="utf-8").write(cost)

    erev = """# E01–E05 电气复审状态（G1）

| 编号 | 问题 | 本轮复审结论 | 证据等级 | 状态 |
|---|---|---|---|---|
| E01 | 比较器共模 | U8/U11 均 3.3 V 供电、基准 1.0 V（≤VCC−2=1.3 V 全温区）；U23 OVP 用 EXT12 供电、2.5 V 基准在 0…10 V 内。需核对**上电瞬间**输入未建立时的输出状态（目前仅设计分析）。 | STRONGLY SUPPORTED（手册+计算） | 待实测 |
| E02 | OVP 比较器+分立锁存 | 纸面偏置推导极性正确（过压→OUT 低→R45 拉低 LATCH_B→PNP 通→NPN 锁存→Q23 拉低 COMP）。**BJT 级 SPICE 尝试失败**（自研 PNP 模型未收敛，已回滚并记录 I9-03）；未用 ngspice/LTspice 验证，保持 HOLD。 | STRONGLY SUPPORTED（纸面） | **HOLD** |
| E03 | OVP 阈值与峰值 | 分压理论触发 198.8 V；1% 电阻+0.5% 基准+Vos worst-case 192.9–204.1 V；比较器切换门槛/传输延迟/关断后峰值**未实测**，不得把 192.5–204.5 V 当作安全放行窗口。 | PROVISIONAL | **HOLD** |
| E04 | 高压泄放 | 总电容 20 µF（主板，另模块各 0.1 µF）；主板 200 kΩ + 每模块 200 kΩ；172→100 V 由 9 管电流主导、100→50 V 由泄放主导，计算共 ≈0.76 s；**无主动泄放**；静态功耗 172²/50k ≈0.59 W 分布于 4 个 200 kΩ（各约 0.15 W）；断电后**必须实测电压**再接触，禁止按计算值直接触摸。 | PROVISIONAL | **HOLD** |
| E05 | DRV_PG/使能/断连 | 逻辑包含 DRV_PG·FAULT_OK·SAFETY_OK·HV_EN_REQ；断连通过 SAFETY_LOOP 断开 HV_EN。上电顺序/掉电/单模块短路/MCU 复位**未实测**；保护验证前不得整机高压调试。 | PROVISIONAL | **HOLD** |

**结论**：E02–E05 保持 HOLD，需 ngspice/LTspice 或实物台架；本轮不把任何一项标为 VERIFIED。
"""
    open(os.path.join(DOC9, "E_REVIEW9.md"), "w", encoding="utf-8").write(erev)
    print("wrote cad/QS30_DISPLAY_MODULE.scad + cad/QS30_parameters.json")
    print("wrote docs9/MECH9_G1.md, ASSEMBLY_WIRING9.md, COST9_SPLIT.md, E_REVIEW9.md")


if __name__ == "__main__":
    main()
