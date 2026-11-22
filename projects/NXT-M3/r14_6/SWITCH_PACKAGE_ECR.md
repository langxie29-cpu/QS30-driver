# 开关节点封装 ECR

SW_HV / SNUB 继续使用 **3.20 mm** 原生筛查。重复峰值、地弹及关断过冲均为 **UNKNOWN**。逐对的原生对象、网络和尺寸见 [SWITCH_PACKAGE_CLEARANCE.csv](SWITCH_PACKAGE_CLEARANCE.csv)。

| 器件 | 修改与状态 | 后续资格 |
| --- | --- | --- |
| C48 | KEMET C2220C101JDGACTU，100 pF、±5%、C0G、1 kVDC。取消 1206 通用封装，使用 C1009 表 3 的 2220 median land。每焊盘 1.50 × 5.40 mm，中心距 5.30 mm，铜距 3.80 mm，庭院 7.30 × 5.90 mm。B.Cu (172.50, 101.00) mm、270°。C48 和 R86 保留 DNP。 | 两端已接回，原 1.80 mm 违规消除。测定有效电容、脉冲电流、焊料外缘、使用温度和工作峰值，再决定装配。 [KEMET C1009 表 3](https://www.mouser.com/datasheet/3/508/1/KEM_C1009_C0G_HV_SMD.pdf) · [精确料号](https://no.farnell.com/kemet/c2220c101jdgactu/cap-100pf-1kv-mlcc-2220/dp/3505448) |
| D3 | Diodes ES1G-13-F、SMA。400 V 重复反压、1 A 的表列条件、25 ns 规定工况恢复时间。原厂 pad 建议内边距约 1.50 mm。原生净距保留 HOLD。 | 候选 onsemi MUR160G 为轴向、600 V/1 A。原厂应用笔记给出的恢复时间 75 ns，与现用 25 ns 的测试条件需对齐。展开引脚的实际铜距和回路需独立核对。更换前须核实反压裕量、峰值/平均电流、反向恢复电荷、温升和回流环路。D3.1→C47.1 仍开路。 [Diodes ES1G，第 2、4 页](https://www.diodes.com/datasheet/download/ES1G.pdf) · [onsemi 轴向候选](https://www.onsemi.com/download/application-notes/pdf/and8226-d.pdf) |
| Q32 | ST STD13N60M2，DPAK，漏极 2/热片，栅 1、源 3。原生漏极到栅/源两项保留 HOLD。 | 对照原厂 Fig. 21 再评估分离引脚的 STW26N60M2 TO-247 候选。候选的漏极还连金属背板。孔周焊盘、引脚展开、板外净空、驱动能力、Qg/Coss、装配热阻与启动/故障 SOA 需要独立核验。 [现用 ST DPAK 第 12 页](https://www.st.com/resource/en/datasheet/std13n60m2.pdf) · [ST TO-247 候选](https://www.st.com/resource/en/datasheet/stw26n60m2.pdf) |

C48 与 R86.2 的 SNUB 新铜约 14.14 mm，C48.2→R79.2 的 GND 新铜约 12.17 mm，均为背层且无新增换层。吸收回路同时包含 R86.1→开关节点和实际功率地回路，新增长度会改变脉冲环路电感，故保持 DNP。下一候选应同时规划 Q32→D3→C47 的高频回流和吸收件紧凑摆位。电阻脉冲能量采用实测开关波形积分，电容损耗、二极管反向恢复与 MOSFET SOA 用同一工况复核。母线 170/195 V 的直流筛查无法确定重复峰值。
