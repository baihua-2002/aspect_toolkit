# Benchmark 3.5: Magmatic Shear Bands

## 任务描述

请帮我生成一个 ASPECT 参数文件，模拟孔隙弱化粘度条件下的剪切带（shear band）自发形成过程。

## 物理背景

McKenzie 方程组在无熔融、无浮力条件下的剪切局部化问题（Spiegelman et al. 2007, Section 3.5）。Gamma = 0，g_hat = 0，粘度依赖于孔隙度和应变率：

- D(phi)/Dt = (1 - phi_0*phi) * P/xi
- -div(K*grad(P)) + P/xi = div(K*grad(P*))
- div(V) = phi_0 * P/xi
- grad(P*) = div(eta*(grad(V)+grad(V)^T))

本构关系：eta(phi, eps_dot) = eta_0 * exp(alpha*(phi - phi_0)) * eps_II^((1-n)/n)

其中 alpha = -28 ± 3（孔隙弱化系数），n = 1（Newtonian）。该机制解释了剪切变形实验中观察到的低角度富熔体带（Katz et al. 2006, Nature）。

## 具体要求

- 2D 笛卡尔盒模型：X = 2，Y = 1
- X 重复 8，Y 重复 4
- 等粘度 eta = 1（基准），密度 = 1
- 无重力（或重力 = 0）
- 无热膨胀（alpha = 0），等温（T = 1）
- 边界条件：
  - 顶边：施加水平速度 u = 1（简单剪切驱动）
  - 底边：固定（u = 0, v = 0）
  - 顶底固定温度
- 初始条件：均匀背景 + 小扰动 0.01*sin(2*pi*x)*sin(2*pi*y)
- 网格：全局加密 4 级 + 自适应加密 2 级，每 5 步重网格
- CFL = 0.3，最大时间步 0.05
- 后处理：visualization + velocity statistics
- 运行到 t = 0.5

## 验证标准

- 孔隙度局部化形成低角度（~15-30°）剪切带
- 带方向与最大开启方向一致（Stevenson 1989）
- 涡度扰动在带内集中
- 结果与 Katz et al. (2006) Figure 1 定性一致

## 参考文献

- Spiegelman, M., Katz, R., Simpson, G. (2007). Section 3.5, Eq. 3.13-3.17.
- Katz, R., Spiegelman, M., Holtzman, B. (2006). The dynamics of melt and shear localization in partially molten aggregates. Nature, 442:676-679.
- Stevenson, D.J. (1989). Spontaneous small-scale melt segregation in partial melts undergoing deformation. GRL, 16(9):1067-1070.
