# Benchmark: 2D 俯冲带（Subduction，三层组分 + 自适应细化）

## 任务描述

请生成一个 ASPECT 参数文件，模拟二维俯冲带：右侧边界以板块速度注入洋壳与海洋岩石圈，在俯冲角度约束下形成倾斜的俯冲板片，与上覆板块相互作用。

## 物理背景

模型为 3000×670 km 的二维矩形剖面（Boussinesq 近似）。包含 3 个组分场：

1. **OP** — 上覆板块（大陆）
2. **ML_SP** — 俯冲板块的岩石圈地幔
3. **crust_SP** — 俯冲板块的地壳

俯冲板片的地壳层与上覆板块之间以 35° 角分离（初始组分由多段线性函数的几何关系定义）。右侧边界为流入/流出边界：上部注入俯冲板块（约 6.5 cm/yr 量级），下部为软流圈回流（约 -5 cm/yr），中间以线性过渡衔接。

## 具体要求

- 2D 笛卡尔盒，X 3000 km × Y 670 km，X 方向 4 个重复单元（cell 纵横比 ~1:1）
- 3 个组分场，名称 OP、ML_SP、crust_SP；初始分布由函数定义（参考点坐标：A、B、C、D、E 及多个 z 值构成的俯冲几何）
- 材料：multicomponent，4 种材料（背景、OP、ML_SP、crust_SP），密度 3200/3250/3250/3250 kg/m³，粘度 1e20/1e23/1e23/1e20 Pa·s，粘度用 maximum composition 平均
- 重力：垂直 9.81 m/s²
- 边界条件：
  - 左、底、顶：切向速度（free slip）
  - 右边界：x 方向 prescribed velocity（函数：俯冲板块流入 + 回流 + 线性过渡）
  - 温度：底、顶、右边界固定为 0；初始温度 0（无热效应）
  - 组分：右边界固定为初始组分（流入边界）
- 非线性：single Advection, single Stokes
- 求解器：Stokes 线性容差 1e-6，廉价 Stokes 预处理步数 200
- 网格：全局加密 4 级 + 1 级自适应细化（策略：minimum refinement function + viscosity + composition；细化率 0.9、粗化率 0.1；minimum refinement function 保证板片/俯冲带区域高分辨率、深部地幔粗网格），运行中不细化
- 时间：CFL 1.0，**End time = 5e6 yr**（削减后的模拟时长，保证 ~30s 内跑完）
- 后处理：visualization（material properties、strain rate、error indicator）+ velocity statistics；可视化输出间隔 = End time

## 运行要求

- 单个 MPI 进程，在**本机 MacBook 上 ~30s 内跑完**并正常终止（Termination requested by criterion: end time）
- 输出目录：output-subduction

## 验收要点

- 运行成功、正常终止
- 初始时刻右侧边界驱动俯冲板片运动（RMS velocity > 0，~cm/yr 量级）
- 三个组分质量守恒
- 自适应细化后板片区域网格分辨率高于深部地幔
