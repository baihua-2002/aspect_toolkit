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

1594 条 ASPECT 官方参数定义 + 专家仿真案例检索，为 LLM 提供领域知识。

```python
from RAG import AspectRAG
rag = AspectRAG()
result = rag.search("mantle convection", domain="geodynamics")
# result.parameters, result.cases
```

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

- 10 个工具函数包装现有模块
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
