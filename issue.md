# aspect_prm_builder Review Issues

Review date: 2026-07-22
ASPECT version: 3.1.0-pre (`/Users/bai/workspace/aspect-main/build/aspect-release`)

## Bugs

### 1. 缺少 `__main__.py`，CLI 入口不可用

`python -m aspect_prm_builder` 报错：

```
No module named aspect_prm_builder.__main__; 'aspect_prm_builder' is a package and cannot be directly executed
```

**修复：** 添加 `aspect_prm_builder/__main__.py`：

```python
import sys
from .main import main

sys.exit(main())
```

### 2. `main.py` 的 `load_answers` 对 `.prm` 文件误用 `json.load`

`main.py:31-33`：

```python
if p.suffix in (".json", ".prm"):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
```

`.prm` 文件不是 JSON，应调用 `assembler.parse_prm()`。

**修复：**

```python
if p.suffix == ".json":
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
if p.suffix == ".prm":
    return assembler.parse_prm(p.read_text(encoding="utf-8"))
```

### 3. `connector/config.json` 中 binary 路径与实际不符

默认配置指向 `aspect`，而本机实际 binary 为 `aspect-release`。`ConnectorConfig.default()` 同样硬编码了错误路径。

## 设计改进建议

### 4. schema 与真实 ASPECT 参数缺乏同步机制

当前 schema 是手工维护的子集，参数名拼写偏差会导致 ASPECT 运行时报错。建议利用 `RAG/parameters.json`（完整参数表）或 `aspect --help` 输出做自动校验/生成。

### 5. `parse_prm` 不处理 `include` 指令

真实 cookbook 常用 `include "file.prm"` 引入子文件，当前解析器会静默忽略，导致往返解析丢失参数。

### 6. validator 不检查条件依赖

例如选了 `Geometry model.Model name = spherical shell` 但答案中包含 `Geometry model.Box.X extent`，当前不会警告。可结合 engine 的 `_subsection_active` 逻辑做交叉校验。

### 7. 缺少单元测试

建议为 schema / assembler / validator 添加 pytest 测试套件，至少覆盖：

- 必填参数缺失
- 非法 choice 值
- 类型不匹配
- strict 模式
- parse_prm 往返一致性
- 真实 cookbook 解析

## 测试通过项（供参考）

| 测试项 | 结果 |
|--------|------|
| demo.py 生成 convection_box.prm → ASPECT 完整运行 1072 步 | PASS |
| llm_example.py 生成 van Keken benchmark → ASPECT 正常求解 | PASS |
| parse_prm 往返解析（37 参数，re-assemble 后 validation 无错误） | PASS |
| 解析真实 ASPECT cookbook（48 参数正确提取） | PASS |
| validator 边界测试（缺失必填、非法 choice、类型错误、strict） | PASS |
| CLI pipeline（JSON → validate → .prm） | PASS |
| connector 端到端（生成 → 运行 → 成功，14.8s） | PASS |
