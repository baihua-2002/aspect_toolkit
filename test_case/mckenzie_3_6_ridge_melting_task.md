# Benchmark 3.6: 2D Ridge Model with Forced Adiabatic Melting

## 任务描述

请帮我生成一个 ASPECT 参数文件，模拟二维洋中脊下方的熔体生成与运移过程，包含强制绝热熔融。

## 物理背景

McKenzie 方程组的完整求解（Spiegelman et al. 2007, Section 3.6），加入熔融源项：

- Gamma = rho_s * W * dF/dz

其中 W 为固体上升速度，F(z) = F_max/d 为 imposed 线性熔融函数（描述固相线以上高度的熔融程度）。该问题模拟洋中脊下方熔体和固体的耦合流动，由 Spiegelman (1996) 和 Scott & Stevenson (1989) 发展。

## 具体要求

- 2D 笛卡尔盒模型：X = 4，Y = 3（无量纲，代表洋脊半宽和深度）
- X 重复 8，Y 重复 6
- 等粘度 eta = 1，密度 = 1
- 重力竖直向下，大小 = 1
- 无热膨胀（alpha = 0）
- 边界条件：
  - 顶边：施加对称分离速度（左半 u = -1，右半 u = +1，模拟板块扩张）
  - 底边和侧边：自由滑移
  - 顶底固定温度（底 T=1，顶 T=0）
- 初始温度：线性剖面 T = 1 - y/3
- 网格：全局加密 3 级 + 自适应加密 2 级，每 5 步重网格
- CFL = 0.3，最大时间步 0.5
- 后处理：visualization + velocity statistics + temperature statistics
- 运行到 t = 10

## 验证标准

- 脊轴下方形成高孔隙度通道（熔体聚焦）
- 固体流线呈对称上涌模式
- 熔体流线向脊轴汇聚
- 孔隙度浮力数 R 控制流动形态（Spiegelman 1996, Figure 4）

## 参考文献

- Spiegelman, M., Katz, R., Simpson, G. (2007). Section 3.6, Eq. 3.18.
- Spiegelman, M. (1996). Geochemical consequences of melt transport in 2-D. EPSL, 139:115-132.
- Scott, D.R., Stevenson, D.J. (1989). A self-consistent model of melting, magma migration and buoyancy-driven circulation beneath mid-ocean ridges. JGR, 94:2973-2988.
