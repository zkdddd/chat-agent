# kagent 术语表（专有名词解释）

> 给项目 owner：每个专有名词 **是什么 + 在 kagent 里指什么（file:line）+ 面试怎么用**。
> 配合 `docs/project-capabilities-overview.md` 阅读。生成于 2026-07-23，基于真实代码核验，共 84 个术语。

---

## 目录

- [AI/Agent 域](#ai-agent-域)（26）
- [符号/代码智能 域](#符号-代码智能-域)（8）
- [验证/测试 域](#验证-测试-域)（14）
- [上下文/记忆 域](#上下文-记忆-域)（12）
- [安全/审计 域](#安全-审计-域)（18）
- [工具/平台 域](#工具-平台-域)（6）

---

## AI/Agent 域

**ReAct (Reasoning + Acting)**

- 是什么：一种 Agent 范式：模型按 思考(Reason)->行动(Act)->观察(Observe) 的循环推进任务，每一步先想再做再看结果，而不是一次性输出答案。
- 在 kagent 里：code_agent.py:1556 的 for round_idx in range(max_rounds) 主循环——每轮先调模型拿 assistant 消息，若有 tool_calls 就逐个执行并把 tool 结果塞回 messages，再进下一轮；无 tool_calls 且条件满足时收尾。这就是 kagent 的 ReAct 实现。
- 面试怎么用：可以说：我用 ReAct 模式实现 Agent，让模型在 思考-行动-观察 的循环里自主调用工具，而不是一次性生成答案。

**Tool loop / 工具循环**

- 是什么：Agent 反复 调用模型->执行工具->把结果喂回模型 的迭代循环，直到任务完成或达到轮次上限。
- 在 kagent 里：code_agent.py:1556-2008 的 for round_idx in range(max_rounds) 循环：每轮把 messages 喂给模型 _stream_assistant_message 拿 tool_calls，逐个 _execute_tool_action 执行并 append role=tool 结果，回到 messages 后进入下一轮——直到无 tool_calls 触发收尾或达到 max_rounds。
- 面试怎么用：可以说：Agent 的核心是一个 tool loop，每轮解析模型返回的函数调用、执行、把结果回灌，循环到收敛或达到轮次上限。

**tool_call**

- 是什么：模型在回复里要求调用某个函数的结构化请求，包含函数名和参数(JSON)。
- 在 kagent 里：模型返回的 assistant.tool_calls（code_agent.py:1706），每个含 function.name 和 function.arguments(JSON 字符串)；code_agent.py:1859 用 json.loads(raw_args) 解析参数后 _dispatch_tool 执行。
- 面试怎么用：可以说：模型按 OpenAI function-calling 协议返回 tool_call，我解析 JSON 参数后路由到对应工作区工具执行。

**tool_result**

- 是什么：工具执行后回灌给模型的结果消息，是 ReAct 里 Observation 的载体。
- 在 kagent 里：工具执行后以 role=tool、tool_call_id、content=tool_result_json_for_model(...) append 进 messages（code_agent.py:782-788），即喂回模型的 Observation；同时 emit 一个 type=tool_result 事件给 UI。
- 面试怎么用：可以说：工具结果以 role=tool 消息回灌给模型作为 Observation，驱动下一轮决策。

**Observation / 观察**

- 是什么：ReAct 中的 O：Agent 通过工具拿到的环境反馈(命令输出、文件内容、错误信息)，作为下一轮推理的输入。
- 在 kagent 里：即 role=tool 那条消息的 content——工具的 stdout/stderr/匹配结果/错误等，模型下一轮据此推理；失败时还会附加 focus_prompt、validation_failure_prompt 等系统提示引导修复。
- 面试怎么用：可以说：每轮工具的 Observation 喂回模型，让 Agent 基于真实执行结果而非凭空推理下一步。

**max_rounds**

- 是什么：工具循环的最大迭代轮数上限，防止 Agent 陷入死循环无限消耗。
- 在 kagent 里：code_agent.py:1420 run(...) 的默认参数 max_rounds=12，对应 :1556 的 for round_idx in range(max_rounds)；超过则在 :2007 调 _finish_run_with_trust_check('max_rounds', ...) 并以 status=max_rounds 结束 run_log。
- 面试怎么用：可以说：我给 Agent 设了 max_rounds=12 的硬上限防止死循环，超限会触发 max_rounds 收尾并记录到 run_log。

**AgentPhase**

- 是什么：Agent 运行时所处的阶段标签，用于状态机和 UI 展示，反映当前在做什么。
- 在 kagent 里：这是 kagent 自己的命名/概念：code_agent.py:79-87 定义的状态机枚举 STARTING/INSPECTING/PLANNING/EDITING/VALIDATING/REPAIRING/FINALIZING/STOPPED；_set_phase 在工具循环里按当前工具类型切换并发 agent_status 事件给 UI 显示。
- 面试怎么用：可以说：我把 Agent 运行建模成显式 phase 状态机(如 INSPECTING/EDITING/VALIDATING)，每步切换会发事件给 UI 展示进度。

**final_trust**

- 是什么：对一次 Agent 运行最终可信度的评估总结：是否完成、改动是否经验证、是否有失败工具/循环告警等，作为质量门。
- 在 kagent 里：这是 kagent 自己的命名/概念：final_trust.py 的 build_final_trust_summary 生成 health(pass/warn/fail)、trustworthy、issues、quality_gate 等字段；code_agent.py _finish_run_with_trust_check 在每次 run 结束时计算并 emit final_trust_check 事件，final_trust_prompt 注入最终回答提示，强制模型披露未通过项、不得谎称验证通过。
- 面试怎么用：可以说：我在 Agent 收尾做了 final_trust 信任检查——基于是否改了代码、是否验证、是否还有失败工具生成 health 和 quality_gate，并在最终回答里强制披露残留风险。

**reasoning_effort**

- 是什么：控制推理模型 思考多少 的参数，值越大模型花越多算力做内部推理再回答。
- 在 kagent 里：config.py:15 REASONING_EFFORT_OPTIONS=[low,medium,high,xhigh]，默认 medium；llm.py 把它作为 reasoning_effort 参数传给 OpenAI chat.completions.create；runtime_metadata_prompt 把当前 effort 告诉模型，normalize_reasoning_effort 做校验归一化。
- 面试怎么用：可以说：我支持 reasoning_effort(low/medium/high/xhigh) 调节模型思考深度，按任务复杂度选档以平衡质量与成本。

**fallback / 降级回退**

- 是什么：主路径失败时自动切换到备用方案继续执行，而非直接报错退出。
- 在 kagent 里：llm.py create_chat_completion_with_reasoning 的回退逻辑：若首次因 reasoning_effort 不被支持报错(_is_unsupported_reasoning_error)，则去掉 reasoning 参数重试(fallback_without_reasoning=True)，让 Agent 在不支持推理的模型上也能继续跑。
- 面试怎么用：可以说：我对 reasoning_effort 做了 fallback——模型不支持该参数时自动去掉它重试，保证跨模型可用性。

**stream / 流式**

- 是什么：模型逐段增量返回输出而非等整段生成完，让前端能边生成边显示。
- 在 kagent 里：llm.py open_chat_stream 和 code_agent.py _stream_assistant_message 都用 stream=True 调 OpenAI；stream_chat 逐 chunk yield delta.content，agent_stream.aggregate_chat_completion_stream 聚合流并把文本增量经 on_text_delta 即时 emit 给 UI。
- 面试怎么用：可以说：我用流式 stream 让模型输出边生成边显示，UI 体验更顺，同时聚合流也能正确解析出 tool_calls。

**token**

- 是什么：模型处理文本的最小计费/计量单位，约等于一个词根或几个字符；上下文以 token 计量。
- 在 kagent 里：context.py:31 estimate_text_tokens 用 (ascii_chars + non_ascii_chars*2)//4 的轻量估算（无 tokenizer 依赖，非 ASCII 如中文按 2 倍计），manage_context 用 estimate_messages_tokens 预估消息总 tokens 与 max_tokens 比较超预算则压缩——这是上下文水位线的度量单位。
- 面试怎么用：可以说：我用一个无依赖的 chars/4 估算器近似 token 数做上下文预算预检，避免依赖外置 tokenizer。

**context window / 上下文窗口**

- 是什么：模型单次请求能容纳的最大 token 数(系统提示+历史+工具结果都要塞进来)。
- 在 kagent 里：config.py:27 CONTEXT_MAX_TOKENS=24000 即窗口预算；context.py:66 manage_context 拿它做水位判断，original_tokens<=max_tokens 则不压缩否则触发 compaction；_trim_until_within_budget 逐条裁剪到预算内。
- 面试怎么用：可以说：我用 CONTEXT_MAX_TOKENS=24000 作为上下文预算，超过就触发摘要压缩，保证不撑爆模型窗口。

**embedding / 向量嵌入**

- 是什么：把文本映射成高维向量的技术，向量相近代表语义相近，用于检索/相似度匹配。
- 在 kagent 里：通常指把文本转成向量做语义检索；但 kagent 故意没用它——failure_memory.py:79 注释明确 no embedding API，改用 TF-IDF+余弦，理由是单开发者工具语料小、要可复现无外部依赖。
- 面试怎么用：可以说：我评估过 embedding 检索，但语料小、要可复现无依赖，所以选了 TF-IDF+余弦这种轻量方案。

**TF-IDF**

- 是什么：词频-逆文档频率，一种把文本转成向量表示的统计方法，强调在一篇里常出现但在全语料里少见的词。
- 在 kagent 里：failure_memory.py:226 _tfidf_vector 和 :215 _compute_idf 实现：对每条失败记录的 text()(nodeid+failure_type+message+symbols)做 tokenize，算 TF×IDF 向量，作为相似失败检索的向量表示。
- 面试怎么用：可以说：失败记忆用 TF-IDF 把失败记录向量化，再做相似度匹配，无需训练或外部依赖。

**余弦相似度 / cosine similarity**

- 是什么：用两向量夹角余弦衡量相似度，值越接近1越相似，常用于文本/向量检索。
- 在 kagent 里：failure_memory.py:237 _cosine(a,b)：对查询向量和每条记录向量算点积除以两向量模长，按 score 降序取 top-k 作为相似失败匹配结果(:108-114)。
- 面试怎么用：可以说：相似失败检索用余弦相似度打分，按相似度降序返回 top-k 历史失败给 Agent 参考。

**insufficient_corpus**

- 是什么：这是 kagent 自己的 reason 字符串，指失败记忆语料太少(记录数低于阈值)不足以做可靠相似检索。
- 在 kagent 里：这是 kagent 自己的命名/概念：failure_memory.py:97 当记录数 < _MIN_CORPUS_FOR_RECALL(=3) 时 recall 诚实地返回 {ok:False, reason:insufficient_corpus, ...}，而不是返回噪音近重复——代码注释明确说这是为了避免假阳性。
- 面试怎么用：可以说：检索会判 insufficient_corpus——语料不足时直接告知而非硬凑结果，避免误导。

**failure_memory / 失败记忆**

- 是什么：这是 kagent 自己的命名/概念：把历史失败用例(测试失败+符号影响+修复提示)建成可检索记忆，让 Agent 复用过去的修复经验。
- 在 kagent 里：这是 kagent 自己的命名/概念：failure_memory.py 的 FailureMemoryIndex——从 STATE_DIR/runs/*.jsonl 收集 test_case_result(failed/error) 记录，建 TF-IDF 索引；code_agent.py 通过 recall_similar_failures 工具暴露给模型，让 Agent 遇到失败时能 recall 历史相似失败和 fix_hint。
- 面试怎么用：可以说：我做了 failure_memory——从历史 run 的失败用例建 TF-IDF 索引，Agent 遇到失败可 recall 相似历史失败及修复提示。

**QThread**

- 是什么：PyQt6 的后台线程类，把耗时任务挪出主(UI)线程，防止界面卡死。
- 在 kagent 里：kagent/ui/agent_worker.py:3 from PyQt6.QtCore import QThread；AgentWorker(QThread)(:18) 在 run() 里阻塞调用 agent.run，避免 LLM 长耗时阻塞界面；用户停止通过 stop() 置 _stop 标志。
- 面试怎么用：可以说：Agent 跑在 QThread 后台线程，避免阻塞主 UI 线程，靠信号把进度送回界面。

**pyqtSignal**

- 是什么：PyQt6 的线程间通信信号机制，后台线程 emit、UI 线程 connect，实现跨线程安全更新界面。
- 在 kagent 里：kagent/ui/agent_worker.py:21-25 定义 chunk/tool_event/done/error/title_ready 五个信号；run() 里把 tool_event.emit 当 on_event、chunk.emit 当 on_text_delta 传给 agent.run，UI 主线程 connect 这些信号即可安全更新界面。
- 面试怎么用：可以说：我用 pyqtSignal 把后台 Agent 的工具事件和文本增量发回主线程更新 UI，线程安全。

**EventFn**

- 是什么：这是 kagent 自己的命名/概念：事件回调函数类型，签名 (dict)->None，供 Agent 把工具调用/状态/结果等事件发给 UI 层。
- 在 kagent 里：这是 kagent 自己的类型别名：code_agent.py:74 EventFn = Callable[[dict[str, Any]], None]；agent.run 把结构化事件(如 tool_start/tool_result/agent_status/final_trust_check)经 on_event 回调发出，ui/agent_worker.py 把它接到 tool_event pyqtSignal 上转发给 UI。
- 面试怎么用：可以说：Agent 对外用 EventFn 回调发结构化事件，UI 层订阅这些事件渲染工具调用、阶段、最终信任检查。

**should_stop**

- 是什么：这是 kagent 自己的命名/概念：停止回调函数类型，返回 True 表示用户要求中止当前 Agent 运行。
- 在 kagent 里：这是 kagent 自己的命名/概念：code_agent.py:75 StopFn = Callable[[], bool]；run(...,should_stop=None) 在 :1557、:1837 每轮/每工具前调 should_stop()，True 则切 STOPPED 并 finish_run_with_trust_check(stopped)；ui/agent_worker.py 传入 lambda: self._stop，用户点停止即置 _stop。
- 面试怎么用：可以说：Agent 主循环每轮都查 should_stop 回调，用户可随时中断，中断也会走信任检查收尾。

**INSPECTION_TOOLS**

- 是什么：这是 kagent 自己的命名/概念：只读、不改动工作区的探查类工具集合，用于收集上下文。
- 在 kagent 里：code_agent.py:167 INSPECTION_TOOLS 集合(list_files/search_file/find_symbol/find_symbol_context/find_symbol_references/symbol_change_plan/read_file/measure_coverage/recall_similar_failures 等)；主循环 :1906 命中则置 state.inspected=True、phase=INSPECTING，且编辑前强制先做 inspection(:1717)。
- 面试怎么用：可以说：我把只读工具归为 INSPECTION_TOOLS，并强制 改前先查，降低盲改风险。

**MUTATION_TOOLS**

- 是什么：这是 kagent 自己的命名/概念：会改动工作区文件系统的工具集合，每类都触发改动追踪与回滚快照。
- 在 kagent 里：code_agent.py:195 MUTATION_TOOLS 集合(write_file/apply_patch/rename_path/copy_path/delete_path/make_directory/rollback_*)；主循环 :1915 命中且成功则置 state.mutated=True、更新 changed_paths、重置 validation 状态(改完需重新验证)。
- 面试怎么用：可以说：MUTATION_TOOLS 一旦成功就标记已改动并重置验证状态，强制重新校验，保证改后必验。

**CONTENT_EDIT_TOOLS**

- 是什么：这是 kagent 自己的命名/概念：直接修改文件内容(而非路径操作)的子集，触发 content_changed 标记、要求重新验证。
- 在 kagent 里：code_agent.py:188 CONTENT_EDIT_TOOLS 集合(write_file/apply_patch/rollback_*)；主循环 :1926 命中则置 state.content_changed=True、validated=False、并清零 validation_repair_attempts/last_validation_summary——内容一变就要重新跑完整验证。
- 面试怎么用：可以说：我把真正改文件内容的工具单独成 CONTENT_EDIT_TOOLS，一旦触发就重置验证状态，确保改后必重验。

**VALIDATION_TOOLS**

- 是什么：这是 kagent 自己的命名/概念：用于跑测试/命令验证改动的工具集合，结果决定 validated/validation_failed 状态。
- 在 kagent 里：code_agent.py:206 VALIDATION_TOOLS={run_command}；主循环 :1936 命中则置 state.validated、按 returncode 设 validation_failed，:1844 命中切 phase=VALIDATING；_run_auto_validation 也用它跑自动验证命令。
- 面试怎么用：可以说：VALIDATION_TOOLS 目前就是 run_command，成功与否直接决定验证通过与否并驱动修复循环。

## 符号/代码智能 域

**AST (Abstract Syntax Tree / 抽象语法树)**

- 是什么：抽象语法树，把源码解析成一棵树状结构，程序里每个类/函数/赋值都变成一个可遍历的节点，让程序能像理解数据一样理解代码结构，而不是当字符串看。
- 在 kagent 里：这是业界通用概念在 kagent 的实现：symbol_index.py 的 _SymbolVisitor 继承 ast.NodeVisitor，在 visit_ClassDef/visit_FunctionDef 里把每个类/函数/方法抽成 Symbol(name/kind/path/line/end_line/container)。Python 用真 AST(ast.parse)，JS/Go/Rust/Java 用正则按行匹配(_symbols_from_javascript_like 等)。
- 面试怎么用：被问代码智能怎么做时说：我先用 Python ast 把源码解析成 AST 抽出符号表，其它语言退化为正则，保证多语言都能建符号索引。

**symbol_change_plan (符号变更计划)**

- 是什么：符号变更计划，指在修改一个函数/类之前先生成一份清单：这个符号定义在哪、被哪些文件引用、相关测试有哪些、风险多大、该跑什么验证。
- 在 kagent 里：这是 kagent 自己的命名：symbol_change_plan.py:11 的 build_symbol_change_plan() 是一个只读 INSPECTION 工具，输入符号名，输出一份结构化变更计划——定义位置、引用列表、相关测试、风险等级、验证命令，让 agent 改符号前先看影响面。
- 面试怎么用：说我在改函数前不是直接动手，而是先调 symbol_change_plan 拿到这个符号的所有引用和相关测试，基于影响面决定改动范围。

**symbol_impacts (符号影响)**

- 是什么：符号影响，指改动某个符号后波及的范围——哪些文件引用了它、多少产线代码受影响、多少测试受影响。
- 在 kagent 里：这是 kagent 自己的命名：symbol_change_plan.py:106 的 _impact_summary() 汇总——受影响文件数、产线引用数、测试引用数、引用类型分布，作为变更影响面的结构化总结塞进 plan 的 impact_summary 字段。
- 面试怎么用：说我做了符号级影响分析：聚合定义/引用/相关测试成 impact_summary，给变更一个量化影响面，而不是凭感觉改。

**impact_score (影响分)**

- 是什么：影响分数，一个 0-100 的数值，量化改一个符号的风险大小，分越高越危险。
- 在 kagent 里：这是 kagent 自己的命名：symbol_change_plan.py:147 的 _impact_score() 用加权公式打分——定义不存在 +25、多定义 +15、产线引用每条 +4(上限35)、受影响文件 +3(上限20)、测试引用 +2(上限12)、有产线引用却无相关测试 +15，封顶100。
- 面试怎么用：说我给符号改动设计了量化风险评分，把引用数/受影响文件数/有无测试覆盖加权成 impact_score，避免只看引用数误判。

**risk_level (风险等级)**

- 是什么：风险等级，把连续的影响分归档成 low/medium/high 这类离散标签，便于人和 agent 快速判断。
- 在 kagent 里：这是 kagent 自己的命名：symbol_change_plan.py:168 的 _risk_level() 把 impact_score 分三档——>=65 high、>=25 medium、其余 low，塞进 plan 的 risk_level 字段给 agent 和人看。
- 面试怎么用：说我把影响分映射成 high/medium/low 三档风险等级，让 agent 根据风险等级决定要不要先跑测试再改。

**nodeid (pytest 测试节点 ID)**

- 是什么：pytest 里的测试唯一标识，格式通常是 '文件路径::测试名'(如 tests/test_x.py::test_foo)，定位到具体某个测试用例。
- 在 kagent 里：kagent 用 pytest 的 nodeid 作为测试唯一标识：test_telemetry.py 的 _nodeid() 把 JUnit XML 的 classname/name/file 合成 'path::test_name' 形式；run_analytics.py 用 nodeid 作 key 聚合每个测试的耗时/状态历史，做 timing regression 和 flaky 检测。
- 面试怎么用：说我做 per-test 分析时用 pytest nodeid(文件::测试名)作主键，跨 run 聚合每个测试的耗时和成败状态。

**find_symbol_references (查找符号引用)**

- 是什么：查找符号引用，给定一个函数/类名，在整个代码库里找出所有用到它的地方(调用、导入、属性访问)。
- 在 kagent 里：这是 kagent 的核心符号工具：symbol_index.py 的 find_symbol_references() 在全项目扫描某符号的所有引用——Python 用 AST 的 _ReferenceVisitor 识别 import/call/name/attribute 四类引用，其它语言退化为正则按行匹配(_line_references)，结果带 is_test 标记区分产线/测试引用。
- 面试怎么用：说我用 AST visitor 走一遍找出符号的调用点/导入点/属性引用，非 Python 退化为正则，symbol_change_plan 就靠它拿引用列表。

**container (容器/父作用域)**

- 是什么：容器，指一个符号所属的外层作用域——比如一个方法的 container 是它所在的类，一个嵌套函数的 container 是它的父函数。
- 在 kagent 里：这是 kagent 自己的命名：Symbol 数据结构的 container 字段记录符号所属父作用域链，_SymbolVisitor._container() 用 '.'.join(self.containers) 拼出，如 'MyClass.my_method'；用来区分顶层函数和类内方法('method' if self.containers else 'function')。
- 面试怎么用：说我抽符号时记录了它所在的 container 父链(类名.方法名)，用来区分顶层函数和类内方法、定位符号位置。

## 验证/测试 域

**pytest**

- 是什么：Python 最主流的测试框架，用 assert 写断言、用 fixture 做前后置、自动发现 test_ 开头的函数/类，一条命令跑全部测试。
- 在 kagent 里：kagent 的验证主战场：coverage.py 的 measure_coverage() 用 'coverage run -m pytest' 跑测试拿覆盖率；symbol_change_plan.py 的验证命令也是 pytest；test_gen.py 生成 pytest 脚手架并用 --collect-only 验证可发现。
- 面试怎么用：说我整个验证体系跑在 pytest 上：测真实覆盖率、跑符号相关测试、生成的脚手架也要能被 pytest 收集。

**JUnit XML / junit (JUnit XML 报告)**

- 是什么：pytest 等测试框架可导出的一种 XML 格式，标准化记录每个测试用例的成败、耗时、失败信息，便于 CI 系统和工具解析。
- 在 kagent 里：kagent 的 per-test 数据来源：test_telemetry.py:10 的 prepare_pytest_junit_command() 给 pytest 命令自动加 --junitxml 参数（:30）输出到 .kagent/test-results/，parse_junit_xml()（:45）解析每个 testcase 成 {nodeid, status, duration_ms, ...}，喂给 run_analytics 做 flaky/timing 分析。
- 面试怎么用：说我想拿到 per-test 耗时和成败做趋势分析，就给 pytest 自动加 --junitxml，再解析 XML 转成结构化测试结果。

**test_case_result (测试用例结果)**

- 是什么：测试用例结果，指单个测试用例的运行结果记录，至少包含用例标识、状态(passed/failed/error)、耗时。
- 在 kagent 里：这是 kagent 自己的运行事件类型：run_analytics.py:268 处理 event=='test_case_result' 的事件，每个事件 data 含 nodeid/status/duration_ms，是从 JUnit XML 解析后写进 run_log 的；是 per-test 遥测的基础数据单元。
- 面试怎么用：说我把每个 JUnit testcase 转成一条 test_case_result 事件写进 run_log，作为 per-test 耗时/成败/趋势分析的最小数据单元。

**flaky (不稳定测试)**

- 是什么：不稳定测试，指同一个测试在同一代码上时过时失败(今天绿明天红)，通常是测试依赖了时序/网络/顺序等不可控因素。
- 在 kagent 里：run_analytics.py:306 的 _flaky_tests() 实现——要求一个 nodeid 至少跨 3 次运行(_FLAKY_MIN_RUNS=3)，且既有 pass 又有 fail(pass_rate 严格在 0 和 1 之间)；全 fail 算 regression 不算 flaky，全 pass 算 stable。
- 面试怎么用：说我做了 flaky 检测：跨 run 聚合每个测试成败，只把既有 pass 又有 fail 的标 flaky，全 fail 的归为 regression 而非 flaky。

**timing regression (耗时回归)**

- 是什么：性能回归，指一个测试或命令随时间变慢了——同样的代码以前跑 100ms 现在跑 300ms，通常是某次改动引入了性能问题。
- 在 kagent 里：run_analytics.py:391 的 _timing_regressions() 实现——取最近 5 次(_TIMING_BASELINE_WINDOW=5)做中位数基线，当最新一次耗时既 >=1.5 倍基线(_TIMING_REGRESSION_RATIO)又绝对增量 >=200ms(_TIMING_MIN_DELTA_MS)时才报警，双阈值避免快测试被抖动误报。
- 面试怎么用：说我用中位数基线 + 双阈值(1.5 倍且 +200ms)检测性能退化，避免慢测试被绝对抖动误报、快测试被比例抖动误报。

**median baseline (中位数基线)**

- 是什么：中位数基线，用历史若干次运行耗时的中位数作为正常值基准，相比均值更抗极端值干扰。
- 在 kagent 里：run_analytics.py:405 的 baseline = _median(window)：取最近 5 次耗时的中位数作基线，不用均值；中位数抗 outlier，一个偶发卡顿不会把基线拉高导致漏报。
- 面试怎么用：说我没用均值做基线而是用中位数，因为均值会被偶发卡顿拉高导致性能回归漏报，中位数更抗 outlier。

**coverage (代码覆盖率)**

- 是什么：代码覆盖率，跑完测试后统计有多少行/分支被真正执行到，衡量测试集覆盖产品代码的比例。
- 在 kagent 里：coverage.py 的 measure_coverage() 用 'coverage run --source=. -m pytest' 跑测试采集覆盖，再 'coverage json' 导出真实 line_rate/branch_rate(无测试返回 None)；test_gen.py 的 find_untested_symbols() 反向用它做覆盖缺口扫描。
- 面试怎么用：说我用 coverage 工具跑 pytest 拿真实行覆盖率，无测试时优雅返回 None 而不是崩，下游也基于真实覆盖数据决策。

**line_rate (行覆盖率)**

- 是什么：行覆盖率，覆盖率指标的一种，指被执行到的代码行数占总可执行行数的比例(如 0.85 表示 85% 的行被测到)。
- 在 kagent 里：这是 kagent 自己的字段：coverage.py measure_coverage 返回的 line_rate，把 coverage 报的 percent_covered 归一化到 0-1(_to_rate)；validation.py:534 的 coverage_bonus 也用它做真实加分。
- 面试怎么用：说我把覆盖率从 0-100 归一化成 0-1 的 line_rate，既用于覆盖率回归 gate 也用于验证命令排序的真实加分。

**coverage_bonus (覆盖率加分)**

- 是什么：覆盖率加分，在验证命令排序时给覆盖率高/全量的命令额外加分，鼓励优先跑覆盖好的验证。
- 在 kagent 里：这是 kagent 自己的命名：validation.py:532 的 coverage_bonus，曾是写死标签加分，现已改成真实 line_rate*0.18(:535)，只给 'Project verification'/'Pytest suite' 这类全量命令加，让排序反映真实覆盖而非假标签。
- 面试怎么用：说我把验证命令排序里的 coverage_bonus 从写死标签换成真实测到的 line_rate，避免假指标误导命令优先级。

**regression gate (回归门禁)**

- 是什么：回归门禁，一个自动检查：当代码覆盖率相比基线下降超过阈值时拦截/警告，防止新增代码没被测试覆盖。
- 在 kagent 里：这是 kagent 自己的命名：coverage.py 的 coverage_regression_gate()，对比 trend 里的 recent_line_rate vs baseline_line_rate，当 delta <= -0.03(下降 >=3%)时判 'warn'，否则 pass；在 code_agent.py 被调用。
- 面试怎么用：说我做了覆盖率回归 gate：把最近覆盖率跟历史均值比，下降超 3 个百分点就 warn，挡住"改了代码却没测"的提交。

**test generation (测试生成)**

- 是什么：测试生成，根据产品代码自动产出测试代码的辅助能力——通常生成测试骨架，由人或 AI 补断言。
- 在 kagent 里：kagent 的两个只读测试生成工具(INSPECTION_TOOLS)：test_gen.py 的 find_untested_symbols() 扫覆盖缺口、generate_test_scaffold() 读 AST 生成 pytest 脚手架，注册在 code_agent.py 的 scaffold_test_for_symbol。
- 面试怎么用：说我做了 AI 辅助测试生成：先扫覆盖缺口找未测符号，再为它生成 pytest 脚手架，把人从写样板代码里解放出来专注断言。

**scaffold (脚手架)**

- 是什么：脚手架，自动生成的测试骨架代码——有导入、有空测试函数、有 TODO 占位，但没有真实断言，等人/agent 补完。
- 在 kagent 里：test_gen.py 的 generate_test_scaffold() 生成的内容(_render_scaffold)：导入被测模块 + 每个可测符号一个占位 def test_x(带 TODO + assert True)，故意不编造假断言以免虚假信心；不自动写文件，需 write_file 保存后用 pytest --collect-only 验证可发现。
- 面试怎么用：说我生成的是 pytest 脚手架——导入+占位测试+TODO，刻意不造假断言，让人或 agent 补真实预期，避免假绿。

**--junitxml (pytest 参数)**

- 是什么：(已并入 JUnit XML 条目)pytest 的命令行参数，让 pytest 把测试结果以 JUnit XML 格式写到指定文件，供下游工具解析。
- 在 kagent 里：见 JUnit XML / junit / --junitxml 条目——test_telemetry.py:30 prepare_pytest_junit_command 给直接 pytest 命令自动拼上 --junitxml="<路径>"，输出到 .kagent/test-results/<run_id>-<seq>-<idx>.xml，再由 parse_junit_xml 解析；非直接 pytest(如 verify.ps1 脚本)不强行加。
- 面试怎么用：同 JUnit XML 条目。

**compileall (Python 批量编译)**

- 是什么：Python 标准库模块，批量把 .py 编译成 .pyc，顺带做语法检查——能快速发现整个目录的语法错误而不用真跑。
- 在 kagent 里：Python 标准库的批量字节编译工具，kagent 用作语法检查：validation.py 的 'Python compileall' 命令对批量源文件跑 compileall，verify.ps1:16 也用 'compileall -q' 做编译检查；与 py_compile(单文件)配套。
- 面试怎么用：说我用 py_compile 查单文件语法、compileall 批量编译，在跑测试前先卡住语法错误这一层。

## 上下文/记忆 域

**水位线 / water level**

- 是什么：水位线，比喻一个预算阈值/进度标记——上下文涨到水位就要压缩，或用一个消息 id 标记"已摘要到哪"。
- 在 kagent 里：kagent 里有两层水位：① context.py:80 manage_context 用 max_tokens(24000)作预算水位，超了就压缩旧消息；② db.py:62 context_summaries 表的 through_message_id 作"已摘要到哪条"的水位线，prepare_session_history 只处理 id 大于它的新消息，回写新水位。
- 面试怎么用：说我用 token 预算水位触发压缩，又用 through_message_id 水位线记录"摘要到哪条"，跨会话恢复时只增量处理新消息。

**manage_context**

- 是什么：这是 kagent 自己的函数名：调模型前对消息历史做预算检查，超 token 就摘要压缩旧消息、保留近期消息。
- 在 kagent 里：context.py:58 的核心函数；code_agent.py:235 _prepare_model_messages 和 llm.py:177 open_chat_stream 都在调模型前调用它，按 max_tokens/keep_recent_messages/summary_max_chars/per_message_max_chars 做压缩与裁剪，返回 (managed_messages, stats)。
- 面试怎么用：可以说：每轮调模型前我都过一遍 manage_context 做预算检查与摘要压缩，保持上下文不超限。

**context_compacted**

- 是什么：标志位，表示本次上下文管理实际触发了摘要压缩(消息被折叠成 Earlier context compacted 段)。
- 在 kagent 里：context.py:75/111 manage_context 返回的 stats.compacted 标志，code_agent.py:242 据此发 agent_status 事件 Context compacted (X -> Y estimated tokens)，并把压缩结果写回 messages[:]；db 端 agent_worker.py:166 还会 save_context_summary 持久化摘要。
- 面试怎么用：可以说：压缩发生时我会发 Context compacted 事件并持久化摘要，下次会话直接复用。

**上下文工程 / context engineering**

- 是什么：上下文工程，指主动管理喂给 LLM 的上下文——哪些信息保留、哪些压缩、哪些丢弃——让长会话既不超 token 预算又不丢关键信息。
- 在 kagent 里：kagent 用四道水位线把无限上下文控制进有限预算：① tool_result_context.py 截断工具结果(设 context_compacted 标志)；② context.py:58 manage_context 按 CONTEXT_MAX_TOKENS=24000 压缩；③ project_memory/project_rules 注入记忆；④ db.py context_summaries 跨会话滚动摘要(through_message_id 水位增量)。
- 面试怎么用：说我的 agent 没有硬塞全部历史，而是做了四道水位线的上下文工程：截断、压缩、记忆注入、跨会话摘要，保信息密度不超预算。

**manage_context (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：context.py:58 的 manage_context()，核心上下文管理函数，发模型前按预算压缩历史消息。
- 在 kagent 里：这是 kagent 自己的命名：context.py:58 的 manage_context()，发模型前按 max_tokens 预算把旧消息折叠成摘要、保近期 keep_recent_messages 条 + system 前缀；_summarize_messages 每条抽 role+关键字段，_trim_until_within_budget 兜底裁剪到预算内。
- 面试怎么用：说我每次发模型前跑 manage_context 按 token 水位压缩旧消息成摘要、保近期对话，保证长会话不超预算也不丢近期关键信息。

**context_compacted (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：布尔字段，标记该工具结果或对话历史是否经过裁剪/摘要压缩。
- 在 kagent 里：这是 kagent 自己的命名：tool_result_context.py 里每个 _compact_* 函数都会设 context_compacted 布尔字段，标记"工具结果是否被裁剪过"，让 agent/前端知道原始输出被截断(如 run_command 保头尾+抽错误行，错误信息永不丢)。另有 context.py manage_context 压缩时 stats.compacted 同名标志，二者语义一致。
- 面试怎么用：说我给每个工具结果设了 context_compacted 标志，标记是否被裁剪，并保证错误行永远保留不丢。

**project_memory (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：长期项目记忆——项目类型、源码/测试数、入口/配置文件、验证命令。
- 在 kagent 里：这是 kagent 自己的命名：project_memory.py 的 build_project_memory() 聚合项目结构(project_map summary)、入口文件、配置文件、验证命令、偏好；load_or_refresh_project_memory DB 缓存(db.py project_memories 表，每工作区一条 upsert)；format_project_memory_for_prompt 注入时显式"prefer current files"防记忆漂移。
- 面试怎么用：说我把项目结构/验证命令/偏好沉淀成 project_memory 注入 prompt 作稳定背景，并显式提醒"以当前文件为准"防记忆漂移。

**context_summaries (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：db.py:59 的 context_summaries 表，跨会话持久化的对话摘要。
- 在 kagent 里：这是 kagent 自己的命名：db.py:59 的 context_summaries 表，每会话一条(session_id PRIMARY KEY，upsert)，存 summary/through_message_id/source_message_count；save_context_summary 用 INSERT...ON CONFLICT 更新，get_context_summary 读出，prepare_session_history 折叠回 prompt。
- 面试怎么用：说我用 context_summaries 表做跨会话滚动摘要，每会话一条 upsert，用 through_message_id 水位增量，重启后只处理新消息。

**KAGENT.md (项目规则文件)**

- 是什么：kagent 读取的项目级规则文件(类似 CLAUDE.md)，告诉 agent 这个项目的编码规则、验证命令、安全约束。
- 在 kagent 里：kagent 的项目级规则文件：project_rules.py:9 RULES_FILENAME='KAGENT.md'；load_project_rules 读它注入 system 消息；check_project_rules 对它做健康度体检(4 必需 section + 验证命令 + 文档规则，score=100-high×30-medium×15)；缺失时 generate_project_rules 生成草稿但 agent 不擅自改。
- 面试怎么用：说我设计了 KAGENT.md 规则系统：读/生成/体检三层闭环，agent 可见规则健康度但显式禁止自己改，划定可见性 vs 写权限边界。

**task_plan (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：显式执行清单——把任务拆成有序步骤带状态。
- 在 kagent 里：这是 kagent 自己的命名：task_plan.py 的 build_task_plan() 硬编码 4-5 步模板 understand→inspect→make→validate→final，_task_profile 用关键词启发式抽 files/risks/validation 注入步骤，set_plan_step 状态机推进，plan_for_model 每轮渲染成 markdown checklist 注入 system。
- 面试怎么用：说我的 agent 有硬编码 task_plan 骨架保证"先读后改后验后汇报"不可绕过，尤其 validate 不被跳过，是半自主而非全自主分解。

**task_resume (kagent 内部命名)**

- 是什么：这是 kagent 自己的命名：长任务断点恢复——从上次 run 日志重建上下文。
- 在 kagent 里：这是 kagent 自己的命名：task_resume.py 的 build_resume_context() 从 run_log 重建恢复上下文——读事件、健康分析、plan 快照、_resume_priority 算优先级(如 fix_validation_failure/run_validation/recover_failed_tool)、_resume_prompt 生成恢复提示。
- 面试怎么用：说我做了 task_resume 长任务恢复：从上次 run_log 重建 plan 快照和优先级，让 agent 从断点续跑而非从头重来。

**upsert (插入或更新)**

- 是什么：Insert or Update——一条记录存在就更新、不存在就插入，避免"先查再决定插还是改"的两次操作。
- 在 kagent 里：db.py:227 的 save_context_summary 用 'INSERT...ON CONFLICT(session_id) DO UPDATE SET...' 实现 upsert——主键冲突就更新而非报错；project_memories/workspace_root、context_summaries/session_id 都靠 upsert 保证"每会话/每工作区一条"天然成立。
- 面试怎么用：说我用 SQLite 的 ON CONFLICT upsert 模式保证"每会话/每工作区一条"天然成立，不用先查再插再更新三步走。

## 安全/审计 域

**risk_policy / 风险策略**

- 是什么：风险策略：对一个工具调用做风险评估、定风险等级、决定是否需要人工批准的安全规则集合。是 agent 安全层的第一道闸门。
- 在 kagent 里：kagent 自己的命名/概念。risk_policy.py 是风险定级引擎：tool_policy()(risk_policy.py:141) 按工具名+参数给出 risk_level/approval_required/destructive 三件套，命令走 _command_tool_policy() 按模式匹配 CRITICAL/NETWORK/GIT_WRITE 等分类，apply_patch 按 file_count/总改动行数/是否敏感路径定级。5 档由 RISK_LEVELS(risk_policy.py:8: safe/low/medium/high/critical)定义。
- 面试怎么用：可说：我给 agent 的每个工具调用都接了 risk_policy，按工具语义和 diff 规模分 5 档风险并决定是否要用户审批，把危险动作挡在执行前。

**tool_policy / 工具策略**

- 是什么：工具策略：针对单个工具调用算出来的风险评估结果对象(等级+是否需批准+是否破坏性+原因)。
- 在 kagent 里：kagent 自己的命名/概念。指 risk_policy.py:141 的 tool_policy(name,args,display_args,preview_text) 函数及其返回的 dict(risk_level/approval_required/destructive/reason/risk_categories)。它是 risk_policy 的具体计算入口。
- 面试怎么用：可说：每次工具调用前我都跑一遍 tool_policy 函数算出该动作的等级和是否需审批，UI 据此决定直接执行还是弹审批。

**approval_required / 需人工批准**

- 是什么：是否需要人工批准：高风险/破坏性动作执行前必须用户点确认的标志位。
- 在 kagent 里：risk_policy.py 在 _build_tool_policy 里：approval_required 默认为 destructive 或等级>=medium 时为 True。只读工具(INSPECTION_TOOLS)和低风险动作显式设 False。UI 看到该字段为 True 时弹人工确认。
- 面试怎么用：可说：risk_policy 算出 approval_required=True 的动作会先弹确认框，用户放行才执行，避免 agent 自行删除或改敏感文件。

**destructive / 破坏性**

- 是什么：破坏性：该动作会删除/覆盖/不可逆地改变文件或环境，属于最危险的一类操作。
- 在 kagent 里：risk_policy.py:251/256 delete_path 置 destructive=True 并标 critical；CRITICAL_COMMAND_PATTERNS(:78，如 rm -rf/git reset --hard)也置 destructive=True。destructive 的动作默认 approval_required=True。
- 面试怎么用：可说：我把删除、rm -rf 这类标记 destructive 并强制审批，且每次执行前都先拍快照保证可回滚，破坏性操作不裸跑。

**rollback / 回滚**

- 是什么：回滚：把工作区文件恢复到之前某个保存点，撤销 agent 的某次改动。是 agent 安全网的兜底能力。
- 在 kagent 里：workspace.py 的 rollback 体系：_capture_restore_states() 改文件前先存快照并写一条 rollback_entries 记录；rollback_last_change/rollback_change/rollback_paths 从快照恢复。apply_patch/write_file/delete_path 等都会 _save_restore_rollback。
- 面试怎么用：可说：agent 每次写文件前先存原始内容快照入库，用户可按 rollback 条目回退任意一次改动，相当于给 agent 装了撤销键。

**snapshot / 快照**

- 是什么：快照：改动前对原文件/目录做的一份完整拷贝，作为回滚的还原源。这里不是内存快照而是文件系统副本。
- 在 kagent 里：workspace.py:176 _capture_path_state 用 shutil.copy2/copytree 把要改的文件原样拷到 rollback 目录；快照根目录由 _snapshot_root_for_token(:154) 按 token 分隔存放在 ROLLBACK_ROOT/session_id 下。恢复时 _restore_path_state 从快照拷回。
- 面试怎么用：可说：我做的是文件级快照——改动前把原始文件拷到 rollback 目录，回滚时按快照还原，不依赖 git，对非 git 工作区也适用。

**superseded / 被取代**

- 是什么：被取代：当回滚到某个较早的改动点后，比它更晚的活跃回滚条目自动标记为已失效(superseded)，不再可单独回滚。
- 在 kagent 里：kagent 自己的状态语义。db.py:405 mark_rollback_entries_superseded_after 把比当前回滚条目更新的 active 条目置为 superseded(因为回滚到旧点会让后续改动失效)。preview 时 _rollback_preview_payload(workspace.py:985)会统计 superseded_active_count 给出警告。
- 面试怎么用：可说：回滚到较早的改动点会让之后的新改动失效，我标为 superseded 并在预览里提醒用户有多少条更新会被取代，避免静默丢改动。

**patch_recovery / 补丁恢复**

- 是什么：补丁恢复：apply_patch 失败后，自动分析失败原因、抽取要重读的文件、给 agent 下一步修复指引的机制。
- 在 kagent 里：kagent 自己的模块。patch_recovery.py 的 patch_failure_recovery 从失败 error 和 change_plan 提取目标路径，给出 category=patch_failed/retryable=True 和 read_targets(让 agent 重新读这几个文件再改)，patch_recovery_prompt 拼成提示注入下一轮。
- 面试怎么用：可说：apply_patch 失败时我专门做了 patch_recovery，自动从错误里抽目标文件、提示 agent 重读后用更小补丁重试，而不是盲目重试同一个补丁。

**tool_loop_guard / 工具循环守卫**

- 是什么：工具循环守卫：检测 agent 是否在重复调用同一个工具(尤其反复失败的)，发现后注入警告引导它换策略，防止死循环空转。
- 在 kagent 里：kagent 自己的模块。tool_loop_guard.py：tool_call_signature(:12)对工具名+归一化参数算 sha1 指纹；record_tool_call 记进环形历史(MAX_HISTORY=20)；loop_warning(:45)发现同一签名重复>=REPEAT_THRESHOLD(2) 且都失败就报 repeated_failed_tool，或只读工具重复>=3 次报 repeated_inspection。code_agent.py 集成。
- 面试怎么用：可说：为防 agent 卡在死循环里反复调用同一个失败工具，我做了 tool_loop_guard 用参数指纹检测重复调用并注入引导，逼它换思路。

**tool_recovery / 工具恢复**

- 是什么：工具恢复：单个工具调用失败后，按错误类型给出修复提示和是否可重试的判断，喂回给 agent 下一轮。
- 在 kagent 里：kagent 自己的模块。tool_recovery.py:9 is_tool_failure 判定失败(rejected/error/run_command 非零或超时)；recovery_hint_for_tool 按错误文本分类返回 hint(patch_failed/invalid_arguments/timeout/path_not_found/permission_scope…)，命令类转交 repair_strategy.classify_failure。
- 面试怎么用：可说：每个工具失败我都跑 tool_recovery 给出带 retryable 标志的具体修复指引，把错误从黑盒变成可被 agent 理解的下一步。

**failure_diagnostics / 失败诊断**

- 是什么：失败诊断：从命令输出/错误文本里用正则解析出失败位置(文件+行号+节点+消息)，结构化提取出来供后续定位。
- 在 kagent 里：kagent 自己的模块。failure_diagnostics.py:10 extract_failure_diagnostics 合并 stderr/stdout/error，用正则抽 pytest 失败节点、Python traceback(File "...", line N)、SyntaxError、file:line 四类，最多 MAX_DIAGNOSTICS=12 条。
- 面试怎么用：可说：验证失败时我用 failure_diagnostics 用正则从 pytest 输出和 traceback 里抽文件:行号，定位到具体失败位置再修，不让 agent 看一整屏日志瞎猜。

**failure_focus / 失败聚焦**

- 是什么：失败聚焦：把诊断结果转成"最该先读哪几段代码"的目标列表，引导 agent 聚焦到失败点附近而非满工作区乱搜。
- 在 kagent 里：kagent 自己的模块。failure_focus.py:11 focus_targets_from_diagnostics 取诊断里的 path/line，生成最多 MAX_FOCUS_TARGETS=3 个读取区间(默认前后 DEFAULT_CONTEXT_LINES=40 行)，并叠加 symbol_impacts 里的相关失败测试对应符号定义。focus_prompt 拼成提示让 agent 先读这些。
- 面试怎么用：可说：定位到失败点后我用 failure_focus 自动框出最相关的几个代码区间让 agent 先读，缩小搜索范围再修，省 token 也更准。

**repair_strategy / 修复策略**

- 是什么：修复策略：按失败类别给出对应修复方向的规则集，告诉 agent 针对这种失败该怎么修。
- 在 kagent 里：kagent 自己的模块。repair_strategy.py:7 classify_failure 按错误关键词分类为 missing_dependency/command_not_found/timeout/syntax_error/import_error/assertion_failure/runtime_error/test_failure/unknown_failure，每个配 next_step 修复策略。被 tool_recovery._command_failure_hint 调用。
- 面试怎么用：可说：对命令失败我做 repair_strategy 按错误类型分类并给差异化修复策略，比如缺依赖就提示装、断言失败就比预期对实际，而不是一刀切重试。

**classify_failure / 失败分类**

- 是什么：分类失败：把一段失败输出归到某个语义类别(断言失败/语法错误/缺依赖/超时…)的动作，是 repair_strategy 的入口。
- 在 kagent 里：kagent 自己的函数。repair_strategy.py:7 classify_failure(result_or_text)，返回 {category, next_step}。也支持直接传字符串。是 repair_strategy 的入口。
- 面试怎么用：可说：我的修复流程第一步是 classify_failure 给失败归类，归类决定后续 focus 和修复策略，把模糊的"失败了"变成可操作的分类。

**quality_gate / 质量门禁**

- 是什么：质量门禁：把一次 agent 运行各关键检查项(运行完成/改动已验证/无验证失败/工具失败已恢复/无模型错误等)汇总成一个 pass/warn/fail 的放行判定。
- 在 kagent 里：kagent 自己的概念。run_review.py:119 build_quality_gate 汇总各 check 状态定 pass/warn/fail；final_trust.py:88 build_quality_gate_summary 也产一份。code_agent 末端把 quality_gate 写进 run_finish 事件。UI 有 run_quality_gate_btn 触发展示(ui/main_window.py:2265)。
- 面试怎么用：可说：每次 agent 跑完我过一遍 quality_gate 检查项(是否完成、改动是否验证、有无失败工具/模型错误、KAGENT.md 是否健康)，fail 就不许宣称成功。

**run_log / 运行日志(JSONL)**

- 是什么：JSONL：每行一个 JSON 对象的日志文件格式(JSON Lines)。适合逐行追加事件流。
- 在 kagent 里：kagent 自己的运行日志。run_log.py 的 RunLogger 每次运行生成 run_id，写到 STATE_DIR/runs/<日期>-<run_id>.jsonl，逐行 append JSON 事件(run_start/tool_call/model_request/agent_status/run_finish…)。read_run_events/summarize_run_log 读取解析。run_review 就基于它做复盘。
- 面试怎么用：可说：我用 JSONL 逐事件追加写运行日志，天然支持流式追加和按行解析，比单 JSON 更适合长时运行的可观测性。

**SQLite**

- 是什么：SQLite：轻量嵌入式关系数据库，单文件、无需服务进程，适合桌面应用本地持久化。
- 在 kagent 里：kagent 的持久化层 db.py。init_db 建 sessions/messages/context_summaries/rollback_entries/project_memories 表，_conn 用 sqlite3 加线程锁 _lock。rollback 条目、上下文摘要、项目记忆都存这里。
- 面试怎么用：可说：我用 SQLite 存会话、回滚条目、上下文摘要和项目记忆，单文件零部署、配合 threading.Lock 做并发安全，桌面端很合适。

**subprocess / 子进程**

- 是什么：子进程：在主程序里另起一个进程执行外部命令并收集其输出/退出码的机制(Python subprocess 模块)。
- 在 kagent 里：workspace.py 的 run_command 用 subprocess.run(command, shell=True, cwd=workdir, capture_output=True, timeout=...) 执行命令；apply_patch 用 subprocess.run(["git","apply",...]) 打补丁。test_telemetry.py 的 prepare_pytest_junit_command 给 pytest 命令追加 --junitxml 收集每个用例结果。
- 面试怎么用：可说：agent 的 run_command 通过 subprocess 执行用户命令并捕获超时/退出码，pytest 命令我自动注入 --junitxml 抓每个用例结果做遥测。

## 工具/平台 域

**pyqtgraph**

- 是什么：pyqtgraph：基于 PyQt 的高性能科学绘图库，适合画实时折线/曲线图，比 matplotlib 在 Qt 里更顺滑。
- 在 kagent 里：ui/main_window.py:5456 _run_analytics_dashboard_widget 用 import pyqtgraph 画 pass-rate 折线图(chart.plot)，下接 Flaky/Timing regression 两个 QTableWidget；ImportError 时降级为 QTextBrowser 渲染 markdown。
- 面试怎么用：可说：我用 pyqtgraph 在桌面端画运行通过率折线图叠加 flaky/耗时回归表，做成了真实可视化面板，并做了无依赖降级保证可打开。

**dashboard / 仪表盘**

- 是什么：仪表盘：把多维数据用图表/表格直观呈现的可视化面板，方便人看趋势而非读日志。
- 在 kagent 里：ui/main_window.py:5456 的 _run_analytics_dashboard_widget 构建：上方 pyqtgraph pass-rate 图 + 下方 flaky/timing-regression 表，数据来自 build_run_analytics。这是把原来纯 markdown 的运行分析升级成的可视化面板。
- 面试怎么用：可说：我把跨次运行的质量门禁/验证/失败工具趋势做成 dashboard，通过率折线+flaky+耗时回归三块，让趋势一眼可见。

**Activity 面板 / 活动面板**

- 是什么：活动面板：UI 里集中展示当前会话改动/可回滚项/历史运行等"近期活动"的对话框，是用户回看 agent 行为的入口。
- 在 kagent 里：ui/main_window.py:4725 _show_activity_panel 是个 QDialog，汇总当前会话的可回滚改动数/路径、rollback 历史、可恢复的 run、运行趋势分析等"活动"入口，是 agent 跑完后回看和操作的工作区活动总览。
- 面试怎么用：可说：我做了个 Activity 面板把一次会话里所有可回滚改动、历史和恢复入口集中展示，用户能从总览直接进回滚或恢复。

**Run Debug / 运行调试**

- 是什么：运行调试：针对单次 agent 运行做调试复盘的视图入口，可切换看摘要/时间线/复盘/质量门禁/缺陷报告/回归计划等不同切面。
- 在 kagent 里：ui/main_window.py:1110 _run_debug_markdown 按 mode(summary/timeline/review/quality_gate/bug_report/regression_plan)渲染当前 run 日志的不同视图；_show_run_debug 弹窗展示。由 run_summary_btn/run_timeline_btn 等一组按钮触发。
- 面试怎么用：可说：我做了 Run Debug 把单次运行展开成摘要/时间线/复盘/质量门禁/缺陷报告/回归计划多视角，方便排查某次跑歪的原因。

**verify.ps1**

- 是什么：项目自带的 PowerShell 校验脚本，作为该工作区的一键验证入口(语法检查/测试/构建打包在一起)。
- 在 kagent 里：validation.py:675 _project_verify_command 检测工作区 scripts/verify.ps1，存在则返回 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1' 作为验证命令之一(:678)，没有则降级 run-tests.bat。verify.ps1:16 内部也用 'compileall -q' 做编译检查。
- 面试怎么用：可说：验证层我优先认项目自带 scripts/verify.ps1 作为一体化校验入口，自动拼成 powershell 调用，让 agent 用项目原生验证而不是我硬编码命令。

**STATE_DIR / 状态目录**

- 是什么：状态目录：agent 存放运行时产物(run 日志、回滚快照、分析结果等)的根目录，和用户工作区源码分开。
- 在 kagent 里：config.py:20 STATE_DIR=KAGENT_STATE_DIR，默认 .kagent_state。run 日志写 STATE_DIR/runs/*.jsonl(run_log.py)，rollback 快照写 ROLLBACK_ROOT=STATE_DIR/rollback(config.py:21)，分析结果等也落这里。是 agent 所有运行时副作用的根目录。
- 面试怎么用：可说：我把 run 日志、回滚快照、分析产物都收在 STATE_DIR 这个统一状态目录下，和工作区源码分离，不污染用户仓库。

---

## 交叉校验备注

交叉校验说明（已对照代码核验，所有 inKagent 引用文件/行号/常量均真实存在）：

1. 去重合并：原三份草稿里 "JUnit XML"、"junit"、"--junitxml" 是同一套机制的不同层面，已合并为一条 "JUnit XML / junit / --junitxml"，isWhat 解释格式本身、inKagent 同时覆盖 test_telemetry.py 的 prepare_pytest_junit_command(--junitxml 参数) 和 parse_junit_xml(解析)。另保留一条占位 "--junitxml (pytest 参数)" 指向主条目，避免读者以为是独立概念。

2. 路径修正：草稿 A 多处把 agent_worker.py 和 main_window.py 当成在 kagent/ 根下，实际二者都在 kagent/ui/ 子目录（agent_worker.py:3 的 QThread 导入、main_window.py:5456 的 pyqtgraph 面板均已核实）。合并稿里已统一改为 ui/agent_worker.py、ui/main_window.py。

3. kagent 内部命名 vs 业界术语归类（面试口径重点）：
   - 纯业界通用词：ReAct、Tool loop、tool_call/tool_result、Observation、token、context window、stream、fallback、AST、embedding、TF-IDF、余弦相似度、pytest、JUnit XML、coverage、line_rate、flaky、timing regression、median baseline、compileall、subprocess、SQLite、pyqtgraph、dashboard、upsert。这些 isWhat 用业界定义，inKagent 给本项目实现。
   - kagent 自创/内部命名（面试时务必说明"这是我自己起的名字"，否则面试官搜不到）：AgentPhase、final_trust、EventFn、should_stop、INSPECTION_TOOLS/MUTATION_TOOLS/CONTENT_EDIT_TOOLS/VALIDATION_TOOLS、symbol_change_plan、symbol_impacts、impact_score、risk_level、find_symbol_references、container、test_case_result、coverage_bonus、regression gate、insufficient_corpus、failure_memory、水位线、manage_context、context_compacted、project_memory、context_summaries、KAGENT.md、task_plan、task_resume、risk_policy、tool_policy、approval_required、destructive、rollback、snapshot、superseded、patch_recovery、tool_loop_guard、tool_recovery、failure_diagnostics、failure_focus、repair_strategy、classify_failure、quality_gate、run_log、Activity 面板、Run Debug、verify.ps1、STATE_DIR。

4. 易踩坑提醒：
   - token 估算不是单纯 chars/4：context.py:37 实际是 (ascii_chars + non_ascii_chars*2)//4，中文按 2 倍计。面试说"chars/4"够用，但被追问中文时要会补这一句。
   - reasoning_effort 有 fallback：llm.py 对不支持的模型会自动去掉该参数重试，跨模型可用性是加分点。
   - flaky vs regression 的区分是面试亮点：全 fail 算 regression 不算 flaky（run_analytics.py:306 _flaky_tests 严格要求 pass_rate 严格在 (0,1) 之间，且 _FLAKY_MIN_RUNS=3）。
   - timing regression 用双阈值（1.5 倍 AND +200ms）+ 中位数基线（窗口5），避免快/慢测试误报，是工程细节。
   - impact_score 权重是写死的启发式（定义不存在+25、产线引用每条+4 上限35 等，封顶100），面试可主动说"这是启发式不是学习来的"，避免被当成 ML 模型追问。
   - failure_memory 故意不用 embedding：注释明说 no embedding API，选 TF-IDF+余弦是为了可复现、无外部依赖、语料小——这是"技术选型权衡"的经典面试题答案。
   - rollback 快照是文件级 shutil 副本、不依赖 git，superseded 语义（回滚到旧点会让更新的改动失效）是 kagent 特有状态机细节。
   - quality_gate 有两处产出（run_review.build_quality_gate 与 final_trust.build_quality_gate_summary），面试讲清"运行门禁"和"最终信任门禁"是两个层面即可。

5. 无捏造内容：所有 inKagent 中的函数名、常量值（_MIN_CORPUS_FOR_RECALL=3、_FLAKY_MIN_RUNS=3、_TIMING_REGRESSION_RATIO=1.5、_TIMING_MIN_DELTA_MS=200、_TIMING_BASELINE_WINDOW=5、MAX_HISTORY=20、REPEAT_THRESHOLD=2、MAX_DIAGNOSTICS=12、RISK_LEVELS 五档、CONTEXT_MAX_TOKENS=24000）均已逐一 grep 核实存在且数值一致。impact_score 的 +25/+4(上限35)/+3(上限20)/+2(上限12)/+15/封顶100 公式与 symbol_change_plan.py:147-165 吻合。