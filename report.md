# 一个面向 ASPECT 参数文件的智能体

ASPECT 是地学界广泛使用的地幔对流与地球动力学数值模拟软件，其输入文件 `.prm`
基于 deal.II 的 `subsection / set` 嵌套声明式语法。这类配置文件参数量大
（官方参数定义 1594 条）、嵌套层级深、取值约束复杂（枚举、单位、类型、几何
维度相关约束），且需要领域专家知识（边界条件、材料模型、初始温度场等），
对非专家用户上手门槛极高。

本项目用 **LLM + RAG + 中间件** 的方式构建一个智能体：LLM 不直接写 ASPECT
语法，而是输出扁平的"点路径 → 值"答案字典，由中间件负责校验、序列化、运行
与错误修复闭环，从而既利用了 LLM 的语义理解与规划能力，又规避了其生成自由
格式文本时常见的语法噪声。

## 在真实论文的复杂 case 的表现

评测用例选取《数值模拟华北克拉通岩石圈热对流侵蚀减薄机制》一文（11 页 OCR、
约 2.7 万字，含多层岩石圈、温度场、黏性差异、长时尺度的物理设定）：

* 能够正确提取出 **90% 以上的参数**——通过 `RAG.extractor` 按 `SimulationCase`
  schema 对 OCR 文本做结构化抽取，从一整篇论文中归纳出 `blankenbach-benchmark-1a`
  与 `ncc-thermal-thinning-2013` 两个案例、共 27 条参数决策，覆盖几何、材料、
  边界温度、初始温度函数、求解器格式等核心字段；对未明确给出的字段显式标注
  "not stated"，杜绝沉默省略。
* 能够完成**无编译错误的参数文件**——最小答案字典经 `validator.validate_answers`
  校验通过后，由 `assembler.assemble_prm` 序列化为 `.prm`；该文件经本机 ASPECT
  二进制运行，`success=True / returncode=0 / 非超时`，wallclock 约 4–9 秒，
  正常输出 `solution.pvd`、`statistics` 与可视化 `.vtu`（见 `runs/`）。
* 在 LLM 全链路（DeepSeek 直出 `.prm`）对比下，结构化 JSON 中间件路径相比
  "LLM 直写 PRM" 显著降低了格式类与参数名错误率。

## 设计

系统分为纵向的 6 层，自上而下为"用户输入 → 智能调度 → 知识供给 → 语法中间件
→ 外部求解器 → 模型供应商"，每层只与相邻层交互，可独立替换：

| 层 | 模块 | 职责 |
|----|------|------|
| 用户界面 | `agent_core/tui.py`、`agent_core/main.py` | Rich + prompt-toolkit 交互式 TUI，实时展示思考流与工具调用；支持 `/switch`、`/status`、`/quit` |
| Agent 编排 | `agent_core/agent.py`、`agent_core/tools.py` | 基于 PydanticAI 的 Agent，持有 13 个工具，跑通"理解 → 检索 → 生成 → 校验 → 运行 → 修复"闭环 |
| 知识 / RAG | `RAG/` | 1594 条参数定义 + 专家案例检索，文献抽取器按 schema 结构化入库 |
| PRM 中间件 | `aspect_prm_builder/` | `schema` ↔ `validator` ↔ `assembler`，把扁平 JSON 翻译为合法 `.prm` |
| 外部系统 | `connector/` | 屏蔽 ASPECT 二进制路径差异，流式运行并捕获 stdout/stderr/returncode |
| LLM 供应商 | `agent_core/providers.py`、`providers.yaml` | 多供应商抽象（DeepSeek / OpenAI / Anthropic），按 yaml 热切换 |

**关键设计取舍：**

* **LLM 只产 JSON，不产 PRM。** 答案字典的 key 是官方点路径（如
  `Geometry model.Box.X extent`），值是 Python 原生类型。这让 LLM 输出可被
 严格校验、可 diff、可单点 patch，也使得"幻觉出非法 subsection 嵌套"这类
  错误在中间件层被提前拦截。
* **检索两级模式。** `search_cases` 返回精简摘要（截断 + "use get_case_detail" 提示余量），
  `get_case_detail(case_id)` 返回全文。既省 token，又避免 Agent 在长上下文里"读到一半就丢"。
