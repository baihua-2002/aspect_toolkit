# Connector — ASPECT 交互中间件

屏蔽系统差异，运行指定的 `.prm` 文件，获得结构化结果。

## 使用

```python
from connector import AspectConnector

connector = AspectConnector()  # 自动加载 connector/config.json
connector.validate()           # 检查 ASPECT binary 是否可用

result = connector.run("path/to/model.prm")
print(result.success)           # bool
print(result.elapsed_seconds)   # 运行耗时
print(result.output_directory)  # 输出目录路径
print(result.stderr)            # 错误信息（用于 agent 修复循环）
```

## 配置 (config.json)

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `aspect_binary` | ASPECT 可执行文件路径 | — |
| `mpirun_binary` | MPI 启动器（空字符串表示不使用） | `"mpirun"` |
| `default_nproc` | 默认 MPI 进程数（1=串行） | `1` |
| `working_directory` | 运行输出根目录 | `"./runs"` |
| `default_timeout_seconds` | 超时时间 | `3600` |
| `extra_args` | 传递给 ASPECT 的额外参数 | `[]` |

## 运行隔离

每次运行在 `working_directory/<prm文件名>/` 下执行，输出互不干扰。

## 错误处理

- 配置错误（binary 不存在、prm 文件不存在）→ 抛出异常
- 运行时失败（ASPECT 退出码非零、超时）→ 返回 `RunResult(success=False, ...)`，不抛异常

## 异步运行

```python
proc = connector.run_async("long_simulation.prm")
# 自行 poll/等待
proc.wait()
```
