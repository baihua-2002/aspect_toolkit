# 测试用例设计：同一用例 × 双难度描述（详细版 / 模糊版）

## 1. 设计动机

现有用例（`*_task.md`）都是"详细版"：物理背景、几何、材料、边界、网格、运行时长全部显式给出，
LLM 只需做"需求 → 参数点路径"的映射。这只能检验一种能力：**给定完整需求时的参数保真度**
（对应 P3 评估指标中的"端到端参数正确率"，失败模式 E3：检索到了但没用对）。

但实际用户不会这样提需求。真实场景是模糊的："帮我算一下洋中脊下面的岩浆运移"——几何多大、
粘度多少、跑多久，用户统统不知道，这些恰恰是 Agent 应该靠 RAG/文献/物理常识补全的部分。

因此把**每一个用例**做成两个描述版本，刻意拉开难度，分别"考验"不同的能力维度：

| 版本 | 信息量 | 考验的能力 | 失败模式 | 评分方式 |
|------|--------|-----------|---------|---------|
| **详细版** `*_task.md` | 全部参数显式给出 | 参数映射保真、不擅自改动、点路径对齐 | E3（检索到了但没用对）| 与 `*_answers.json` 精确比对（机器可判） |
| **模糊版** `*_task_vague.md` | 只给目标与极少量约束 | 需求分析、RAG 检索、假设补全、假设披露、物理判别特征 | E1/E2 之外：**知识-补全能力** | 运行成功 + 物理判别特征 + 假设披露质量（人工/半自动） |

> 同一用例两份描述、同一份 ground truth（物理现象），可以 A/B 对比同一个模型在
> "照抄式任务" 与 "推理式任务" 上的能力差，也能量化"模糊度 → 性能衰减"曲线。

## 2. 命名与目录约定

```
test_case/
├── README.md                              # 本设计文档
├── run_benchmark.py                       # 一键跑某个用例的某版本（详细/模糊）
├── <case>_task.md                         # ① 详细版：完整需求（现有文件，保持不变）
├── <case>_answers.json                    # ① 详细版标准答案（仅评分用，不喂给 agent）
├── <case>_task_vague.md                   # ② 模糊版：给 agent 看的"用户原话"
└── <case>_vague_acceptance.md             # ② 模糊版验收标准（仅评分用，不喂给 agent）
```

- **详细版答案** `*_answers.json`：唯一的真值来源。详细版评分由机器完成（见 §3）。
- **模糊版验收** `*_vague_acceptance.md`：物理判别特征 + 允许的参数范围 + 假设披露要求。
  这份文件**不能出现在 agent 的输入里**，否则模糊版退化为详细版。
- 模糊版的**标准答案就是详细版的 answers.json**——同一物理场景，两份描述殊途同归。

## 3. 详细版（信息全给）— 考验"参数保真度"

**给 agent 的输入**：`<case>_task.md`（物理背景 + 全部具体参数 + 验证标准）。

**评分（机器可判，0-100）**：

| 维度 | 权重 | 判据 |
|------|------|------|
| 运行成功 | 40 | `run_aspect_simulation` 返回 success，正常终止到 End time |
| 参数正确率 | 40 | 与 `*_answers.json` 逐项比对（`validator` 能自动对齐点路径）；数值允许 1e-9 相对误差；单位换算等价可接受 |
| 无越界项 | 10 | 不出现答案里没有、且改变物理本质的参数（如擅自加熔融/加热模型） |
| 关键项命中 | 10 | 判别性参数（边界条件、物理模型名、几何尺度）必须命中，缺一项即全扣 |

**能力意义**：分数低 = 参数检索/映射链路（RAG 参数定义 → validator → assembler）有问题，
与 P3 的"端到端参数正确率"直接挂钩。

## 4. 模糊版（信息稀缺）— 考验"需求-补全能力"

**给 agent 的输入**：`<case>_task_vague.md`。设计要点：

1. **只给目标与不可推演的约束**。可推演的信息（盒子尺寸的量级、物理模型选择、边界条件类型）
   一律不给——这正是要考验的部分。
2. **给一条"处理要求"**：明确要求 agent 对每个"没被明确告知、只能靠假设补齐"的参数写出
   假设与依据（ASPECT 默认 / 文献 / 检索到的案例），即 P1.⑩ 的防幻觉覆盖报告。
   这条属于**过程要求**而非答案泄漏，必须保留。
3. **给"期望结果（提示）"**：用一两句话描述现象（如"熔体往脊轴汇聚形成高孔隙通道"），
   作为 agent 自查方向的锚点，但绝不给数值。
4. 文本刻意使用口语化、有歧义的表达（如"细长的盒子""差不多就行"），模拟真实用户。

**评分（半自动，0-100）**，依据 `*_vague_acceptance.md`：

| 维度 | 权重 | 判据 |
|------|------|------|
| 运行成功 | 30 | .prm 能跑通并正常终止（网格/时长在允许范围内即可，不要求与详细版逐字一致） |
| 物理判别特征 | 30 | 验收文件列出的 2-3 个判别性现象（用可视化/statistics 判定），如：单涡 / 对流胞 / 脊轴熔体聚焦 / 波形稳定传播 |
| 参数合理性 | 20 | 每个被补全的参数落在验收文件允许的合理区间（如重力量级、粘度量级、网格分辨率下限） |
| 假设披露 | 20 | agent 明确列出：哪些参数来自需求、哪些来自 RAG/案例、哪些是自行假设，无沉默省略 |

