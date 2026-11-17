# R2 模型与资格边界

原模型始终保持原字节，所有原生运行在执行前与 R1 登记 SHA 比对。主研究路线保持 **LT3757A + LTspice 24.0.12.0 / Normal solver**，没有新的控制器选型循环。完整 SHA、网表、选项、最大步长、执行预算和路径逐项在每例 `preregister.json`。

| 对象 | 原件 SHA256 | 本轮采信范围 / 缺口 |
|---|---|---|
| LT3757A.sub | `c03284243ac3b8e500e5bed3696deb8ebbde10eb8cb2a58b6e37929d9d18b634` | ADI 原生不透明模型，完整真实反馈与冷启动；不外推所有硅片阈值/延迟角点 |
| STP9NK50Z | `6ad61988b9e045684dc8271bc51ddfdca00d65b745e6edd6c4492a42df1ad7a4` | 原模型明确 25°C；内部 LG/LS/LD=7.5/7.5/4.5nH 已存在。本征节点与封装端区分。q:101 奇异矩阵失败保留；GHz 瞬态/热态/SOA 未获硬件资格 |
| US1G | `f8669a85e8f3ed412ba97ab72bc6b7b0facbdf57111187ede39a365801324ec3` | 原模型 TT=123.315ns，含结电容及 BV=400V；本轮直接观察反向恢复与雪崩样封装瞬态。未改 TT/BV；不把可重复模型峰值当成准确实物 Qrr/峰值 |
| SS14 负栅支路 | `3288afb62761edfc9e9095127e92e5f9d0e52cd79c1ec948db82bec9ed1f8ae2` | 原来源边界不提升；2Ω 阻尼支路不改。脉冲/温度/确切器件资格 HOLD |
| MSS1583-154KED | 无原厂热态 SPICE | 150µH、DCR .16Ω 线性研究模型；±10%冷态边界夹具不是 L(I,T)。25°C 降感 10/20/30% 对应 3.1/3.6/3.9A；Irms 20/40°C 温升 1.55/2.2A 不是热态绝对额定 |
| COUT 20.3µF / ESR .1Ω | 参数化研究夹具 | 两只主电容和模块等效；精确 MPN、ESR 频率/温度/偏压、寿命及容差 HOLD。不能把本轮 .091Vpp 直接当硬件纹波 |
| TPS26601RHFR U101 | PSpice库 `4403a72094d2b378e673bdaba4dc3851f54e82d08cbfffaf1d582ea65f8b4219`；TINA库 `70280bca6ced7970839a7393bf24182ef470e9b623316604f9479019b88f62cf` | 本轮重取 TI 当前发布包，SHA 与历史一致且仍加密。未在受支持原生环境回放；没有用理想钳流替代。MODE 开路是断路器锁存，不是持续限流。真实前级、RTN、关断最大延迟、SOA/热态 HOLD |
| 负载 | 原网表与新 BLOAD 明确登记 | RLOAD 5200Ω、10400Ω、1000Ω 均为等效电阻；并联双泄放与反馈保留。没有真实 QS30 起辉/保持/负阻/九管动态模型 |

LT 的默认电感损耗不能默认为零。原厂家内 LG/LS/LD 未给 Rser；[ADI 文档](https://analogdevicesinc.github.io/ltspice-reference/ai_ref/DEVICE-MODELS-GUIDE.html)说明默认 1mΩ 等引擎行为。本轮没有改写这些原模型或引擎阻尼来掩盖问题；理想 `.5Li²` 能量恒等式的剩余误差仍 INCONCLUSIVE，不能单凭它判定有源造能或证明硬件安全。

采样滤波选择依据为 [ADI LT3757/LT3757A 手册](https://www.analog.com/media/en/technical-documentation/data-sheets/LT3757-3757A.pdf) SENSE Programming：100ns 前沿消隐及 22Ω、2.2–10nF 研究范围；不是任意减小采样灵敏度。65µA 偏置为典型值，不能用其提前触发量抵消所有最坏传播/滤波延迟。实际 Kelvin、元件公差、热态及故障仍需资格化。

原厂程序、库和许可证保持本机，不随本目录重新分发。GitHub 附件只包含本轮产生的 raw 字节的可逆压缩分片；恢复 SHA 通过只证明字节完整，不代表电气合格。
