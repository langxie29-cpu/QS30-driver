# R11 5 V 升压仿真

使用 KiCad 自带 ngspice‑46 实际执行 25 个命名工况，22 个生成完整波形。另留存标称代理首次超时的重试记录。标准仿真时窗 30 ms，母线、电容、功率域从零开始。参考母线筛选窗 165–175 V、末段纹波 ≤1 V，为本轮诊断指标。生产公差与启动时限待定。 [资格矩阵](POWER_QUALIFICATION_MATRIX.csv) · [模型映射](SCHEMATIC_TO_SIMULATION_MAP.csv)

标称代理 5 V、7.65 mA 得 169.809 V 稳态平均、170.641 V 峰值、0.133112 Vpp 纹波。在 18.6304 ms 首次超过 161.5 V。L3 峰值 1.73528 A，Q32 峰值 VDS 171.858 V，二极管最大反向电压由原始波形算得 171.257 V，C47 电流 RMS 78.1 mA。输入 1 ms 后峰值约 1.650 A。初次接通出现理想输入开关造成的虚高冲击电流，必须用实际 eFuse dV/dt 和输入阻抗模型补算。标称 MOS、二极管、电感铜损与采样电阻末段平均约 123、5.88、12.8、15.8 mW。 [标称原始测量](evidence/r2/nominal/measurement.json) · [波形复算](evidence/r2/nominal/waveform_metrics.json)

| 条件 | 末段平均 | 结果 |
| --- | ---: | --- |
| 5 V，9.9 mA | 169.813 V | LIMITED_PASS，代理 |
| 4.4 V，9.9 mA | 150.736 V | REWORK，纹波 1.648 Vpp，低线掉出调节 |
| 5.5 V，7.65 mA | 169.794 V | LIMITED_PASS，出现 1.75726 A 最大电感峰值 |
| 空载 / 轻载 | 169.846 / 169.783 V | LIMITED_PASS，保留双泄放 |
| 负载阶跃 / 输入变化 | 169.804 / 169.802 V | LIMITED_PASS，末段恢复，输入变化期间的边界需继续审查 |
| 关断、重启 | 132.878 V | REWORK，30 ms 记录内未恢复。模拟 ARM 边界，无真实再授权逻辑 |
| 原理图 DNP R40 开路 | 约 0 V | LIMITED_PASS，仅对开路代理及所建路径成立 |

取得 TI 的 LM5155-Q1 Rev. H 原包，记录 ZIP 和库散列。未修改的库遇到嵌套 COMP 初值解析失败。只处理该初值语句后的 UIC 尝试遇到约 2 ns 时间步发散，零直流偏置的非 UIC 运行超时。闭环有效证据来自电流模式控制器代理，模拟保留 22 µH、50 mΩ、100 kHz、分压、补偿、软启动、门驱供应与高压储能拓扑。它无法关闭 LM5155 资格。TPS61040、UCC27511、ES1G、STD13N60M2、eFuse 及保护器件采用明确代理。负载以三管电流与简化熄灭电压替代。C47 串联 25 mΩ 为代理。 [TI 瞬态模型](https://www.ti.com/lit/mo/snvmbl2h/snvmbl2h.zip) · [兼容性和运行日志](evidence/r2)

R4 对假定的 10 nH、50 nH 开关支路敏感度分别得 175.385 V 和 251.15 V VDS。HV_ISENSE 铜线累计超过 100 mm，SW_HV 仍有两项未连接，完整开关回路面积与反馈 Kelvin 束无法由本稿提取。50 nH 假设下的峰值是全组最高，开关峰值和 EMI 仍需布局闭合后的实际提取及器件模型交叉审查。表列各器件电流、电压、功耗与模型边界。 [应力表](COMPONENT_STRESS_REVIEW.csv)

本机完整 RAW 位于本项目的 `evidence/r2/<case>/waveform.raw`，共 22 个，约 3.80 GB。每个路径的散列在相邻 `measurement.json`。Git 含每次运行的网表、日志、测量、指标和 CSV 波形抽样。TI 模型从原网站按散列取回，Git 中没有厂商库或大 RAW。部分日志中的 d_vr 测量宏缺少保存向量，已从同批原始二极管端电压复算。 [复现](REPRODUCE.md)
