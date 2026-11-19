# 分立 R8 复现

从 R7 `bfaa22d1080544b754c8809873c136ee7247688a` 的独立 `nxt/nxt-m3-5v-discrete-cathode-r8` 工作树进入 `projects/NXT-M3/r8`。Python 3.11+ 仅用标准库。

~~~powershell
python -m unittest -v
python orchestrate.py
python gate0_screen.py
python verify_offline.py
~~~

`gate0_screen.py` 从冻结预注册文件生成两个独立参数扫描、逐条件指标、R7 管座抽取映射、静态功率边界和 1/3/5/10 套报价投影。两个扫描均为解析计算。保留已封存结果时可在新工作树单独复现。四路资格判定为 NOT_ENTERED，三管映射为草案。源文档版本、来源、原始 PDF 和参考文件 SHA-256 见 [来源清单](evidence/source_manifest.json)，当地源文件可从固定 URL 取回。版权和元件模型许可未明的源文件可依散列核对。

编排器支持验证后的外部审查 checkpoint。原生 dsh 的 `--dump-config` 返回 YAML，已在隔离环境确认实际模型 ID。需要局部受控 host 回执供调度器核对限制范围、工具与请求次数，仅在显式授权后使用 `--live --accept-model-costs --external-decisions --run-id live-...`。本机当前原生入口的配置目录存在依赖链接冲突，隔离启动解决了只读检查，受控 live host 尚未验证。外部 Codex 审查要求 OpenAI/`gpt-6.1-sol`、原始证据与 audit SHA 绑定、独立审查说明，并经 `gate_decisions` 明确放行。G0 唯一许可状态为 ACCEPT_CANDIDATE，G1/G2 最低 LIMITED_PASS。技术 HOLD 或失败保持原日志和散列。

~~~powershell
python orchestrate.py --doctor --dsh D:/path/node.exe D:/path/dsh/lib/bin.js
python orchestrate.py --live --accept-model-costs --external-decisions --run-id live-discrete-01 --dsh D:/path/verified-host.exe
python orchestrate.py --live --accept-model-costs --external-decisions --run-id live-discrete-01 --resume --decision D:/path/decision.json --review D:/path/review.json --dsh D:/path/verified-host.exe
~~~

原有工作流及 R7 文件保留。恢复检查 Git HEAD、模型身份、控制文件与历史证据散列，断点回到已验证任务。实物高压、采购、PCB、Gerber 和放行均受 ENGINEERING HOLD 约束。
