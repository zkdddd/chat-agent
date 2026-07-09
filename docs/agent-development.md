# Agent Development Log

这个文档用来记录 KAgent 的代码 Agent 能力是怎样一步步发展出来的。

记录原则：
- 每次新增功能或优化能力，都要写一条记录。
- 每条记录说明“做了什么、为什么做、影响哪些模块、怎么验证、下一步是什么”。
- 优先记录代码能力、上下文能力、工具能力、验证能力和稳定性能力。

## 当前阶段目标

当前阶段先把代码 Agent 的核心功能做好，不优先扩展产品化 UI、混合模型策略或复杂生态能力。

重点方向：
- 让 Agent 能稳定理解项目结构。
- 让 Agent 能安全读写文件、运行命令并验证结果。
- 让 Agent 的上下文不容易爆掉。
- 让 Agent 失败后能自己判断原因并恢复。
- 让每一次运行都能被追踪和复盘。

## 2026-07-09: 上下文管理

### 做了什么

新增上下文管理模块，用来控制发给模型的历史消息长度。

主要能力：
- 估算消息 token 数。
- 保留最近关键对话。
- 将较早上下文压缩成摘要。
- 限制单条消息最大字符数。
- 支持会话级持久化摘要。

### 为什么做

之前上下文容易越积越大，导致压缩失败、请求失败或模型注意力被旧内容干扰。

这个阶段先保证 Agent 长时间工作时不会被历史消息拖垮。

### 影响模块

- `kagent/context.py`
- `kagent/db.py`
- `kagent/llm.py`
- `kagent/ui/agent_worker.py`
- `kagent/agent/code_agent.py`

### 验证

新增 `tests/test_context.py`，验证旧消息会被压缩，最近消息会保留。

## 2026-07-09: Agent 状态机

### 做了什么

给代码 Agent 增加运行阶段状态。

主要阶段：
- `starting`
- `inspecting`
- `planning`
- `editing`
- `validating`
- `repairing`
- `finalizing`
- `stopped`

### 为什么做

之前 Agent 在做什么不够清楚。状态机可以让 UI、日志和后续调试都知道 Agent 当前处于哪个阶段。

### 影响模块

- `kagent/agent/code_agent.py`

### 验证

通过现有 Agent 流程测试和完整测试脚本验证状态切换不破坏主流程。

## 2026-07-09: Agent 模块拆分

### 做了什么

把原本过大的 `code_agent.py` 拆成多个职责更清晰的模块。

拆分模块：
- `kagent/agent/tool_schema.py`
- `kagent/agent/risk_policy.py`
- `kagent/agent/validation.py`
- `kagent/agent/tool_view.py`
- `kagent/agent/run_log.py`

### 为什么做

`code_agent.py` 承担了太多职责，后续继续加能力会越来越难维护。

模块拆分后，每块能力可以独立测试、独立演进。

### 验证

新增多组单元测试：
- `tests/test_risk_policy.py`
- `tests/test_validation.py`
- `tests/test_run_log.py`

## 2026-07-09: 自动验证流程

### 做了什么

新增自动验证计划和执行流程。

主要能力：
- 根据项目类型和变更文件生成验证计划。
- Python 项目优先做语法检查。
- 如果存在 `scripts/verify.ps1`，优先运行项目统一验证脚本。
- 支持 pytest 验证。
- 验证失败后进入 repair 流程，最多自动修复多轮。

### 为什么做

代码 Agent 不能只改文件，还要尽量确认改动没有破坏项目。

验证流程是代码能力的核心闭环：改动 -> 验证 -> 失败修复 -> 再验证 -> 最终答复。

### 影响模块

- `kagent/agent/validation.py`
- `kagent/agent/code_agent.py`
- `scripts/verify.ps1`
- `run-tests.bat`

### 验证

新增 `tests/test_validation.py`。

运行结果曾达到：

```text
14 passed
```

## 2026-07-09: 运行日志

### 做了什么

新增 JSONL 运行日志。

