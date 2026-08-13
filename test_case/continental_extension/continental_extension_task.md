# Benchmark: 陆缘伸展（Continental Extension，粘塑性 + 粒子 + 自由表面）

## 任务描述

请生成一个 ASPECT 参数文件，模拟大陆岩石圈的伸展破裂：200×100 km 的二维剖面，左右两侧以 0.25 cm/yr 的速度向外拉伸，底部以补偿性垂向流入平衡质量。模型采用粘塑性流变（位错蠕变 + Drucker-Prager 塑性 + 应变弱化），初始塑性应变种子位于中上部，促使正断层在预期位置发育；顶面为自由表面，可形成伸展盆地的地形起伏。参考 ASPECT cookbook: continental_extension。

## 物理背景

- **流变**：visco plastic 材料模型——位错蠕变（背景/地幔为干橄榄岩、上地壳湿石英岩、下地壳湿钙长石，各组分不同的前置因子/应力指数/激活能/激活体积）+ Drucker-Prager 塑性（内摩擦角 30°、粘聚力 20 MPa），塑性应变在 0.5–1.5 之间将摩擦角与粘聚力弱化 4 倍；塑性阻尼项启用（粘度 1e21 Pa·s）
- **组分场**（5 个，粒子方法 advect）：noninitial_plastic_strain、plastic_strain（应变型，初始 0.5–1.5 随机种子）、crust_upper、crust_lower、mantle_lithosphere（化学组分，上地壳 20 km、下地壳 20 km、岩石圈地幔 60 km 的水平层状）
- **初始温度**：Chapman (1986) 大陆地温（上地壳表面 273 K、热流 0.055 W/m²、热产率 1e-6 W/m³；下地壳热流 0.035 W/m²、热产率 0.25e-6 W/m³；地幔热流 0.030 W/m³；热导率全部 2.5 W/(m·K)），+ 组分加热（上/下地壳 1e-6 / 0.25e-6 W/m³）
- **粒子**：每个参考单元 5×5 个，属性：initial composition、viscoplastic strain invariants、position；插值 bilinear least squares
- **自由表面**：顶面 free surface（法向投影）+ diffusion（坡度输运系数 1e-8），左右边界附加切向网格速度
- 边界速度：左/右边界 x 方向 ±0.25 cm/yr（函数：x < 100 km 向左、否则向右），底部 y 方向 0.25 cm/yr 补偿；组分在底部固定为初始值

## 具体要求

- 2D 笛卡尔盒：X 200 km × Y 100 km，X 10 个重复单元、Y 5 个；全局加密 2 级，无自适应细化，运行中不细化（基准版本削减了 cookbook 的细化策略）
- 非线性：iterated Advection and Stokes，容差 1e-4，最大 200 次迭代
- 求解器：block AMG，线性容差 1e-8，GMRES restart 100，full A block 预处理
- 时间：CFL 0.5，最大时间步 5e3 yr，**End time = 2e4 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 后处理：basic statistics、velocity statistics、topography、visualization（material properties: density, viscosity）；可视化输出间隔 = End time

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 输出目录：output-continental_extension

## 验收要点

- 运行成功、正常终止
- 伸展速度边界驱动岩石圈变形（RMS velocity > 0）
- 塑性应变种子区域发生应变弱化（viscoplastic strain invariants 随时间增长）
- 自由表面产生地形起伏（topography 输出非零/可分辨）
