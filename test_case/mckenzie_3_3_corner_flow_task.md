# Benchmark 3.3: Constant Porosity Corner Flow

## 任务描述

请帮我生成一个 ASPECT 参数文件，模拟等孔隙度、等粘度条件下的角流（corner flow）问题，用于验证动态压力梯度驱动的熔体聚焦。

## 物理背景

McKenzie 方程组在 phi = 1, K = 1, eta/xi 常数, Gamma = 0 时的退化情形（Spiegelman et al. 2007, Section 3.3）。压实压力 P = 0，固体流场为不可压缩 Stokes：

- div(V) = 0
- grad(P*) = eta * nabla^2(V) - phi_0 * k

动态压力梯度 grad(P*) 驱动熔体流动。此问题被 Spiegelman & McKenzie (1987) 用于洋中脊和岛弧下方熔体聚焦的解析模型。

## 具体要求

- 2D 笛卡尔盒模型，区域 1×1（无量纲）
- 等粘度 eta = 1，密度 = 1
- 重力竖直向下，大小 = 1
- 无热膨胀（alpha = 0），等温
- 边界条件：
  - 顶边：施加水平速度 u = 1（模拟板块运动）
  - 左边：施加垂直速度 v = -1（模拟下沉）
  - 其余边：自由滑移
- 不求解温度方程（no Advection, iterated Stokes）
- 网格：4×4 重复，全局加密 4 级
- 后处理：visualization + velocity statistics
- 运行到 t = 1

## 验证标准

- 角点处压力奇异（解析已知，Batchelor 1967）
- 等值线呈角流特征
- 动态压力梯度可用于计算熔体流线（Spiegelman & McKenzie 1987, Figure 1）

## 参考文献

- Spiegelman, M., Katz, R., Simpson, G. (2007). Section 3.3, Eq. 3.7-3.10.
- Spiegelman, M., McKenzie, D. (1987). Simple 2-D models for melt extraction at mid-ocean ridges and island arcs. EPSL, 83:137-152.