主要能力：
- 每次 Agent 运行生成独立 `run_id`。
- 记录 `run_start`、`agent_status`、`tool_start`、`tool_result`、`run_finish` 等事件。
- 日志保存到 `.kagent_state/runs/`。
- `agent_start` 事件包含 `run_id` 和 `run_log_path`。
- 新增日志读取和摘要能力。

### 为什么做

Agent 一旦失败、卡住或行为异常，需要能复盘它每一步做了什么。

只写日志还不够，还要能读回来并生成摘要。

### 影响模块

- `kagent/agent/run_log.py`
- `kagent/agent/code_agent.py`

### 验证

新增 `tests/test_run_log.py`。

覆盖：
- JSONL 写入。
- 日志读取。
- 日志摘要。
- 最新日志选择。
- 坏 JSON 报错。

## 2026-07-09: 工具展示优化

### 做了什么

优化工具调用报告展示。

主要能力：
- 工具报告展示输入、预览、结果。
- 修复部分历史乱码标题，让报告更容易看懂。

### 为什么做

工具调用是 Agent 行为的核心证据，展示不清楚会影响调试和信任感。

### 影响模块

- `kagent/agent/tool_view.py`
- `kagent/agent/code_agent.py`

### 验证

新增 `tests/test_tool_view.py`。

## 2026-07-09: 工具输出压缩

### 做了什么

新增工具结果上下文压缩模块。

主要能力：
- UI 和日志保留完整工具结果。
- 发送给模型的工具结果使用压缩版。
- `read_file` 大内容保留头尾。
- `search_file` 限制匹配数量。
- `list_files` 限制文件条目数量。
- `run_command` 保留退出码、摘要、头尾输出，并提取关键错误行。

### 为什么做

工具输出很容易撑爆上下文，尤其是大文件、大目录、测试输出和错误堆栈。

压缩工具结果可以显著降低上下文压力，同时保留模型继续推理需要的关键信息。

### 影响模块

- `kagent/agent/tool_result_context.py`
- `kagent/agent/code_agent.py`

### 验证

新增 `tests/test_tool_result_context.py`。

运行结果达到：

```text
24 passed
```

## 2026-07-09: 工具失败恢复提示

### 做了什么

新增工具失败分类和恢复建议。

主要分类：
- `invalid_arguments`
- `missing_required_argument`
- `path_not_found`
- `permission_scope`
- `expected_file`
- `expected_directory`
- `non_text_file`
- `timeout`
- `missing_dependency`
- `command_not_found`
- `code_error`
- `validation_failed`
- `user_rejected`

失败工具结果会在给模型的上下文中附带 `recovery` 字段。

### 为什么做

Agent 工具调用失败后，不能只是看到一坨错误文本。它需要知道下一步应该怎么恢复。

例如：
- 路径不存在时，先搜索或列目录。
- 命令缺依赖时，不要盲目重试。
- 代码语法错误时，打开对应文件修复再验证。
- 用户拒绝高风险操作时，不要自动重复执行。

### 影响模块

- `kagent/agent/tool_recovery.py`
- `kagent/agent/tool_result_context.py`

### 验证

新增 `tests/test_tool_recovery.py`。

运行结果达到：

```text
31 passed
```

## 2026-07-09: 任务规划和检查清单

### 做了什么

新增轻量任务规划模块。

主要能力：
- Agent 运行前生成执行检查清单。
- 检查清单会根据任务类型包含不同步骤。
- 代码任务通常包含理解任务、检查上下文、修改文件、验证改动、总结结果。
- 普通回答任务只保留理解任务和最终回答。
- 每个步骤支持 `pending`、`active`、`done`、`skipped`、`failed` 状态。
- 工具调用、自动验证、修复流程和最终回答会更新对应步骤状态。
- 计划状态会写入 `agent_plan` 日志事件。
- 最终回答提示会带上计划状态，帮助模型基于实际执行过程总结。

### 为什么做

之前 Agent 已经有上下文、工具、验证、日志和错误恢复，但还缺一个执行中枢。