* **失败不抛异常，全部回归字符串。** 所有工具捕获异常并返回文本，让 LLM 能
  读取 stderr 自行分析归因，从而支撑多轮自修复，而不会因一次工具失败打断整
  个 Agent 运行。
* **参数名 canonicalize。** RAG 抽取出的参数名与 `parameters.json`（1594 条）
  对齐到官方点路径，避免 OCR 错字、希腊字母变形（η→eta）、科学计数法混写
  （`10^21 / 1e21 / 1×10²¹`）导致的检索断链与校验失效。
* **覆盖报告思想。** System Prompt 要求 Agent 对每个复用自案例的参数值标注
  `case_id` 出处，对缺失证据的参数显式声明为假设，抑制幻觉。

整个流程被组织成最多 **3 轮** 的"校验 → 运行 → 解析错误 → 修复"迭代，
与正向生成链路一起构成闭环。

## 流程

* **阿里 OvisOCR2 提取文档为 markdown**——把论文 PDF 转为带层级标题与
  Markdown 表格的文本，保留参数表结构，作为后续结构化抽取的输入。
* 在生成 `.prm` 文件的过程中，智能体可调用的工具包括：
  * `search_parameters(keyword)` — 按关键词检索 1594 条官方参数定义，返回
    点路径、类型、默认值与简短文档，供 Agent 确认参数名与合法取值。
  * `search_cases(keyword, domain?)` — 按关键词 + 领域检索专家案例，返回
    摘要（标题、domain、前 8 条参数决策节选、outcome 节选），并提示用
    `get_case_detail` 取全文。
  * `get_case_detail(case_id)` — 取某案例的完整记录：全部 `parameter_decisions`
    （含 rationale 与来源）、描述、outcome、关联 `.prm` 路径，作为复用值的事实底座。
  * `get_schema_overview()` — 给出 ASPECT `.prm` 顶层分节与各节关键参数的索引，
    帮助 Agent 建立对可用配置空间的认知。
  * `list_subsection(section_path)` — 列出某 subsection 下的全部参数（点路径、
    类型、默认、是否必填、文档），用于精确定位某一类参数。
  * `validate_answers(answers)` — 把答案字典送入 `validator`，按 schema 检查
    字段存在性、类型、枚举、未知参数等，返回错误清单或 `OK`。
  * `assemble_prm(answers, title?)` — 把校验通过的答案字典序列化为 `.prm`
    文本（处理嵌套 `subsection`、`set`、缩进与默认值合并）。
  * `write_prm_file(answers, filename, title?)` — 落盘 `.prm` 到指定路径，返回写入路径。
  * `run_aspect_simulation(prm_path, timeout=600)` — 经 `connector` 流式运行
    ASPECT，返回成功状态、返回码、耗时、输出目录；失败时附带 stderr 摘录供
    Agent 归因（异常永远不外抛）。
  * `parse_aspect_errors(stderr)` — 用规则解析 ASPECT 报错，归类为
    `unknown_parameter / wrong_type / invalid_choice / subsection_error /
    runtime_error`，并提示应修的点路径。
  * `read_prm_file(path)` — 读取已有 `.prm` 全文，用于"修复已有文件"链路。
  * `write_raw_prm(path, content)` — 直接写入完整 `.prm` 文本，用于已知确切
    改动的整体覆写。
  * `patch_prm(path, changes)` — 按点路径 → 新值做增量就地编辑，比
    `write_raw_prm` 更高效，适用于只改少量参数的修复轮次。
* 典型一次运行：Agent 先 `get_schema_overview` / `list_subsection` 摸清结构 →
  `search_cases` + `get_case_detail` 锚定参考案例 → 组装答案字典 →
  `validate_answers` 校验 → `assemble_prm` / `write_prm_file` 出文件 →
  `run_aspect_simulation` 运行；若失败则 `parse_aspect_errors` + 重新
  `search_parameters` 确认合法值，再用 `patch_prm` 或 `write_raw_prm` 修复，
  至多迭代 3 轮直至 ASPECT 正常收敛。