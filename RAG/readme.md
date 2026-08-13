# RAG — ASPECT 参数与专家案例检索系统

为 agent 的"生成-运行-修复"循环提供知识检索能力，包含两类知识源：

## 架构

```
RAGResult (统一检索结果)
├── parameters: list[Parameter]         # ASPECT 参数定义（官方文档）
└── cases: list[SimulationCase]         # 专家模拟案例（文献清洗）
        └── parameter_decisions: list[ParameterDecision]  # 案例中的参数决策
```

### 数据源

| 文件 | 内容 | 状态 |
|------|------|------|
| `parameters.json` | 1594 条 ASPECT 参数定义 | 已有 |
| `cases.json` | 专家模拟案例（2 条文献清洗 + 19 条官方 cookbook） | 已有 |
| `cookbook_importer.py` | 官方 cookbook → 专家案例导入器 | 已有 |

案例来源两类：
- **官方 cookbook**（`cookbook_importer.py`，19 条）：从 `cookbooks/*.prm` 直接解析，
  参数 100% 与官方配置一致，rationale 为人工撰写的物理意图。跨领域覆盖
  benchmark（convection-box / van-keken / stokes）、球壳（2d/3d、bunge 深度相关粘度）、
  熔融运移（mid-ocean-ridge）、组分场（passive/active/particles）、自由表面
  （free-surface / crustal-deformation / continental-extension）、俯冲起始等。
- **文献清洗**（`extractor.py`，2 条）：OCR 论文 → LLM 结构化抽取。

### 模块

| 模块 | 职责 |
|------|------|
| `parameter_searcher.py` | 参数定义检索（关键词模糊搜索，name > section > doc 加权） |
| `case_searcher.py` | 专家案例检索（关键词 + 领域过滤，title > tags > description 加权） |
| `rag.py` | 统一入口 `AspectRAG`，一次搜索同时返回参数 + 案例 |
| `cookbook_importer.py` | 官方 cookbook → 专家案例导入（解析 `.prm`，无 LLM） |

## 使用

```python
from RAG import AspectRAG

rag = AspectRAG()
print(rag.parameter_count)  # 1594
print(rag.case_count)       # 21（2 文献 + 19 cookbook）

# 统一搜索：同时返回参数定义 + 相关案例
result = rag.search("CFL")
for p in result.parameters:
    print(f"  {p.name}: {p.default}  — {p.documentation[:80]}")
for c in result.cases:
    print(f"  案例: {c.title}")
    for d in c.parameter_decisions:
        print(f"    {d.parameter_name} = {d.value}  ({d.rationale})")
```

### 单独使用检索器

```python
from RAG import ParameterSearcher, CaseSearcher

# 参数检索
ps = ParameterSearcher()
ps.get("CFL number")        # 精确查询
ps.search("time step")      # 关键词搜索

# 案例检索
cs = CaseSearcher()
cs.search("subduction", domain="mantle convection")  # 按领域过滤
cs.by_parameter("CFL number")  # 反查使用某参数的案例
```

## 案例库扩充

### 官方 cookbook 导入（无需 LLM）

从 ASPECT 官方 cookbooks 生成专家案例：参数 100% 忠实于 `.prm` 文件，
rationale 为人工撰写的物理意图，支持多行续行、行内注释与 `include` 去重。

```bash
uv run python -m RAG.cookbook_importer --dry-run   # 预览不落盘
uv run python -m RAG.cookbook_importer             # 合并进 cases.json
uv run python -m RAG.cookbook_importer --overwrite # 覆盖同 case_id 旧记录
```

案例清单在 `cookbook_importer.py` 的 `CASES` 常量中定义，修改后重跑即增量更新。

### 文献清洗（LLM 结构化抽取）

```bash
uv run python -m RAG.extractor test_case/OCR_xxx.md --dry-run  # 预览不落盘
uv run python -m RAG.extractor test_case/OCR_xxx.md            # 合并进 cases.json
```

## cases.json Schema

`RAG/cookbook_importer.py` 与 `RAG/extractor.py` 共同按此 schema 生成案例
（顶层 JSON 实测仅含 `cases` 键，`source`/`count` 为可选元信息）：

```json
{
  "source": "expert_cases",
  "count": 21,
  "cases": [
    {
      "case_id": "cookbook-heat-flow",
      "title": "Heat flow in a square",
      "domain": "heat conduction",
      "description": "2D steady-state heat conduction benchmark",
      "source": "cookbooks/heat_flow/heat-flow.prm",
      "prm_path": "cookbooks/heat_flow/heat-flow.prm",
      "parameter_decisions": [
        {
          "parameter_name": "Dimension",
          "value": "2",
          "rationale": "2D 足以验证稳态热传导解析解"
        },
        {
          "parameter_name": "CFL number",
          "value": "0.5",
          "rationale": "降低 CFL 以保证首步稳定性"
        }
      ],
      "outcome": "收敛，误差 < 1%",
      "success": true,
      "tags": ["benchmark", "heat", "steady-state", "2D"]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `case_id` | str | 唯一标识 |
| `title` | str | 案例标题 |
| `domain` | str | 领域（mantle convection / subduction / heat conduction …） |
| `description` | str | 物理模型与边界条件描述 |
| `source` | str | 来源引用 |
| `prm_path` | str | 关联 .prm 文件 |
| `parameter_decisions` | list | 专家参数决策列表 |
| `parameter_decisions[].parameter_name` | str | ASPECT 参数名（与 parameters.json 关联） |
| `parameter_decisions[].value` | str | 设定值 |
| `parameter_decisions[].rationale` | str | 决策原因（专家经验） |
| `outcome` | str | 运行结果 |
| `success` | bool | 是否成功 |
| `tags` | list[str] | 检索标签 |

## 检索打分机制

### 参数搜索 (`ParameterSearcher.search`)

| 匹配位置 | 分数 |
|----------|------|
| 完整关键词命中 name | +1000 |
| 分词命中 name | +100/词 |
| 完整关键词命中 section | +100 |
| 分词命中 section | +30/词 |
| 完整关键词命中 documentation | +50 |
| 分词命中 documentation | +5/词 |

### 案例搜索 (`CaseSearcher.search`)

| 匹配位置 | 分数 |
|----------|------|
| 完整关键词命中 title | +1000 |
| 分词命中 title | +200/词 |
| 命中 tag | +150/词 |
| 完整关键词命中 domain | +100 |
| 完整关键词命中 description | +50 |
| 分词命中 description | +10/词 |
| 命中 rationale | +5/词 |

### 参数→案例关联

`AspectRAG.search` 在案例直接搜索无结果时，会通过命中的参数名反查案例
（`CaseSearcher.by_parameter`），形成 **参数定义 → 专家决策** 的知识闭环。

## 后续扩展计划

1. **文献清洗 → cases.json**：从 ASPECT cookbook、论文、实际项目中提取专家决策
2. **向量化检索**：当案例规模增大后，引入 embedding 替代关键词匹配
3. **参数→案例图谱**：构建参数与案例的关联图，支持"该参数在哪些场景下常用什么值"
4. **失败案例库**：记录失败决策及其原因，供 agent 修复循环参考
5. **版本化**：cases.json 增加 `aspect_version` 字段，支持版本过滤
