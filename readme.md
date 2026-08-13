# ASPECT 参数配置文件（.prm）智能生成 Agent

用 LLM + RAG 自动生成 ASPECT 地幔对流模拟软件的 `.prm` 配置文件。LLM 不直接写 ASPECT 语法，而是输出结构化 JSON 答案，中间件负责校验、序列化和运行。

## 项目结构

```
aspect_agent/
├── RAG/                   # 检索增强系统（1594 条参数定义 + 专家案例）
├── aspect_prm_builder/    # PRM 构建中间件（schema/engine/assembler/validator）
├── connector/             # ASPECT 运行连接器（启动、捕获结果）
├── agent_core/            # PydanticAI Agent 编排层（多供应商 + TUI）
├── providers.yaml         # LLM 供应商配置
├── main.py                # 入口
└── pyproject.toml         # Python 3.13, uv 管理
```

## 快速开始

### 安装

```bash
# 克隆项目后安装依赖
uv sync
```

### 配置 API Key

创建 `.env` 文件（已加入 `.gitignore`，不会提交）：

```env
DEEPSEEK_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here      # 可选
ANTHROPIC_API_KEY=your-key-here   # 可选
```

### 配置供应商

编辑 `providers.yaml` 添加或修改 LLM 供应商：

```yaml
providers:
  deepseek:
    type: openai                        # OpenAI 兼容协议
    base_url: https://api.deepseek.com
    model: deepseek-chat
    api_key_env: DEEPSEEK_API_KEY

  openai:
    type: openai
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY

  anthropic:
    type: anthropic
    model: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY

default: deepseek
```

### 启动 Agent TUI

```bash
uv run python -m agent_core
```

TUI 命令：
- `/switch <provider>` — 切换 LLM 供应商
- `/status` — 查看当前配置
- `/quit` — 退出

## 模块说明

### connector — ASPECt 运行中间件

屏蔽系统差异，运行 `.prm` 文件并捕获结构化结果。

```python
from connector import AspectConnector
connector = AspectConnector()
result = connector.run("simulation.prm", timeout=3600)
# result.success, result.stdout, result.stderr, result.elapsed_seconds
```

### RAG — 检索增强系统

1594 条 ASPECT 官方参数定义 + 21 条专家仿真案例（19 官方 cookbook + 2 文献清洗）检索，
为 LLM 提供领域知识。

```python
from RAG import AspectRAG
rag = AspectRAG()
result = rag.search("mantle convection", domain="geodynamics")
# result.parameters, result.cases
```

官方 cookbook → 专家案例（无需 LLM，参数忠实于 `.prm`）：

```bash
uv run python -m RAG.cookbook_importer --dry-run   # 预览不落盘
uv run python -m RAG.cookbook_importer             # 合并进 cases.json
```

文献清洗（OCR 文本 → 结构化案例库）：

```bash
uv run python -m RAG.extractor test_case/OCR_xxx.md --dry-run  # 预览不落盘
uv run python -m RAG.extractor test_case/OCR_xxx.md            # 合并进 cases.json
```

抽取器按 `SimulationCase` schema 让 LLM 结构化抽取（参数表逐行转成
parameter_decisions，科学计数法统一 e-notation，未知字段显式 "not stated"），
参数名映射到官方点路径，长文档按页分块后合并。

### aspect_prm_builder — PRM 构建中间件

LLM 只需输出扁平 JSON（`"Geometry model.Box.X extent": 1`），中间件处理所有 ASPECT 语法。

```python
from aspect_prm_builder import assembler, validator
answers = {
    "Dimension": 2,
    "Geometry model.Model name": "box",
    "Geometry model.Box.X extent": 1.0,
    "Geometry model.Box.Y extent": 1.0,
    "Material model.Model name": "simple",
    "Material model.Simple model.Viscosity": 1e21,
}
errors = validator.validate_answers(answers)
prm_content = assembler.assemble_prm(answers)
```

### agent_core — Agent 编排层

基于 PydanticAI 的智能 Agent，自动执行"需求分析 → 参数检索 → 生成 → 校验 → 运行 → 错误修复"闭环。

- 11 个工具函数包装现有模块（案例检索为 search_cases → get_case_detail 两级模式）
- 多供应商支持（DeepSeek / OpenAI / Anthropic / Gemini）
- Rich TUI 界面，实时展示工具调用过程
- 支持生成新 .prm 和修复已有 .prm 文件

## 工作流程