任务规划可以让 Agent 在动手前先明确路径，执行中减少乱调用工具、重复调用工具和漏验证。

### 影响模块

- `kagent/agent/task_plan.py`
- `kagent/agent/code_agent.py`
- `README.md`

### 验证

新增 `tests/test_task_plan.py`。

运行结果达到：

```text
35 passed
```

## 2026-07-09: 测试失败定位能力

### 做了什么

新增失败诊断解析模块。

主要能力：
- 从 `run_command` 的 stdout、stderr、summary、error 中提取失败位置。
- 支持 Python traceback 的 `File "...", line ...`。
- 支持 `SyntaxError` 附近的文件和行号。
- 支持 pytest 的 `FAILED tests/test_x.py::test_name` 节点。
- 支持通用 `file.py:line` 格式。
- 压缩后的命令结果会带上 `diagnostics` 字段。
- 验证失败摘要会追加 `Failure locations`，帮助 repair prompt 聚焦失败位置。

### 为什么做

之前 Agent 能看到验证失败，但需要自己从长输出里猜哪里坏了。

失败定位能力可以让 Agent 更快找到要读的文件、要看的行号和失败测试名，减少盲目搜索和重复运行全量测试。

### 影响模块

- `kagent/agent/failure_diagnostics.py`
- `kagent/agent/tool_result_context.py`
- `kagent/agent/validation.py`
- `README.md`

### 验证

新增 `tests/test_failure_diagnostics.py`。

扩展测试：
- `tests/test_tool_result_context.py`
- `tests/test_validation.py`

运行结果达到：

```text
41 passed
```

## 2026-07-09: 失败位置自动聚焦读取

### 做了什么

新增失败聚焦读取模块。

主要能力：
- 根据 `diagnostics` 生成具体 `read_file` 目标。
- 对 traceback、语法错误、`file.py:line` 读取失败行附近上下文。
- 对 pytest nodeid 自动读取对应测试文件。
- 自动验证失败后，会先读取最多 3 个失败位置片段。
- 聚焦读取结果会进入模型上下文和工具报告。
- 聚焦目标会写入 `failure_focus` 日志事件。
- 读取完成后再进入 repair 流程，让模型基于失败位置附近代码修复。

### 为什么做

之前 Agent 已经能知道失败位置，但还需要下一轮模型主动决定读取哪里。

自动聚焦读取把“知道哪里坏了”推进到“已经把坏的位置附近代码拿到手”，可以减少盲目搜索和重复工具调用。

### 影响模块

- `kagent/agent/failure_focus.py`
- `kagent/agent/code_agent.py`
- `README.md`

### 验证

新增 `tests/test_failure_focus.py`。

运行结果达到：

```text
45 passed
```

## 2026-07-09: 小范围验证和增量验证

### 做了什么

新增 focused validation 命令生成和执行流程。

主要能力：
- 验证失败后，根据 `diagnostics` 生成小范围验证命令。
- pytest nodeid 会生成单个测试命令。
- 测试文件失败会生成对应测试文件命令。
- 普通 Python 源文件失败会生成 `py_compile` 命令。
- 修复后先运行 focused validation。
- focused validation 通过后不会直接结束，而是继续运行完整验证计划。
- 完整验证通过后清空 focused validation 状态。

### 为什么做

之前每次修复后都会直接回到完整验证计划。对大项目来说，这会让迭代速度变慢。

增量验证让 Agent 先确认刚才失败的位置是否修好，再做完整验证，能更快反馈修复是否有效，同时保留最终完整验证的安全性。

### 影响模块

- `kagent/agent/validation.py`
- `kagent/agent/code_agent.py`
- `README.md`

### 验证

扩展 `tests/test_validation.py`。

运行结果达到：

```text
48 passed
```

## 2026-07-09: 代码变更影响分析

### 做了什么

新增影响分析模块。