> 模糊版**不存在唯一正确答案**（合理假设 ≠ 答案），所以**不设** `*_answers.json` 式的逐项比对，
> 详细版 answers 只作为"人类评委的参考基准"。

## 5. 用例矩阵（现状 + 本设计新增）

| 用例 | 物理场景 | 详细版 | 详细版答案 | 模糊版（新增） | 模糊版验收（新增） |
|------|---------|:------:|:---------:|:--------------:|:------------------:|
| mckenzie_3_1_stokes | 盖子驱动空腔流（零孔隙 Stokes） | ✅ | ✅ | ✅ | ✅ |
| mckenzie_3_2_passive_advection | 零渗透率被动平流 | ✅ | ✅ | ✅ | ✅ |
| mckenzie_3_3_corner_flow | 等孔隙角流（洋脊/岛弧熔体聚焦） | ✅ | ✅ | ✅ | ✅ |
| mckenzie_3_4_solitary_wave | 岩浆孤立波传播 | ✅ | ✅ | ✅ | ✅ |
| mckenzie_3_5_shear_bands | 剪切带自发形成 | ✅ | ✅ | ✅ | ✅ |
| mckenzie_3_6_ridge_melting | 洋中脊强制绝热熔融 | ✅ | ✅ | ✅ | ✅ |
| ncc_thermal_thinning_minimal | 华北克拉通热对流侵蚀减薄 | ✅ | ✅ | ✅ | ✅ |
| ncc_thermal_thinning_pdf | 论文 PDF 端到端抽取复现 | ✅（PDF 即详细源） | 参考 prm | 待补 | 待补 |

> 目录型用例（`subduction/`、`continental_extension/`、`shell_simple_2d/`、
> `free_surface_with_crust/`、`subduction_initiation/`）目前只有 .prm 无 task 文件，
> 可作为下一批双版本化候选。

## 6. 运行方式（自动化）

`test_case/run_benchmark.py` 为自动化运行器，自动发现用例、批量跑、自动评分汇总。

```bash
uv run python test_case/run_benchmark.py --list                     # 列出全部用例（详细/模糊/答案就绪状态）
uv run python test_case/run_benchmark.py --case mckenzie_3_1_stokes --version detailed
uv run python test_case/run_benchmark.py --case mckenzie_3_4_solitary_wave --version vague
uv run python test_case/run_benchmark.py --cases mckenzie_3_1_stokes,ncc_thermal_thinning_minimal --versions detailed,vague
uv run python test_case/run_benchmark.py --all --versions vague --provider deepseek
uv run python test_case/run_benchmark.py --report                 # 仅重新汇总历史结果
```

行为约定：

- **自动发现**：扫描 `test_case/` 下 `*_task.md`（详细）、`*_task_vague.md`（模糊）、
  `*_vague_acceptance.md`（验收）与子目录形式用例（如 `ncc_thermal_thinning_pdf/`）。
- **归档**：每次运行产物落到 `runs/<case>_<version>_<时间戳>/`（task、prompt、agent 输出、
  transcript、产出的 .prm、result.json），ASPECT 运行目录由 connector 落在 `runs/<prm_名>/`。
- **详细版自动评分（0-100）**：运行 40 + 参数比对 40 + 关键项 10 + 越界项 10（实现见
  `grade_detailed`）。其中参数项把 agent 亲笔产出的 .prm 用 `parse_prm` 解析后与
  `*_answers.json` 逐项比对（数值允许 1e-6 相对误差）；运行成功依据 ASPECT 日志中的
  `Termination requested by criterion` 判定。
- **模糊版**：不设机器分数，产出人工评分辅助（运行成功信号、产出的 .prm、假设披露片段抽取），
  供按 §4 与 `*_vague_acceptance.md` 人工判定。
- **汇总**：每批跑完自动更新 `runs/benchmark_summary.json` 与 `runs/benchmark_summary.md`；
  `--report` 可随时从历史 `result.json` 重生成。
- **鲁棒性**：单个用例异常/超时不影响整体；`--timeout` 控制单用例 agent 超时（默认 3600s）。
  注意超时仅停止等待，后台守护线程可能继续运行，批量请给足超时。

## 7. 新增用例 Checklist

1. 先写详细版 `*_task.md` + 真值 `*_answers.json`，人工跑通确认 answers 本身可运行；
2. 从详细版"信息脱敏"得到模糊版 `*_task_vague.md`：
   - 保留：目标、物理现象、不可推演的约束；
   - 移除：所有数值、所有显式参数名、模型选择；
   - 加入：假设披露要求 + 期望结果提示；
3. 写 `*_vague_acceptance.md`：判别特征（从 answers 反推）+ 允许参数区间 + 披露要求；
4. 双版本各跑一次，确认详细版分数 > 90、模糊版能靠假设跑通；
5. 更新本文件 §5 矩阵。
