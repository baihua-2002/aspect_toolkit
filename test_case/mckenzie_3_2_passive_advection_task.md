# Benchmark 3.2: Zero Permeability Passive Advection

## 任务描述

请帮我生成一个 ASPECT 参数文件，模拟零渗透率条件下的被动孔隙度平流问题。

## 物理背景

McKenzie 方程组在 K = 0、Gamma = 0 时的退化情形（Spiegelman et al. 2007, Section 3.2）。固体基质不可渗透，孔隙度作为被动示踪剂被流场平流：

- D(phi)/Dt = 0（孔隙度物质守恒）
- div(V) = 0（不可压缩）
- grad(P*) = div(eta*(grad(V)+grad(V)^T)) - phi_0*phi*g_hat（含浮力的 Stokes）

## 具体要求

- 2D 笛卡尔盒模型，区域 1×1（无量纲）
- 等粘度 eta = 1，密度 = 1
- 重力竖直向下，大小 = 1
- 热膨胀系数 alpha = 1（浮力驱动对流）
- 边界条件：四边自由滑移，顶底固定温度（底 T=1，顶 T=0）
- 初始温度：线性剖面 + 小扰动 0.01*sin(pi*x)*sin(pi*y)
- 网格：4×4 重复，全局加密 4 级
- 后处理：visualization + velocity statistics + temperature statistics
- 运行到 t = 1，最大时间步 0.1

## 验证标准

- 孔隙度场被流场被动平流，无数值扩散（理想情况）
- 流场由热浮力驱动，形成对流胞
- 不可压缩约束 div(V) = 0 满足

## 参考文献

Spiegelman, M., Katz, R., Simpson, G. (2007). Section 3.2, Eq. 3.3-3.6.