主要能力：
- 根据变更文件推断相关测试文件。
- 支持常见 Python 测试命名约定，例如 `context.py` -> `tests/test_context.py`。
- 支持嵌套模块路径，例如 `kagent/agent/validation.py` -> `tests/agent/test_validation.py`。
- 如果变更文件本身就是测试文件，会直接把该测试文件作为相关测试。
- Python 验证计划会把相关测试插入到语法检查之后、完整 pytest 或项目验证之前。
- 默认验证计划命令数从 2 提升到 3，以容纳“语法检查 + 相关测试 + 完整验证”。

### 为什么做

之前增量验证主要依赖失败诊断。对于尚未失败的普通改动，Agent 仍然只能直接跑完整验证。

影响分析让 Agent 能在改动后先运行最可能受影响的测试文件，尽早发现局部问题，再进入完整验证。

### 影响模块

- `kagent/agent/impact_analysis.py`
- `kagent/agent/validation.py`
- `README.md`

### 验证

新增 `tests/test_impact_analysis.py`。

扩展 `tests/test_validation.py`。

运行结果达到：

```text
52 passed
```

## 2026-07-09: 项目索引和文件地图

### 做了什么

新增轻量项目地图模块。

主要能力：
- 扫描项目文件并跳过 `.git`、虚拟环境、`node_modules`、构建目录等无关目录。
- 分类源码文件、测试文件、配置文件和入口文件。
- 建立源码文件到测试文件的命名映射。
- 支持常见 Python 测试命名约定。
- 提供项目地图摘要，包含源码数量、测试数量、配置文件、入口文件、已映射源码数量。
- 影响分析模块开始复用项目地图。
- 如果变更文件尚未在文件地图中出现，影响分析仍会用命名约定做兜底推断。

### 为什么做

之前影响分析内部自己维护文件命名规则。随着后续符号搜索、验证计划、测试选择能力增强，这类项目结构信息需要统一来源。

项目地图是后续能力的底座：搜索、测试选择、影响分析、入口识别、项目理解都可以复用它。

### 影响模块

- `kagent/agent/project_map.py`
- `kagent/agent/impact_analysis.py`
- `README.md`

### 验证

新增 `tests/test_project_map.py`。

扩展影响分析测试。

运行结果达到：

```text
55 passed
```

## 2026-07-09: 符号级搜索能力

### 做了什么

新增 Python 符号索引模块，并暴露为 Agent 工具。

主要能力：
- 使用 Python AST 解析源码文件。
- 提取 class、function、method、import。
- 支持按符号名精确查找。
- 支持按符号名模糊查找。
- 支持按符号类型过滤。
- 返回符号所在文件、起始行、结束行、容器和导入模块。
- 新增 `find_symbol` 工具，Agent 可以直接按符号定位代码。
- 工具结果会被压缩，避免大量符号结果撑爆上下文。

### 为什么做

之前 Agent 定位代码主要依赖全文搜索和读取文件。对于函数、类、方法这类结构化目标，全文搜索噪声较多。

符号级搜索让 Agent 能更快找到定义位置，减少盲目搜索，也为后续引用分析和影响范围分析打基础。

### 影响模块

- `kagent/agent/symbol_index.py`
- `kagent/agent/tool_schema.py`
- `kagent/agent/code_agent.py`
- `kagent/agent/tool_result_context.py`
- `README.md`

### 验证

新增 `tests/test_symbol_index.py`。

扩展 `tests/test_tool_result_context.py`。

运行结果达到：

```text
59 passed
```

## 2026-07-09: 编辑前 diff 规划能力

### 做了什么

新增变更计划模块。

主要能力：
- 对写文件、应用补丁、重命名、复制、删除、创建目录、回滚等变更工具生成结构化计划。
- 计划包含工具名、操作类型、涉及路径、路径数量、风险级别、是否破坏性、是否需要审批。
- 如果存在 diff 或预览，会记录预览摘要。
- 工具执行前会发出 `change_plan` 日志事件。
- 工具报告中新增“变更计划”区块。
- 工具结果压缩后仍会保留 `change_plan`，让模型上下文能看到执行前计划。

### 为什么做

