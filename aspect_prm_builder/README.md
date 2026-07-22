# ASPECT `.prm` 参数中间件

一个用于**降低 LLM 编写 ASPECT 参数文件心智负担**的中间件系统。

LLM 不需要直接写 `.prm` 文本，只需要按 Schema 回答具体的参数配置（或生成一个 JSON 答案字典），本中间件负责校验、组装并输出符合 ASPECT 语法的 `.prm` 文件。

---

## 核心设计

| 模块 | 说明 |
|------|------|
| `schema.py` | ASPECT 参数 Schema 定义，包含参数类型、默认值、依赖关系，可导出为 JSON |
| `engine.py` | 交互式提问引擎，按 Schema 逐步询问，支持根据选择项自动跳过无关子分支 |
| `assembler.py` | 将答案字典序列化为 `.prm` 文件；也支持把已有 `.prm` 解析为答案字典 |
| `validator.py` | 校验答案的类型、必填项、选择项合法性 |
| `main.py` | 命令行入口 |
| `demo.py` | 示例：从答案字典重建 `convection-box` |
| `llm_example.py` | 示例：从答案字典重建 `van-keken-smooth` |

---

## 快速开始

### 1. 从 LLM 答案生成 `.prm`

准备一个 JSON 文件 `answers.json`：

```json
{
  "Dimension": 2,
  "End time": 0.5,
  "Geometry model.Model name": "box",
  "Geometry model.Box.X extent": 1,
  "Geometry model.Box.Y extent": 1,
  "Material model.Model name": "simple",
  "Material model.Simple model.Viscosity": 1,
  "Postprocess.List of postprocessors": [
    "visualization",
    "velocity statistics",
    "temperature statistics"
  ]
}
```

然后运行：

```bash
PYTHONPATH=. python3 -m aspect_prm_builder.main \
  --answers answers.json \
  --output my_model.prm
```

### 2. 交互式生成

```bash
PYTHONPATH=. python3 -m aspect_prm_builder.main --output my_model.prm
```

### 3. 从已有 cookbook 导入并改写

```bash
PYTHONPATH=. python3 -m aspect_prm_builder.main \
  --from van-keken/van-keken-smooth.prm \
  --output output.prm \
  --save-answers output.json
```

### 4. 导出 Schema 给 LLM 作为上下文

```bash
PYTHONPATH=. python3 -m aspect_prm_builder.main \
  --export-schema aspect_prm_builder/generated_examples/schema.json
```

---

## Python API 用法

```python
from aspect_prm_builder import assembler, engine, schema, validator

# 1. 准备答案（通常由 LLM 生成）
answers = {
    "Dimension": 2,
    "End time": 0.5,
    "Geometry model.Model name": "box",
    "Geometry model.Box.X extent": 1,
    "Geometry model.Box.Y extent": 1,
    "Material model.Model name": "simple",
    "Material model.Simple model.Viscosity": 1,
}

# 2. 校验
errors = validator.validate_answers(answers, schema.build_schema())
if errors:
    for path, msg in errors:
        print(f"{path}: {msg}")

# 3. 组装为 .prm 文本
prm_text = assembler.assemble_prm(answers, schema.build_schema())
print(prm_text)

# 4. 或直接写入文件
assembler.write_prm("my_model.prm", answers, schema.build_schema())
```

---

## 目录结构

```
aspect_prm_builder/
├── __init__.py          # 包入口
├── schema.py            # 参数 Schema
├── engine.py            # 交互式引擎
├── assembler.py         # .prm 组装与解析
├── validator.py         # 校验器
├── main.py              # CLI
├── demo.py              # convection-box 示例
├── llm_example.py       # van-keken-smooth 示例
└── generated_examples/  # 已生成的示例 .prm 和 JSON
```

---

## 扩展 Schema

ASPECT 插件众多，本中间件的 Schema 只覆盖了常见参数。如需支持新插件，在 `schema.py` 的 `build_schema()` 中：

- 添加新的 `ScalarParameter`（数值/字符串）
- 添加 `BoolParameter`（布尔）
- 添加 `ChoiceParameter`（单选）
- 添加 `ListParameter`（列表）
- 添加 `Subsection`（嵌套子节）
- 对不确定的参数使用 `RawParameter` 作为逃生口

示例：

```python
P("My new parameter", "描述", default=1.0),
S("My section", "新子节", [
    P("Sub param", "子参数", default="value")
])
```

---

## 设计原则

1. **LLM 只回答参数值，不记语法**。Schema 负责把答案转成正确的 ASPECT 格式。
2. **默认值和依赖处理**。有默认值的参数可以省略；选择不同模型时自动跳过不相关子节。
3. **可验证**。生成前会检查类型、必填项、选择项合法性。
4. **可扩展**。通过 Schema 即可新增 ASPECT 插件支持。

---

## 示例输出

详见 `generated_examples/` 目录：

- `convection_box_demo.prm`
- `van_keken_smooth_demo.prm`
- `roundtrip_convection_box.prm`
- `roundtrip_van_keken_smooth.prm`
- `schema.json`
