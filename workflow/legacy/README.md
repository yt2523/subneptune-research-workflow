# 本地科研 Agent 工作流

已联通：本对话 Codex 总调度 → Cline/DeepSeek 编码 → 独立 Codex/GPT 只读审核 → 固定测试 → 人工批准关卡。

这是一套小型串行实现。没有安装额外编排框架。求解器长任务和 GitHub 网络发布尚未启用。

## 已验证的入口

在 PowerShell 或 VS Code 终端进入 `D:\GPT\projects\Sub-Neptune\workflow`：

```powershell
.\Workflow.ps1 -Action Status -Run 'D:\GPT\projects\Sub-Neptune\workflow\runs\live-20261025-142733-11d838'
.\Workflow.ps1 -Action Report -Run 'D:\GPT\projects\Sub-Neptune\workflow\runs\live-20261025-142733-11d838'
```

新任务准备 TASK.md，写清问题、允许改动、物理假设、单位、文献和验收标准。`scope.json` 是允许修改的文件名数组，例如 `["src/EOS.cpp","run/test.cfg"]`。

```powershell
.\Workflow.ps1 -Action New -Task 'D:\path\TASK.md' -Repo 'D:\GPT\projects\Sub-Neptune\Magrathea' -Scope 'D:\path\scope.json'
# 上一步返回一个新的运行目录，以下用该目录替换 <run>
.\Workflow.ps1 -Action Code -Run '<run>'
.\Workflow.ps1 -Action Review -Run '<run>'
```

`New -Repo` 从当前提交 HEAD 创建 `workflow/<run-id>` 分支和独立 worktree，不包含原工作目录未提交的修改。若要用未提交成果，先由你或总调度明确选择并提交；不能擅自混入。每份编码提案自动产生本地 commit；拒绝的版本也保留。支持 Python/C++/Fortran/Julia 和常见配置文件。暂不支持二进制修改、文件删除、重命名、多写者并发。

总调度随后在已配置的沙箱中运行固定测试，把实际结果记录到 `Store.record_tests()`。不能用“模型说测试通过”代替真实执行。此版本没有给任意生成代码开放无人值守的终端。测试完成且独立审核通过后，`Approve` 只设置批准标志；它不会启动求解器。

审核拒绝时，总调度把具体缺陷回传 DeepSeek，并明确修订 TASK.md；保留之前任务副本。再次 Code、测试、Review，最多先做两轮，避免无限循环。不能用 `--task` 偷换不同审核标准。

## 模型和凭据

- 总调度：当前 Codex/ChatGPT 对话，沿用你的登录。
- 编码：Cline 3.0.73；provider 固定 deepseek，model 沿用已有配置 `deepseek-v4-pro`。
- 审核：单独 `codex exec`，read-only、ephemeral、忽略用户配置以减少额外工具和上下文；使用当前 Codex 可用默认 GPT 模型。
- Cline 现有 CLI 配置已复制到 `D:\Codex\cline-home`，目录访问限制为本机当前账户和 SYSTEM。没有复制 VS Code 插件目录。不要把该目录加入 Git、报告或聊天。
- 模型调用不把 Key 放在参数或提示词中。角色、实际返回模型元数据及可用用量写到运行记录。

## 目录和阅读顺序

```text
workflow/
  Workflow.ps1           # 人工/总调度入口
  workflow.py            # 状态、关卡、文件提案、本地 Git
  agents.py              # 有超时的 Cline/Codex 适配器
  prompts/               # orchestrator / coder / reviewer
  test_*.py              # 控制器回归测试
  acceptance_profile.py  # 此次工具任务的固定验收测试
  runs/<run-id>/
    REPORT.md            # 先看状态和限制
    TASK.md              # 再看物理/数值契约
    review-XX.json       # 逐轮独立审核意见
    tests-XX.md          # 实测结果
    proposal-XX.json     # 逐轮完整文件提案、模型与用量
    source/              # 独立代码目录和 Git 历史
    *.input.md           # 实际发送给模型的输入
    *.events.jsonl       # CLI 可见事件
    state.json           # 可恢复状态
    audit.jsonl          # 结构化动作、序号和摘要
  logs/                  # 安装、连接和集成测试记录
```

审计保存 CLI 暴露的事件、输入和用量；不宣称能获得厂商内部隐藏推理或所有底层请求。记录在本地，不是防管理员篡改的审计系统。原始事件可能含私有代码，默认不推送。

## 关卡、恢复和成本

代码、规范任务或 scope 变化会使旧审核和测试失效。文件摘要使用长度前缀和内容 SHA256，任务摘要使用规范 JSON。审计与状态保存递增序号；写入中断导致序号不一致时，运行关卡关闭，状态变为 recovery_required。

限流、进程超时或服务错误保存 paused。不要盲目重试；先看事件末尾和 state。额度恢复后由总调度重启未完成步骤，成功步骤与提案继续复用。不会承诺订阅额度一定在某固定时刻恢复，也没有安装后台唤醒器。

单次 Cline 超时75秒，外层90秒；GPT外层120秒。模型上下文文件总字符数上限32000，超限要求缩小 scope。DeepSeek 做实现，GPT只审核关键结果。文献任务按需挂 LR-assistant，不把整库文献或全部 Skill 每轮重发。

当前控制器采用单写者。不要对同一 run 同时启动 Code/Review/Approve。长时间计算还需要独立的进程树取消、资源配额和 OS/容器沙箱；本版本不把工作目录隔离冒充安全沙箱。

## GitHub 与物理实验的下一道边界

已测试本地 worktree、分支、自动 commit、保留原目录脏修改及 git revert。尚未测试向 yt2523 的 GitHub 认证、push 或 PR。接正式仓库后，先审查 `git diff` 和待推送文件，再 push 工作分支并创建 PR；合并要求测试、独立审核和人工确认。已共享提交优先用 revert 回退，不默认 force-push。

第一项科学任务建议只比较热结构假设对组成推断的偏差：固定质量、EOS、边界条件和组成参数化，先做基准复现，再逐项改变 TP/绝热假设。化学平衡先作为敏感性或一致性约束，避免同时改变多套未知机制。文献校验必须给到方程、单位、页码/图号及代码位置；没有依据时标为未验证。

尚未在此版本实现 Zotero 自动写入、手机推送、HPC 提交、全天自主调度或任意源码无人值守执行。它们不会被这次小型工具联调误标成已完成。


## 2026-10-25 科学比较实测
固定参数灰大气/绝热连接比较完成，18组参数×3种分辨率、9项数值检查通过。原通用程序外壳被拒绝，两轮修复未成功；最终使用未改动的DeepSeek解析核心，经重新独立审核，在主调度的固定输入数值测试驱动中执行。不把这次结果当成通用源码自动化或RCE已验证。报告位于 D:/GPT/projects/Sub-Neptune/outputs/tp-comparison-20261025-dedb3d/REPORT.md。交接模板已修正固定profile.py示例名，编码明确关闭额外推理且严格要求JSON。