之前工具已经有 preview，但 preview 主要是文本，不方便日志分析和后续审批。

结构化变更计划可以让 Agent 在执行改动前明确“要改什么、风险是什么、会影响哪些路径”，后续可以用于审批、回滚说明、提交摘要和安全策略。

### 影响模块

- `kagent/agent/change_plan.py`
- `kagent/agent/code_agent.py`
- `kagent/agent/tool_view.py`
- `kagent/agent/tool_result_context.py`
- `README.md`

### 验证

新增 `tests/test_change_plan.py`。

扩展测试：
- `tests/test_tool_view.py`
- `tests/test_tool_result_context.py`

运行结果达到：

```text
64 passed
```

## 2026-07-09: Patch 失败恢复能力

### 做了什么

新增 Patch 失败恢复模块。

主要能力：
- 当 `apply_patch` 失败时，识别为 `patch_failed`。
- 从 `change_plan` 和错误文本中提取相关文件路径。
- 自动读取相关文件当前上下文。
- 生成恢复提示，要求下一轮使用当前真实上下文生成更小、更精确的 patch。
- 写入 `patch_recovery` 日志事件。
- 恢复建议会进入工具结果压缩上下文。

### 为什么做

补丁失败是代码 Agent 常见问题。失败后如果只把错误文本给模型，模型很容易重复生成同样无法应用的 patch。

自动读取当前文件上下文后，模型能基于真实内容重新生成更小 patch，成功率更高。

### 影响模块

- `kagent/agent/patch_recovery.py`
- `kagent/agent/tool_recovery.py`
- `kagent/agent/code_agent.py`
- `README.md`

### 验证

新增 `tests/test_patch_recovery.py`。

扩展 `tests/test_tool_recovery.py`。

运行结果达到：

```text
68 passed
```

## 2026-07-09: 测试失败修复策略升级

### 做了什么

新增修复策略分类模块。

主要能力：
- 将命令和验证失败进一步分类。
- 支持识别缺依赖、命令不存在、超时、语法错误、导入错误、断言失败、运行时错误、普通测试失败。
- `tool_recovery` 复用统一分类策略。
- `validation_failure_prompt` 会附带 failure category 和 repair strategy。
- 模型在修复时能收到更具体的策略，而不是泛泛地“检查失败并修复”。

### 为什么做

不同失败类型需要不同修复方式。

例如断言失败应该比较 expected vs actual，导入失败应该检查模块路径和循环导入，语法错误应该先打开具体行并运行 `py_compile`。

更细的修复策略能减少盲目重试，提升自动修复质量。

### 影响模块

- `kagent/agent/repair_strategy.py`
- `kagent/agent/tool_recovery.py`
- `kagent/agent/validation.py`
- `README.md`

### 验证

新增 `tests/test_repair_strategy.py`。

扩展测试：
- `tests/test_tool_recovery.py`
- `tests/test_tool_result_context.py`
- `tests/test_validation.py`

运行结果达到：

```text
74 passed
```

## 2026-07-09: 工具调用去重和防循环

### 做了什么

新增工具循环检测模块。

主要能力：
- 为工具调用生成稳定签名。
- 记录最近工具调用历史。
- 识别重复失败的同一工具调用。
- 识别重复读取、搜索、符号查找、文件列表等检查动作。
- 触发循环风险时写入 `tool_loop_warning` 日志事件。
- 向模型上下文追加提示，要求不要原样重试，要换策略或换参数。

### 为什么做

Agent 在复杂任务里容易卡在同一个失败命令、同一个补丁或重复读取同一文件上。

防循环能力可以及时打断重复动作，让模型改变策略，比如读取不同上下文、缩小命令范围、换 patch 方式。

### 影响模块

- `kagent/agent/tool_loop_guard.py`
- `kagent/agent/code_agent.py`
- `README.md`

### 验证

新增 `tests/test_tool_loop_guard.py`。

运行结果达到：

```text
78 passed
```

## 2026-07-09: 运行日志查看器

### 做了什么

新增运行日志查看器模块。

