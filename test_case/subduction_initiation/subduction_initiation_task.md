# Benchmark: 俯冲起始（Subduction Initiation，Matsumoto & Tomoda 1983）

## 任务描述

请生成一个 ASPECT 参数文件，复现二维俯冲起始模型。初始时刻洋陆边界两侧密度不均（大洋侧岩石圈密度大于软流圈），在重力作用下岩石圈开始向洋侧下方下沉，模拟俯冲的起始过程。

## 物理背景

参考 Matsumoto & Tomoda (1983)：模型为一个二维矩形剖面，左半为"洋侧"、右半为"陆侧"（以 x = L0 = 300 km 为界）。模型包含 4 个组分：

1. 左侧软流圈（低密度）
2. 右侧软流圈（低密度）
3. 左侧岩石圈（高密度，大洋岩石圈）
4. 右侧岩石圈（高密度，大陆岩石圈）

另有一"水"材料（粘度极低），覆盖在岩石圈以上，代表上覆海水/沉积层。密度差驱动流动，无热效应（热膨胀系数为 0）。

## 具体要求

- 2D 笛卡尔盒模型，X 方向 400 km，Y 方向 180 km，X 方向 2 个重复单元
- 4 个组分场，初始分布由函数给出（几何关系：左侧岩石圈厚 18 km；右侧岩石圈在 60 km 深以下；水层覆盖在最上部；组分交界面按 L0、H=180 km 定义）
- 材料模型：multicomponent，5 种材料（背景软流圈两侧 + 两种岩石圈 + 水），粘度用谐波平均
- 重力：垂直向下，9.81 m/s²
- 边界条件：四面切向速度（free slip）；温度在上下边界固定
- 初始温度：0（无热效应）
- 压力归一化：surface
- 网格：全局加密 5 级，运行中不细化
- 时间：CFL 数 1.0，最大时间步 1e5 yr，**End time = 1.4e5 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 后处理：visualization（含 material properties、strain rate）、velocity statistics、composition statistics、pressure statistics、material statistics、global statistics；可视化输出间隔 = End time（初始 + 最终两帧）

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 输出目录：output-subduction_initiation

## 验收要点

- 运行成功、正常终止
- 组分质量守恒（composition statistics 中四种组分的总质量不随模拟剧烈变化）
- 初始时刻流速由密度差驱动（RMS velocity > 0）
