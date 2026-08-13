# Benchmark: 2D 笛卡尔俯冲-裂谷（World Builder 初始条件）

## 任务描述

请生成一个 ASPECT 参数文件，使用 **Geodynamic World Builder** 文件定义初始温度与组分结构，模拟二维俯冲-裂谷剖面：左侧为洋中脊（正在扩张的海洋板块），右侧为大陆板块，两者之间为正在俯冲的板片（95 km 厚的俯冲板片以 45° 倾角下插）。

## 物理背景

初始结构与温度完全由 World Builder 文件 `2d_cartesian_subduction_rift.wb` 定义（version 1.0，坐标单位为米，深度自地表向下）：

- **海洋板块**（x ≤ 1150 km）：板块冷却模型温度（脊轴位于 x = 100 km，扩张速度 0.005 m/yr），组分为洋壳（0，10 km 厚）+ 洋岩石圈（1）
- **大陆板块**（x ≥ 1150 km）：线性地温，组分为陆壳（2，30 km 厚）+ 陆岩石圈（3）
- **上地幔**（95–660 km 深）与**下地幔**（660–1160 km 深）：线性绝热地温，组分 4、5
- **俯冲板片**：自 x = 1150 km 处出发，四段折线（0°→45°→45°→0°）下插，板片冷却模型温度，组分结构同海洋板块

## 具体要求

- 2D 笛卡尔盒：X 2000 km × Y 750 km，X 10 个重复单元、Y 3 个（模型只覆盖到 750 km 深，WB 中更深的特征不参与计算）
- 6 个组分场（名称见上），初始温度与初始组分均来自 world builder
- 材料：multicomponent（背景 + 6 组分共 7 个值）：密度 3300（背景）、2900（洋壳）、3300（洋岩石圈）、2700（陆壳）、3200（陆岩石圈）、3300（上地幔）、3400（下地幔）；粘度 1e21、1e22、1e23、1e22、1e23、1e21、1e21 Pa·s；谐波平均；热膨胀系数 0（温度被动）
- 重力：垂直 9.81 m/s²
- 边界条件：四面切向速度（free slip）；温度在顶/底固定（顶 273 K、底 1573 K），侧面绝热
- 非线性：single Advection, single Stokes
- 网格：全局加密 3 级，运行中不细化
- 时间：CFL 1.0，**End time = 1e7 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 后处理：visualization（material properties: density, viscosity）+ velocity statistics；可视化输出间隔 = End time

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 在 case 目录内运行（World Builder 文件为相对路径）
- 输出目录：output-2d_cartesian_subduction_rift

## 验收要点

- 运行成功、正常终止（World Builder 1.0 正常加载，注意文件版本号须为 1.0）
- 初始组分与温度结构正确：洋/陆板块、俯冲板片、上下地幔在正确位置
- 密度差驱动初始流动（RMS velocity > 0，mm/yr–cm/yr 量级）
- 6 个组分质量守恒
