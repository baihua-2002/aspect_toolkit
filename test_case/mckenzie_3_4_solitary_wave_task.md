# Benchmark 3.4: Magmatic Solitary Waves

## 任务描述

请帮我生成一个 ASPECT 参数文件，模拟一维岩浆孤立波（magmatic solitary wave）在均匀孔隙度背景上的传播。

## 物理背景

McKenzie 方程组在小孔隙度极限（phi_0 << 1）下的非线性色散波解（Spiegelman et al. 2007, Section 3.4）。eta 常数，xi = 1，Gamma = 0，渗透率 K = phi^n（n=3）：

- D(phi)/Dt = P
- -div(phi^n * grad(P)) + P = div(phi^n * g_hat)

该系统支持 1D/2D/3D 非线性孤立波，以固定形态和恒定相速度在均匀背景上传播。1D 情形对所有整数 n 存在解析解（Barcilon & Richter 1986, n=3）。

## 具体要求

- 2D 笛卡尔盒模型（近似 1D）：X 方向极窄（0.1），Y 方向长（4）
- X 重复 1，Y 重复 16（高分辨率纵向网格）
- 等粘度 eta = 1，密度 = 1
- 重力竖直向下，大小 = 1
- 无热膨胀（alpha = 0），等温（T = 1）
- 边界条件：四边自由滑移，顶底固定温度
- 初始条件：均匀背景（T = 1 代表均匀孔隙度）
- 网格：全局加密 3 级 + 自适应加密 2 级，每 5 步重网格
- CFL = 0.3，最大时间步 0.1
- 后处理：visualization + velocity statistics
- 运行到 t = 5（足够观察波传播）

## 验证标准

- 孤立波以恒定相速度传播，形态不变
- 任何色散或耗散均为数值伪影
- 波速与 Barcilon & Richter (1986) 解析解一致

## 参考文献

- Spiegelman, M., Katz, R., Simpson, G. (2007). Section 3.4, Eq. 3.11-3.12.
- Barcilon, V., Richter, F.M. (1986). Non-linear waves in compacting media. J. Fluid Mech., 164:429-448.
- Spiegelman, M. (1993). Flow in deformable porous media. J. Fluid Mech., 247:17-38.
