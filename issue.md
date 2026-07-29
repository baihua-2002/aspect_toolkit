# ASPECT Agent 改进建议与 test_case 跑通记录

## 本次 test_case 跑通状态

- 输入案例：`test_case/OCR_数值模拟华北克拉通岩石圈热对流侵蚀减薄机制.md`
- 当前限制：环境中未配置 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`，因此未调用 `RAG.extractor` 的 LLM 抽取链路。
- 已采用替代路径：基于 OCR 中明确给出的华北克拉通热对流侵蚀参数，手工整理最小 ASPECT smoke case 答案字典。
- 新增答案文件：`test_case/ncc_thermal_thinning_minimal_answers.json`
- 生成 PRM 文件：`test_case/ncc_thermal_thinning_minimal.prm`
- 运行命令：`uv run python -m aspect_prm_builder.main --answers test_case/ncc_thermal_thinning_minimal_answers.json --validate`
- 验证结果：`Validation passed.`
- 运行命令：`uv run python -c "from connector import AspectConnector; r=AspectConnector().run('test_case/ncc_thermal_thinning_minimal.prm', timeout=120); print(r.success, r.returncode, r.timed_out, r.output_directory)"`
- ASPECT 结果：`success=True`, `returncode=0`, `timed_out=False`, elapsed about 4s。
- 输出目录：`runs/ncc_thermal_thinning_minimal/output-ncc-thermal-thinning-minimal`

说明：该 PRM 是用于验证当前 builder -> connector -> ASPECT 的最小可运行配置，不等价于复现论文中 201x201 网格、5000 年步长、千万年尺度、I2VIS/MIC 追踪点的完整实验。

## P0：优先修复项

1. 修复 TUI 非交互环境启动问题
   - 现象：`uv run python -m agent_core --help` 会进入 TUI，并在非 TTY stdin 下触发 `prompt_toolkit` 的 `OSError: [Errno 22] Invalid argument`。
   - 建议：`agent_core/main.py` 增加 `argparse`，支持 `--help`、`--once "prompt"`、非 TTY 检测；非交互环境下给出明确错误或执行单次请求。

2. 消除本机硬编码 ASPECT 路径
   - 现状：`connector/config.json` 和 `ConnectorConfig.default()` 依赖 `/Users/bai/workspace/aspect-main/build/aspect` 或本机 build 目录。
   - 建议：提交 `connector/config.example.json`，真实 `connector/config.json` 加入忽略；支持 `ASPECT_BINARY` 环境变量覆盖。

3. 补齐显式依赖
   - 现状：`RAG/extractor.py` 使用 `from openai import OpenAI`，但 `pyproject.toml` 未显式声明 `openai`。
   - 建议：将 `openai` 加入 dependencies，或把 extractor 的 LLM 调用改为复用 `agent_core.providers`/PydanticAI。

4. 修正文档入口和 README 大小写
   - 现状：`pyproject.toml` 指向 `README.md`，仓库根目录实际为 `readme.md`，在大小写敏感文件系统或打包时会失败。
   - 建议：统一为 `README.md`，并让根 README、`agent_core/main.py`、`RAG/extractor.py` 的配置路径说明保持一致。

5. 明确根目录 `main.py` 定位
   - 现状：根 `main.py` 是 RAG demo 加注释代码，不是 README 描述的正式入口。
   - 建议：改为转发到 `agent_core.main`，或移动到 `examples/`，避免用户运行根入口时得到演示逻辑。

## P1：可靠性改进

1. 增加最小自动化测试
   - 覆盖 `ParameterSearcher` 排序、`CaseSearcher` 检索、`assembler.parse_prm/assemble_prm` 往返、`validator.validate_answers`、`AspectConnector._build_command`。
   - 增加一个 smoke test：用 `test_case/ncc_thermal_thinning_minimal_answers.json` 生成 PRM 并验证 builder 输出。

2. 强化 validator 的 ASPECT 语义校验
   - 当前 validator 主要校验字段存在、类型、choice 和未知参数。
   - 建议增加：2D 下禁用 Z 参数、边界 indicator 合法值、list 长度一致性、`Model name` 与子 section 是否匹配、单位字符串误传检测。

3. 增强 `patch_prm` 的 section 定位能力
   - 当前实现依赖简单 depth 和 matched sections，面对重复 subsection、注释、空行和复杂嵌套时容易误定位。
   - 建议复用 `assembler.parse_prm` 建 AST 或显式 section stack，再做精确 patch。

4. 避免 TUI 直接访问私有字段
   - 现状：`agent_core/tui.py` 访问 `self._registry._configs`。
   - 建议：在 `ProviderRegistry` 增加只读迭代接口，例如 `iter_configs()`。

## P2：RAG 与案例抽取质量

1. 将 OCR 抽取流程变成可离线回归
   - 当前 extractor 需要外部 API Key，导致 CI 或本地无 key 时无法跑通。
   - 建议增加 `--from-json` 或 fixture 模式，用固定 LLM 输出测试 `parse_llm_json`、`coerce_case`、`write_cases`。

2. 参数值入库前做结构化归一
   - OCR 案例中存在 `1.0e22|1.0e23 Pa s`、`1773|1873|1973|2073 K` 这种扫描值，不适合直接喂给 builder。
   - 建议区分 `single_value`、`sweep_values`、`unit`、`source_location`，避免 agent 把带单位字符串直接写入 numeric parameter。

3. 增强参数名 canonicalize
   - 当前 `cases.json` 有 `Global parameters.No subsection.Dimension`，而 builder 使用 `Dimension`；两套路径约定不统一。
   - 建议维护一张 canonical map，让 RAG 参数路径、builder schema 路径、ASPECT 文档路径可互转。

4. 建立黄金评测集
   - 对 5-10 个 OCR/cookbook 样例人工整理标准参数表。
   - 指标：字段级抽取 precision/recall、检索 Recall@k、端到端 PRM 可运行率。

## P3：产品化与工程体验

1. 增加命令别名
   - 建议在 `pyproject.toml` 添加 console scripts，例如 `aspect-agent = agent_core.main:main`、`aspect-extract-case = RAG.extractor:main`。

2. 输出覆盖报告
   - Agent 生成 PRM 后输出每个关键参数来源：用户输入、RAG 案例、schema 默认值或人工假设。
   - 对没有文献支撑的参数显式标记为 assumption。

3. 清理运行产物
   - `runs/`、`*.prm`、ASPECT 可视化输出都应保持忽略。
   - 建议增加 `scripts/clean_runs.sh` 或 README 中的清理命令。

4. 区分 smoke case 和 research reproduction
   - 当前最小案例能证明链路跑通，但不复现论文结果。
   - 建议未来新增两个层级：`smoke` 用于快速 CI，`reproduction` 用于长时间科学复现实验。


RAG.extractor 已使用 .env 中的 DEEPSEEK_API_KEY 完成测试。
运行结果
命令：
uv run python -m RAG.extractor \
  "test_case/OCR_数值模拟华北克拉通岩石圈热对流侵蚀减薄机制.md" \
  --dry-run
结果：
- API Key 加载成功
- 输入：11 页，27,635 字符
- 分块数：1
- LLM 原始返回：3 个案例
- 清洗、去重后：2 个案例
- 抽取成功的案例：
- blankenbach-benchmark-1a
- ncc-thermal-thinning-2013
- 共抽取 27 条参数决策
- dry-run 未写入 RAG/cases.json
同时验证了：
- normalize_value() 可处理科学计数法
- parse_llm_json() 可解析 JSON
- RAG 案例检索正常返回已有案例
- RAG 模块编译检查通过
发现的问题
这次抽取证明链路可用，但 LLM 输出仍需人工复核，主要问题包括：
- Formulation.Formulation 输出了 Boussinesq，而当前 builder schema 使用 Boussinesq approximation。
- “free slip” 被部分输出为 Zero velocity boundary indicators，语义上可能不准确，应映射到 Tangential velocity boundary indicators。
- Thermal viscosity exponent、Grid resolution、Number of markers 等字段当前 schema 未覆盖。
- 扫描参数仍以字符串表示，例如 1773|1873|1973|2073 K，不能直接交给 numeric PRM 参数。
- 抽取结果中的 domain 是 mantle convection，而现有 cases.json 中对应案例使用 craton evolution，受控词表还需要统一。
