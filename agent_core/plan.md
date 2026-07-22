阶段 0 — 决策与脚手架
- 确定框架（建议 LangGraph）、LLM provider（云端 Claude/GPT 或本地 Ollama）、是否需要 Docker 沙箱（ASPECT 已是隔离的求解器，建议不用 Docker，直接复用 connector）。
- 新增 agent/ 包：agent/__init__.py、agent/tools.py、agent/parser.py、agent/graph.py、agent/state.py、agent/cli.py。
- pyproject.toml 加入依赖（LangGraph + litellm）。
阶段 1 — 工具层（agent/tools.py，包现有领域代码为 agent tools）
把现有模块封装成 LLM 可调用的 tool（签名 + docstring 即工具 schema）：
- generate_prm(answers: dict) -> str —— 调 engine.build_from_answers + assembler.assemble_prm。
- validate_answers(answers: dict) -> list —— 调 validator.validate_answers（刚修好的）。
- run_aspect(prm_path: str, timeout?) -> dict —— 调 connector.AspectConnector.run，返回 {success, returncode, stdout, stderr, elapsed, output_dir}。
- search_parameter(query: str) / search_case(query: str) —— 调 RAG.ParameterSearcher/CaseSearcher，给 agent 检索 ASPECT 参数语义与 cookbook 先例。
- read_prm(path) / write_prm(path, text) / edit_answers(answers) —— 文件与答案编辑。
- 不做通用 shell/file 工具，收窄动作空间以降低误操作。
阶段 2 — ASPECT 报错解析器（agent/parser.py，本项目独有、最关键）
ASPECT 的 stderr 非结构化，需专用解析器把文本转成 agent 可操作的 Finding 列表：
- 识别类别：unknown_parameter（The following parameter was not found）、wrong_type（Could not convert）、invalid_choice（doesn't match any of the possible values）、missing_subsection、geometry_mismatch、numerical_divergence（Exception zero/nan）、mpi/parallel 错误。
- 每个 Finding 带 {category, raw_line, parameter_path?, suggested_fix?}，映射回 schema.py 的点分路径，便于 agent 定位到 answers 的某个键。
- 把解析结果喂回 agent 作为修复依据，而不是原始 stderr（节省 token、聚焦）。
阶段 3 — Agent 循环（agent/graph.py + agent/state.py）
LangGraph 状态机节点：
[plan] → [generate] → [validate] → [run] → [parse_errors] → [fix] ↻ (回到 generate)
                                          ↓ success
                                       [done]
- State：{intent, answers, prm_path, findings, iteration, max_iterations, history}。
- 条件边：validate 有错 → fix；run 成功 → done；run 失败 → parse_errors → fix；iteration >= max_iterations → escalate_to_human。
- fix 节点：LLM 基于 findings + RAG 检索结果 + schema，产出新的 answers 增量（仅改出错的键），非整文件重写。
- 设 max_iterations=5，每轮强制 validate_answers 先过再 run（避免无效运行浪费 3600s）。
阶段 4 — 状态持久化与续跑
- 用 LangGraph checkpointer（SQLite）存 State，ASPECT 运行中途超时/崩溃可 resume。
- 每轮产物落 runs/<task_id>/：iter_N.prm、iter_N.json、stderr_N.log、findings_N.json（与现有 runs/ 目录结构一致）。
阶段 5 — 评测与护栏
- 护栏：validate 前置（已实现）、run 超时与返回码检查（connector 已有）、LLM 输出 JSON schema 校验（防止 agent 产出非法 answers）、参数白名单（只能改 schema 内键，防止幻觉键）。
- 评测集：用 aspect_prm_builder/generated_examples/ 的 roundtrip 示例 + 人造坏 prm（非法 choice/类型/缺失子节）做回归，目标"≤N 轮内修好"。
阶段 6 — 集成与入口
- agent/cli.py：python -m agent --intent "2D box convection" 或 --answers answers.json。
- main.py：取消注释的 connector 块，改为调用 agent 跑闭环。
- AGENTS.md：写明工具约定、循环上限、ASPECT 运行约束，供 agent 与未来其他 coding agent 复用。
风险与待决项
- ASPECT 错误信息格式随版本变化 → 解析器需版本化、保留 raw stderr 兜底。
- 长运行（3600s）× 多轮 → token 与时间成本高，需 checkpoint + 并行任务隔离。
- 本地模型 tool-calling 成功率低 → 若走本地，用 Forge 的 guardrails 或强制 JSON 模式。
