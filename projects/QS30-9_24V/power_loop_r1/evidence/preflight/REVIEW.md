# 本地预检与首轮启动

2026-11-17。独立worktree `D:/PROJECTS/dsharness/QS30-power-loop-r1`，分支 `nxt/qs30-power-loop-engineering-r1`，起点为用户指定调度器分支6be8cbbf。原QS30-1安全分支及其未提交S06C–F文件保留。

## 实证

- LTspice签名有效，签名主体Analog Devices International UC；文件/产品版本24.0.12.0。不能由旧目录名ltspice26推断26版。见相邻版本和签名JSON。
- NGspice47便携版存在且实际执行`--version`，原始输出同目录。Python3.11.15；数值/绘图Python为原工具目录review_venv。
- 当前Codex会话本地session_meta记录provider=openai，turn_context记录model=gpt-6.1-sol；全局配置model相同，无自定义provider或base_url。本会话直接作决策，子Codex调用为0。此为运行记录核验，不声称完成服务端密码学证明。
- 原DSH启动器仍硬编码迁移前D:/DeepSeekHarness；其原headless默认deepseek-v4-flash。原data/profiles/node_modules下非符号链接也使启动失败。未覆盖全局设置，改为本项目忽略目录中的独立DSH_HOME，原凭据仅私有复制，Node直接调用原安装CLI，专用overlay明确provider=deepseek-official、model=deepseek-flash、baseURL=https://api.deepseek.com。
- `dsh_runtime.json`从实际DSH压缩session的request/header提取指定字段。原session及配置/凭据不发布。子代理、ralph、workflow、goal和额外LLM标题被禁用；首次联调至多两轮、七个worker session，仍非货币/Token硬上限。

## 调度器修复

1. 将错误的`dsh headless prompt`修为文档支持的`--profile headless`，Windows直接Node argv避免陈旧cmd路径与shell拼接。
2. 从effective agent-default-model行精确验证模型和provider，拒绝仅在catalog中出现目标模型的假阳性。
3. 超时保留stdout/stderr部分数据；波形文件上限与控制台截断上限分开。
4. 当前Codex外部决策checkpoint/resume复用原目录与依赖审核，避免CLI递归；拒绝更改轮次/配置预算或自动第三轮。
5. 将真实控制器参考及非线性器件单元证据门槛补到zero_volt_startup；以前只对stage3检查。

离线回归见offline_tests.txt；全部为mock或解析算法测试，绝非电气PASS。首轮真实DSH已启动，调度成功本身不等于M1/M2/M3。安全H01–H10、24V-07/08/09/10和制造HOLD保持。

## 独立反例

第一worker将170V泄放单只90.9k耗散写为19.87mW，错误；直接计算(85V)^2/90.9k=79.483mW，四只和=317.932mW。原文件保留，不能采信其all_ok。

首轮context沿用safety文档5.88985W下界，但S06C的5.716423W预算实际按175.1V计算。不能把170V增量作为精确上限：175.1V增量=0.183993789W，合计5.900417172W。新独立计算记录两个电压基准并明确撤回混合电压结果作为精确预算的解释，未更改任何电气验收阈值。

官方配置语义：[OpenAI advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)。模型标识核验依据：[DeepSeek models API](https://api-docs.deepseek.com/api/list-models/)。