主要能力：
- 根据 `run_id` 在 `.kagent_state/runs/` 中查找对应 JSONL 日志。
- 读取运行日志并生成事件时间线。
- 生成人类可读的运行摘要。
- 摘要中展示 run id、状态、工作区、开始/结束时间、事件数量和最后阶段。
- 汇总工具调用次数、失败工具、验证结果、变更路径。
- 汇总防循环警告、Patch 恢复和失败聚焦读取等调试信号。
- 支持读取最新一条运行日志并生成摘要，方便后续接入 UI 或调试命令。

### 为什么做

前面已经让 Agent 写入 JSONL 运行日志，但原始 JSONL 更适合机器读，不适合人快速复盘。

运行日志查看器把日志变成“可读的运行报告”，后续可以用来排查 Agent 为什么失败、卡在哪里、是否验证过、改了哪些文件，也能作为 UI 里的运行详情面板基础。

### 影响模块

- `kagent/agent/run_log_viewer.py`
- `tests/test_run_log_viewer.py`
- `README.md`
- `docs/agent-development.md`

### 验证

新增 `tests/test_run_log_viewer.py`。

覆盖内容：
- 按 `run_id` 查找日志。
- 生成事件时间线。
- 摘要展示失败工具、验证结果、变更路径和调试信号。
- 最新日志为空时返回 `None`。
- 查找时跳过损坏的 JSONL 文件。

运行结果达到：

```text
83 passed
```

## 2026-07-09: Agent 自检报告

### 做了什么

新增 Agent 运行自检模块。

主要能力：
- 基于 JSONL 运行日志分析本次 Agent 运行健康度。
- 输出 `pass`、`warn`、`fail` 三档健康状态。
- 判断本次运行是否可信。
- 标记运行未结束、非正常完成、代码变更未验证、验证失败。
- 汇总失败工具调用和循环风险。
- 统计 Patch 恢复和失败聚焦读取次数，方便复盘 Agent 是否经历过恢复流程。
- 支持分析最新运行日志或根据 `run_id` 分析指定运行。
- 生成可读的自检报告，后续可接入最终回复或调试面板。

### 为什么做

运行日志查看器解决了“人能看懂日志”的问题，但还没有明确告诉用户“这次 Agent 执行能不能信”。

自检报告把日志里的关键信号转成健康度判断，尤其关注代码 Agent 最重要的几个风险：任务没跑完、改了文件但没验证、验证仍失败、工具反复失败或出现循环。

这一步能让后续最终回复更诚实，也能为 UI 里的运行详情、历史复盘和自动调试打基础。

### 影响模块

- `kagent/agent/run_self_check.py`
- `tests/test_run_self_check.py`
- `README.md`
- `docs/agent-development.md`

### 验证

新增 `tests/test_run_self_check.py`。

覆盖内容：
- 干净完成的运行返回 `pass`。
- 代码变更未验证返回 `fail`。
- 验证失败、失败工具和循环风险会被识别。
- 已恢复的工具失败返回 `warn`。
- 未结束或被中止的运行返回 `fail`。
- 支持分析最新日志和按 `run_id` 分析。

运行结果达到：

```text
89 passed
```

## 当前验证入口

推荐使用：

```powershell
.\run-tests.bat
```

这个脚本会执行：
- Python 语法检查。
- pytest 单元测试。

## 发展日志模板

以后每次添加 Agent 能力，都按这个模板追加。

```markdown
## YYYY-MM-DD: 功能或优化名称

### 做了什么

- ...

### 为什么做

- ...

### 影响模块

- `path/to/file.py`

### 验证

- 运行了什么命令。
- 结果是什么。

### 后续

- 下一步建议。
```

## 下一步建议

下一步建议做最终回复可信度接入。

目标：
- 在 Agent 最终回复前读取本次运行自检结果。
- 如果存在未验证变更、验证失败、未完成运行，要在最终回复里明确提示。
- 如果只有工具失败但已恢复，给出轻量风险提示。
- 后续可以把自检报告接入 UI 调试面板。
