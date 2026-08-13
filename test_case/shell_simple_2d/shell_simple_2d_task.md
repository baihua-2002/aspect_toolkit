# Benchmark: 球壳 1/4 对流（2D Shell Convection）

## 任务描述

请生成一个 ASPECT 参数文件，模拟二维球壳四分之一扇区内的地幔对流：初始温度场为球谐六边形扰动，附加剪切加热，在内外半径温差驱动下发展出对流胞。

## 物理背景

模型为二维球坐标系下的 90° 扇区球壳，内半径 3481 km（核幔边界），外半径 6336 km（地表）。初始温度场在绝热背景上叠加球谐六边形扰动，内外边界固定温度（内热外冷），加热模型包含剪切加热，重力由 PREM 数据提供。

## 具体要求

- 几何：spherical shell，内半径 3481 km、外半径 6336 km、开角 90°
- 材料模型：simple，热膨胀系数 4e-5，粘度 1e22 Pa·s，粘度谐波平均
- 重力：ascii data 模型（默认读取 PREM 数据文件 prem.txt）
- 加热：shear heating（剪切加热）
- 初始温度：spherical hexagonal perturbation
- 边界条件：底部零速度，顶部/左侧/右侧切向速度；内外边界固定温度（内 4273 K、外 973 K）
- 网格：全局加密 5 级，无自适应细化，运行中不细化
- 时间：**End time = 4e6 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 求解器：Stokes 用 block GMG
- 后处理：visualization、velocity statistics、temperature statistics、heat flux statistics、depth average；可视化与 depth average 输出间隔 = End time

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 输出目录：output-shell_simple_2d

## 验收要点

- 运行成功、正常终止
- 初始六边形扰动在热浮力驱动下形成对流运动（RMS velocity > 0 且随时间演化）
- 内外边界热通量（heat flux statistics）非零
