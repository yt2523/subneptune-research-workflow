# Sub-Neptune research + portable AI workflow

把科研工程、实验归档、AI 编程流程放在同一个仓库。可以只试工作流，也可以继续 Sub-Neptune 研究。给AI的启动提示见 [START_HERE.md](START_HERE.md)。

**当前科学状态：完整外部 TP 接口尚未实现。** 已归档的是半灰大气对照、mode0 验证，以及 67 次边界温度/合成气层质量恢复。它们不是观测行星后验，也不是同边界纯 TP 形状实验。

## 先试不花 API 的工作流

需要 Python 3.10+；基础工作流只使用标准库，不必安装项目全部科学依赖。以下命令在仓库根目录执行：

```sh
python -B workflow/portable.py doctor --config workflow/examples/demo.json
python -B -m unittest discover -s workflow/tests -v
python -B workflow/portable.py run --config workflow/examples/demo.json --offline
python -B workflow/portable.py status --config workflow/examples/demo.json
# 再运行一次会恢复已有状态、跳过已通过节点
python -B workflow/portable.py run --config workflow/examples/demo.json --offline
```

离线示例使用标记为 `OFFLINE_FIXTURE_NOT_LLM` 的实现/审核夹具，但实际执行本地断言。通过不代表真实模型调用或行星物理通过。结果保存在配置的 run_dir 中，不上传 Git。

## 用自己的 API 文件

先读 [配置与密钥](docs/workflow/SETUP.md)，复制根目录 `workflow.local.example.json` 为 `workflow.local.json`，给该配置指定新的 run_dir。密钥文件放仓库外，不发到聊天、不提交 Git：

```json
{"DEEPSEEK_API_KEY":"replace-locally","OPENAI_API_KEY":"optional-for-api-review-only"}
```

```sh
python -B workflow/portable.py run --config workflow.local.json --credentials /absolute/path/keys.json --allow-tests
```

Windows 用 `D:/secrets/keys.json` 等实际路径。默认实现者为 DeepSeek；默认独立审核用已登录的 Codex CLI，不需要 OpenAI API key。无 Codex 的同学可配置独立审核 API 与模型，需自行提供相应 key。仅 API 文件不足以安装 Python/Git/Codex 或构建科学求解器；doctor 会检查可见依赖，实际服务权限由使用者账户决定。不会自动登录、安装或启动行星实验。

**执行测试使用预先声明的命令白名单，但不是 OS 安全沙箱。** 首次运行别人的任务前须审阅 tests 命令；可信机器或受限容器内运行。代码改在 run_dir/source 副本中，验收后再查看差异移回工程。

## 从这里继续科研

- [项目状态与最小下一步](docs/PROJECT_STATUS.md)
- [TP 接口验收表](docs/TP_ACCEPTANCE.md)
- [已完成实验索引](experiments/subneptune-20261027/README.md)
- [原始交接与科学限制](experiments/subneptune-20261027/HANDOFF.md)
- [Linux/WSL 构建与批跑](docs/SCIENCE_REPRODUCTION.md)

根目录 `src/`、`tabulated/`、`Makefile` 是 MAGRATHEA 工程；[原项目说明](docs/MAGRATHEA_UPSTREAM_README.md)保留作者、文献与构建信息。历史文件中的 `D:/...` 是原机器路径，保留原字节供追溯；新的工作流配置使用相对路径，不要求同学复制原目录结构。

## 工作流如何运作

任务计划 → 按依赖/优先级选节点 → DeepSeek 编码 → 固定测试 → 独立 Codex/API 审核 → 保存证据 → 继续下一节点。预算或错误中断后从状态恢复。规划依赖已写好的计划；程序不会自行决定新的科学假设或无限扩展研究。

[AGENTS.md](AGENTS.md)定义权限与角色；[短规则](docs/workflow/SHORT_RULES.md)防止复发；[基础设施验收标准](docs/workflow/ACCEPTANCE.md)定义工程合格线；[架构](docs/workflow/ARCHITECTURE.md)解释目录和调用。已有 Windows/Cline 版本在 [workflow/legacy](workflow/legacy/README.md)，作为历史参考；新的入口不依赖作者本机 Cline 配置。

## 分享与引用

基于 [Huang-CL/Magrathea](https://github.com/Huang-CL/Magrathea) 与 [yt2523/Magrathea](https://github.com/yt2523/Magrathea)，保留 MIT 许可和原作者署名。研究快照来自 `archive/subneptune-20261027` 的 `0aa6316`。工作流架构参考见 [来源与边界](docs/workflow/PROVENANCE.md)。这是个人研究工具，不是上游 MAGRATHEA 官方工作流。

English: This repository combines the MAGRATHEA project, immutable synthetic experiment archives, and a portable bounded coding/test/independent-review loop. Start with the zero-key offline demo. Live use requires your own external credential file and configured reviewer. Full TP-profile input is not yet implemented; historical numeric checks do not validate the new interface.


发现问题可在本仓库 GitHub Issues 上报，使用内置模板；智能体先整理脱敏复现，经使用者授权后提交。
