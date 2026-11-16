# 接手与证据范围

2026-11-17，Asia/Shanghai。仓库 langxie29-cpu/QS30-driver，工作基线 `nxt/reva9-electrical-sprint03`，HEAD `ee53f81c3f93539906445482bd17e564829338ef`；工作分支 `nxt/qs30-hv-safety-r1`。

接手存在README、project.json、TASKS.csv修改及大量S06C–F未跟踪成果；全部保留，不纳入本次提交。`git_before.txt`记录切换到工作分支后、开始设计时状态。`history_snapshot.json`记录3189个历史源文件SHA256；范围包括所有已跟踪文件及已有24V docs/config/design/sources，不包括未跟踪历史大波形。最终执行history_guard.py check检查此明确范围，不声称未哈希波形已做全字节核验。

已完整读取用户指定八文件及S06C–F报告；各角色进一步读原始结果。S06C后续存在LT3757A替代候选，因此不能假定S06 UCC方案仍为唯一有效功率基线。S06F仍未通过采样收敛与硬限流资格。旧12V过流采样、约0.79A锁存、复位及失电失败继续保留，未作为新实现复用。

角色A负责规格；B负责候选连接；D负责规格模型和低压SPICE；C在初稿完成后独立对抗审查，不参与初稿实现；E由主智能体独立文件审查PCB/制造。受同时运行槽数限制按先设计后审查串接C，未虚构五个同时运行的独立智能体。

保护逻辑模型通过、低压行为SPICE通过、厂商器件单元通过、完整硬件安全验证是四个不同层级。前两层不得关闭24V-07/08/09或制造HOLD。