```
用户仿真需求
    ↓
[Agent] 调用 RAG 检索参数定义和案例
    ↓
[Agent] 生成答案字典（扁平 JSON）
    ↓
[validator] 校验答案合法性
    ↓
[assembler] 序列化为 .prm 文件
    ↓
[connector] 运行 ASPECT 仿真
    ↓
失败？→ [Agent] 分析错误 → 修复 → 重新校验运行（最多 3 轮）
成功？→ 返回 .prm 文件和运行结果
```

## 技术栈

- **Python 3.13** + **uv** 包管理
- **PydanticAI** — Agent 框架
- **Rich** — TUI 渲染
- **prompt-toolkit** — 交互式输入
- 零外部 C++ 依赖，ASPECT 二进制需单独编译

### P0 — 结构化抽取 + 补全案例详情工具（收益最大、成本最低）

 ① OCR 之后加一步 LLM 结构化抽取，不要把长文本直接入库。用 SimulationCase 的
 schema 做 JSON 约束输出：

 ```
   PDF → Ovis-OCR2 原始文本 → LLM抽取(按schema) → 结构化case → cases.json
 ```

 - 每个字段允许显式 "not stated"，缺失即标注，禁止沉默省略；
 - 表格单独处理：prompt 中要求 OCR 保留 Markdown 表格，抽取时把参数表逐行转成
   parameter_decisions；
 - 长文档按章节切分后分别抽取再合并，避免超出上下文导致后半部分被丢弃（这是"信息
   缺失"最常见的技术原因）。

 ② 给 Agent 加 get_case_detail(case_id) 工具，与参数检索的两级模式对齐：

 ```python
   def get_case_detail(case_id: str) -> str:
       """Get full details of a case: all parameter decisions, tables,
 outcome."""
       c = _case_searcher.get(case_id)
       # 返回完整 parameter_decisions + 表格原文 + outcome 全文
 ```

 ③ 放宽 search_cases 截断，并在截断时提示余量：... (12 more decisions, use
 get_case_detail("case_007"))。

 ### P1 — 文本归一化 + 参数名对齐（修复检索断链）

 ④ 入库和查询两侧做同一套归一化（normalizer.py）：
 - 科学计数法归一：10^21 / 1×10²¹ / 1e21 → 统一形式；上标字符映射（²¹→^21）；
 - 希腊字母映射表（η→eta、ρ→rho），数字上下文纠错（O→0、l→1）；
 - 去跨行连字符、去页眉页脚页码、修 ligature（fi/fl）。

 ⑤ 参数名对官方表 canonicalize：抽取出的参数名与 parameters.json（1594 条）做模糊
 匹配（如 RapidFuzz，阈值 ~90），改写为官方点路径。一举三得：修 OCR 错别字、
 by_parameter() 反查恢复可用、validator 能校验值的类型/取值范围。

 ⑥ 检索改为字段化 + 简单查询扩展：domain/tags 用受控词表；建立领域同义词表
 （Ra↔Rayleigh number、slab↔subduction、η↔viscosity）在查询时扩展。

 ### P2 — 分块 + 混合检索（文档量大时再做）

 ⑦ Chunking：按标题层级切成 300–800 token 的块（10% 重叠），每块记录 case_id + 页
 码/章节 出处。检索定位到块而非整篇文档。

 ⑧ 混合检索：现有关键词打分保留，叠加向量 embedding（本地小模型或 API 均可），必
 要时加 reranker。同时给 Agent 加 search_document_chunks(query, case_id?) 工具。

 ### P3 — 评估闭环（防止改完不知道有没有用）

 ⑨ 建黄金评测集：选 5–10 篇文献/cookbook，人工整理其参数表作为标准答案，持续度量
 三个指标，分别对应三种失败模式：

 ┌──────────────────────────┬─────────────────────────────┐
 │ 指标                     │ 对应失败模式                │
 ├──────────────────────────┼─────────────────────────────┤
 │ 字段级抽取 精确率/召回率 │ E1：清洗时信息就丢了        │
 ├──────────────────────────┼─────────────────────────────┤
 │ 检索 Recall@k            │ E2：抽到了但检索不到        │
 ├──────────────────────────┼─────────────────────────────┤
 │ 端到端参数正确率         │ E3：检索到了但 Agent 没用对 │
 └──────────────────────────┴─────────────────────────────┘

 ⑩ 防幻觉机制：要求 Agent 对每个从案例引用的参数值标注出处（case_id + chunk），最
 终输出"覆盖报告"——哪些需求有文献依据、哪些是默认值/假设。
