# Give this to your coding agent / 复制给AI的启动提示

Replace the local clone path and credential path yourself. Do not put the actual API key in the prompt.

```text
请接手这个仓库。先读根目录 README.md、AGENTS.md、docs/PROJECT_STATUS.md 和 docs/workflow/SHORT_RULES.md。
我克隆的位置：<本机仓库绝对路径>。
我的 API 文件位置：<仓库外 JSON/dotenv 文件绝对路径>；只允许运行时读取，不把内容写入聊天、提示词、日志或Git。

先检查已有 Python/Git；不要自动安装、认证或重跑历史科学实验。
先运行 doctor、基础设施测试、三节点 offline 示例和第二次恢复，确认是真实执行而非口头通过。
若我要试真实工作流，复制 workflow.local.example.json 到被忽略的 workflow.local.json，选择新的 run_dir，检查 tests argv 后带 --allow-tests 执行。
DeepSeek主要编码与修复；Codex做科学/工程决策、诊断和独立验收；固定测试由控制器执行。
预算见配置；完成已授权节点后自动选依赖满足的下一项，保存状态、stop_reason和next_action。
完整TP接口尚未实现；开始物理源码修改或新实验前，按TP_ACCEPTANCE.md明确假设、范围、阈值和预算。
开始时只简短说明当前状态、依赖缺口、最小下一步，不重新下载全部资料。
```

If you only want a generic coding workflow, use the root live example and replace its scope/acceptance/tests. You do not need to study MAGRATHEA or install scientific libraries to run the infrastructure demo. Independent reviewer API/CLI availability is your own account prerequisite.
