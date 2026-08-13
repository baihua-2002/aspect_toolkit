# Benchmark 3.1: Zero Porosity Stokes Flow

## 任务描述

请帮我生成一个 ASPECT 参数文件，用于验证不可压缩 Stokes 流求解器。

## 物理背景

这是 McKenzie 方程组在零孔隙度、无熔融极限下的退化情形（Spiegelman, Katz, Simpson 2007, Section 3.1）。方程简化为：

- div(V) = 0
- grad(P*) = div(eta * (grad(V) + grad(V)^T))

流场完全由边界条件驱动，无体积力。

## 具体要求

- 2D 笛卡尔盒模型，区域 1×1（无量纲）
- 等粘度 eta = 1，密度 = 1
- 无重力（或重力设为 0）
- 无热膨胀（alpha = 0），等温（T = 0）
- 边界条件：四边自由滑移（tangential），顶边施加水平速度 u = 1（lid-driven cavity）
- 不求解温度方程（no Advection, iterated Stokes）
- 网格：4×4 重复，全局加密 4 级
- 后处理：visualization + velocity statistics
- 运行到 t = 1 即可（稳态问题）

## 验证标准

- 顶边驱动下形成经典单涡结构
- 速度场满足无散度约束
- 压力场在角点处有奇异性（解析已知）

## 参考文献

Spiegelman, M., Katz, R., Simpson, G. (2007). An Introduction and Tutorial to the "McKenzie Equations" for magma migration. Section 3.1, Eq. 3.1-3.2.
