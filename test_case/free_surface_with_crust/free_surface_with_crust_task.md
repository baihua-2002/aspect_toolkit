# Benchmark: 自由表面 + 粘性地壳（Free Surface with Crust）

## 任务描述

请生成一个 ASPECT 参数文件，模拟带自由表面的热异常上升：域中心放置一个半径 25 km 的高温异常体（ΔT = 200 K），在热浮力作用下上涌，驱动自由表面产生地形起伏。模型的关键在于使用**自定义插件材料模型 "simpler with crust"**：地壳（浅层）与地幔（深层）具有不同粘度，粘度跃变面位于 170 km 深度。

## 物理背景

本模型是 free_surface cookbook 的扩展（ASPECT cookbook: free_surface_with_crust）。核心差异：通过外部共享库加载自定义材料模型，该模型在 "simpler" 材料模型基础上增加了一个粘性地壳层——上部粘度 1e23 Pa·s（地壳/岩石圈），下部粘度 1e20 Pa·s（软流圈），跃变深度 170 km。粘性地壳抑制了热异常引起的表面地形幅度。

## 具体要求

- **插件**：需先编译 `plugin/` 目录下的插件源码（`simpler_with_crust.cc`），`Additional shared libraries` 指向编译产物（本机已预编译至 `plugin/build_mac/libsimpler_with_crust.release.so`）
- 2D 笛卡尔盒：X 500 km × Y 200 km，X 方向 5 个重复单元、Y 方向 2 个
- 材料模型：simpler with crust（密度 3300 kg/m³、比热 1250、热导 1.0、热膨胀 4e-5、下部粘度 1e20、上部粘度 1e23、跃变高度 170 km）
- 初始温度：函数——以 (250 km, 100 km) 为圆心、半径 25 km 的球内 200 K，其余 0 K
- 边界条件：左/右/底切向速度；四面固定温度 0 K；顶面自由表面（free surface，稳定参数 θ = 0.5）
- 重力：垂直向下，10 m/s²（与 cookbook 一致）
- 网格：全局加密 4 级，无自适应细化，运行中不细化
- 时间：CFL 1.0，首步 1e3 yr、步长最大增长 30 倍/步，**End time = 4e5 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 后处理：visualization（material properties、depth）、velocity statistics、topography；可视化输出间隔 = End time

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 在 case 目录内运行（插件相对路径）
- 输出目录：output-free_surface_with_crust

## 验收要点

- 运行成功、正常终止（插件正确加载，"simpler with crust" 材料模型生效）
- 热异常上涌（RMS velocity > 0），顶面自由表面产生地形（topography 后处理输出非零/可分辨）
- 材料属性输出中密度与粘度随深度分布符合两层结构
