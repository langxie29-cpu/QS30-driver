# 电源架构对照

## P1 12 V 精化参考

原生 [KiCad 项目](NXT_M3_R7_EDA/NXT-M3.kicad_pro)，完整元件身份见 [BOM](FINAL_BOM.csv)。变更集中在已有分压的准确 MPN 和资格说明。前级 TPS26600RHFR、U2 3.3 V 预偏置、TMR 1-1212、LT3757AEMSE#PBF、UCC27511DBVR、STP9NK50Z、STPSC4H065D、MSS1583-154KED、TDK 5 µF 保留。U6 独立 OVP，经 U7/Q2 控制 U4、U5 与 U1，U8 承担上电置位。局部双泄放。模型入口 [P1](REFERENCE_POWER_DESIGN/)。

## P2 12 V 低成本 DCM 研究

保留共用板接口、前级 U1、3.3 V 预偏置、12 V 辅助轨、惰性分压和独立安全链。候选以 TPS40210DGQR 更换控制器、改变反馈至 2×100k/825Ω 研究值，SENSE 0.16Ω（候选 WSL2512R1600FEA），软启动 22nF、RC 187k/1nF、补偿 10k/22n/220p。主功率器件及三个管支路与 P1 同构。外围无完整可采购 MPN，DCM 工作区尚未由稳态波形确认。次候选 UCC28C43DR 在单元模型研究 UVLO、栅驱和限流，未完成整机控制与保护外围。 [可执行研究 deck](ALTERNATIVE_LTSPICE/) · [运行明细](SIMULATION_RESULTS.csv)

~~~mermaid
flowchart LR
    J["J1 10.8–13.2 V"] --> FU["F1 + D1 输入防护"]
    FU --> EF["U1 TPS26600 开断"]
    FU --> VDD["U2 3.3 V 预偏置"]
    EF --> L["L1 150 µH"]
    L --> SW["Q1 漏极 / D20 阳极"]
    SW --> D["D20 SiC"]
    D --> HV["C20 / HV170"]
    HV --> LOAD["三组阳极与 QS30-1 / HV5622；ADC 与双泄放"]
    EF --> AUX["U3 TMR 12 V"]
    AUX --> GD["UCC27511 / HV5622 / 电平移位"]
    EF --> P2["TPS40210（P2）"]
    HV --> P2
    P2 --> GD
    GD --> SW
    HV --> CMP["U6 独立 OVP → U7 故障锁存"]
    VDD --> CMP
    CMP --> EF
    CMP --> GD
    CMP --> P2
~~~

P2 的 DIS 为主动高，仿真使用明确标注的电平映射；实际器件电路需定义所有部分掉电时的安全电平，并保留独立输入切断。直驱是单独研究支路，必须证明 VGS、热、Miller 和故障抑制。引入 MOSFET 或吸收差异的成本不能并入 U4 单价收益。原模型的正常窗口及 P2 均以 165–175 V、≤2 Vpp、≤180 V、50ms 内过 160 V、故障 ≤195 V 为参考，模型外部保护和实际 2W 资格仍开。

## P3 24 V 对照

保留三个独立母线及同样三个显示模块。输入比对 21.6/24/26.4 V，前级只能重定 UVLO、OVP、TVS、反接及外部供电，不能沿用 R6 12 V 电阻和 TVS。12 V AUX 可研究 LMR51420XDDCR 降压，需为 36 V 工作额定核对输入瞬变钳位，3.3 V LDO 热负担需重新预算。此处完成 DCM、占空和输入平均电流计算，尚无 P3 对应的完整硬件图或闭环波形。 [24 V 角点](POWER_AND_LOAD_BUDGET.csv) · [TI](https://www.ti.com/product/LMR51420/part-details/LMR51420XDDCR)

量产 PCB 面积、板边接口、电源和装配均无报价。P1 同一参考占位，P2 SOIC 或 HVSSOP 及新增器件可能改变实际面积，直驱方案少一个 SOT-23，24 V 方案需另一套电源前级。 [成本](POWER_TOPOLOGY_COST_COMPARISON.csv) · [取舍](DESIGN_TRADEOFFS.md)
