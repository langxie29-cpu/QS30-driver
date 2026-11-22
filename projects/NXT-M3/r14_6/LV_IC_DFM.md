# 低压 IC 净距与制造资格

原生 34 个同封装铜对逐项保存在 [LV_IC_CLEARANCE_QUALIFICATION.csv](LV_IC_CLEARANCE_QUALIFICATION.csv)。U6、U13、U14 共 18 对按 TI DGK0008A 进行焊盘整改。中心行距由 4.225 变为 4.40 mm，焊盘由 1.625 × 0.50 变为 1.40 × 0.45 mm，0.65 mm 节距保持。U14.3、U14.4、U14.6 三处旧铜入口随新焊盘延长。18 个旧错误在当前规则下消除，选择器件与装配电压资格仍开放。U1/U11 的 16 个 RPW0010A 违规继续保留。无规则例外。 [TI TCA9517A](https://www.ti.com/lit/ds/symlink/tca9517a.pdf) · [TI TLV1702](https://www.ti.com/lit/ds/symlink/tlv1701.pdf) · [TI TPS25947](https://www.ti.com/lit/ds/symlink/tps25947.pdf)

候选 JLCPCB 公示 1 oz 多层板最小线距 0.09 mm。公示 1 oz 阻焊桥 0.10 mm，部分颜色的最小焊盘间距 0.13 mm，2 oz 最小焊盘间距 0.20 mm。公示能力提供初筛，实际板的铜重、局部蚀刻公差、阻焊注册、桥宽、RPW 中央大焊盘钢网开口和贴装偏差须书面审核。TI RPW 推荐 0.10 mm 钢网及不同开口比例，DGK 用独立 VSSOP 钢网图。验收需包含对应样片的桥连、润湿和尺寸记录。 [JLCPCB 原厂工艺能力](https://jlcpcb.com/capabilities/pcb-capabilities/) · [贴装能力](https://jlcpcb.com/capabilities/pcb-assembly-capabilities)

U13 的 OVP 和 U14 的残压输入来自母线分压。假定正确装配且忽略输入钳位，U14.2 在 170/195 V 约为 3.869/4.438 V，3.3 V 供电时实际输入可能受钳位。合理下臂开路会留下高阻母线源，关断回灌、失供极限、响应准确性及钳位寿命未证明。U1/U11 取 5.25 V 正常筛查包络，U6 取 3.3 V 逻辑包络，均保留启动、关断与故障未知项，真实峰值不能由台账的名义电压推出。
