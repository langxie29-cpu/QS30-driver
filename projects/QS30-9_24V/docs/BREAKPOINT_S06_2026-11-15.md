# 24V重构断点 — S06单元资格结束

2026-11-15，Asia/Shanghai。工作区`D:\PROJECTS\dsharness\QS30-1`，项目`projects\QS30-9_24V`，仍在历史分支`nxt/reva9-electrical-sprint03`；未commit/push/清理，继承脏工作区保留。

**当前门槛：24V-07未通过，08未进入，制造HOLD。** 下一轮读本断点和`docs/SPRINT06_REPORT.md`，不要只从S05断点恢复旧候选。

## 已执行，不需从头重做

- `docs/SPRINT06_PLAN.md`为执行前工作方案；`config/sprint06.json`为当前候选增量，继承S05系统要求。
- TI SLUM521未加密UCC28C43已取得并用原文件执行：振荡约115.3kHz、UVLO8.4/7.6V、CS半幅延迟约52ns；只在名义夹具中部分合格。
- 共25次仿真执行，含重复/修正夹具/负面对照/失败；22次到终点、3次执行失败，16次有限判据通过。矩阵`docs/sprint06/EXECUTION_MATRIX.csv`。
- CT并10k会停振；1M负载只提供输入阻抗/频率敏感性参考，不是实际缓冲器资格。
- 原22Ω直驱在64nC等效电容下约253–254ns关断到3V，超原170ns分配；新增UCC27511DBVR、RGON10Ω/RGOFF2.2Ω候选。
- 独立缓冲夹具部分约38–40ns，但1ns例崩溃；控制器+缓冲联接两例timestep-too-small。不能据部分通过标门驱已合格。
- 反馈重选上臂2×100k，下臂2.94k+45.3Ω、0.1%/25ppm。全温/偏流/温漂研究区间由旧161.66–178.38V改善至约165.25–174.77V；其它闭环误差仍待核。
- L20改候选MSS1583-154KED，150µH、25°C10%降感3.1A；热态资格未通过。300ns门驱分配下最迟峰流约1.502A；若要求20%热态余量需热态10%降感电流≥1.877A。
- 当前预算：HV侧约5.7156W，AUX99.096mA，整机约13.8628W/0.6418A@21.6V。原S05的13.664W属于旧候选历史结果。
- U110改候选LMR51610XFDBVR（400k FPWM），上143k+1k/下10k，目标12.32V；扣当前误差/纹波/路径分配后控制器偏置最低仅约12.018V，余量不足以直接宣告精度保证。
- TPS3700各轨PG、延时/复位与硬件许可已形成具体连接候选，见`docs/S06_CIRCUIT_DELTA.md`；仍未完成失电/反灌/半供电验证。
- 拒绝TPS3808G33复位候选（最坏释放3.194V高于最低3V3）；改TPS389001DSET、16.5k/10k、22n延时。静态阈值仅部分合格，下降下界3.008V到MCU3.0V仅约8mV，必须检查跌落/延迟。
- DRV启动不依赖自身PG；DRV_OK只在之后允许HV，避免启动死锁。FAULT_LATCH_OK/INTERLOCK_OK/HV_SAFE_ARMED来源未完成，保持默认不许可。
- USB离线编程目标保留；未配置100mA下启动/枚举尚未证明。22µF/800mA峰值研究例只支持约4.38µs，不能凭加电容宣布兼容。

## 首要阻塞与接续动作

1. **先解决模型联接/步长失败。** `sim/s06_buffered_gate_v1`在约20/46µs于`xu.gb6_int1`停止；rc0也必须算FAIL。`sim/s06_driver_unit_v1/11.4_switch_1ns`进程rc3221226356、无波形。分离模型兼容/仿真器问题，不放宽容差掩盖；失败目录保持只读。
2. **补真实功率器件与热态磁件。** ST原厂PDF/模型本地下载超时，仍无已运行ST MOS模型；Vishay整流恢复/Coss和磁件热态L(I)/磁损缺证。不要拿泛型开关/旧二极管模型当精确器件通过。
3. **做具体启动/跨模式策略。** 固定最坏CCM斜坡0.522V/µs会在约1.92µs耗尽1V CS量程，不能直接从CT注入后当统一控制方案；需受限启动、零流检测或模式相关控制和具体器件。无可信正常工作点不扫闭环。
4. **前级与PG掉电资格。** TPS26601原厂TINA/PSpice为加密库，未在ngspice完成动态/SOA；其原厂模型说明也不包含温度相关特性。完成RTN/SHDN、窗口/延时、半供电与快速跌落，再接完整保护。
5. **USB与5V故障。** 测/取得ESP32真实启动/枚举电流，确认端口能力和浪涌；处理24→5V反馈失效，继续保留USB目标。
6. 以上门槛满足才决定进入08，从0V自主启动；之后OVP/OC锁存/安全复位、泄放与拆模块单故障、原生图/ERC，PCB等待08/09/10/11。

## 证据与操作入口

- `docs/SPRINT06_REPORT.md`、`docs/S06_CIRCUIT_DELTA.md`、`config/sprint06.json`。
- `docs/sprint06/analysis.json`、`FEEDBACK_CORNERS.csv`、`PG_THRESHOLDS.csv`、`POWER_RAILS.csv`。
- `docs/sprint06/MODEL_QUALIFICATION.csv`、`EXECUTION_MATRIX.csv`、`final_verification.json`、`manifest_s06.json`。
- `sources/sprint06/`：原始ZIP/PDF、提取文件与所有下载manifest。SLUM521原文件不改；SLUM488只在运行目录副本补一个TABLE括号，diff留存。
- `sim/s06_controller_v1`、`s06_controller_v2`、`s06_gate_v3`、`s06_buffered_gate_v1`、`s06_driver_unit_v1`：原始夹具与失败证据，不覆盖。
- `netlist/s06_candidate_power_pins.csv`仍不是完整装配网表，`approved_for_native_generation=false`；PG连接见文档，不能自动当已审查网络导出。

从仓库根目录使用`tools/review_venv/Scripts/python.exe`，不要使用缺numpy的PATH中Espressif Python。复算为`design/sprint06_analysis.py`；新的单元试验用`design/sprint06_model_units.py --run 全新目录名`。`sprint06_sources.py`和固定目录驱动试验不可原地重跑；`sprint06_closeout.py`会改入口/任务证据，S05 finalize更会恢复旧状态，不能当纯只读检查器使用。

用户授权研究、选型与隔离仿真，不授权采购、制造包或实物高压上电。24V分别供170V与辅助降压；三片HV5622的DRV保持约12V，不批量EXT12→EXT24。原生连接只采用已审查候选；本轮原生图/ERC/DRC均未产生。旧HOLD/FAIL保持。

下一会话可直接发送：

> 
