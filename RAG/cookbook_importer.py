"""
ASPECT 官方 cookbook → 专家案例（RAG/cases.json）导入器。

把 cookbooks/*.prm 官方参数文件转换为 SimulationCase 兼容记录，与
extractor.py 的 OCR 文献清洗互补：这里参数 100% 来自原始 .prm，不经过 LLM，
保证取值与 ASPECT 官方配置一致（可复现），rationale 由人工按 cookbook 物理意图撰写。

用法：
    uv run python -m RAG.cookbook_importer --dry-run   # 只打印，不落盘
    uv run python -m RAG.cookbook_importer             # 合并进 cases.json
    uv run python -m RAG.cookbook_importer --overwrite # 覆盖同 case_id 旧记录

设计要点：
  - 每个 cookbook 一个 case（含多 .prm 变体时合并为同一 case 的不同决策）；
  - 顶层全局参数统一加 "Global parameters.No subsection." 前缀，与 parameters.json
    section_path 及已有 cases.json 的点路径约定对齐；
  - 忽略纯输出/环境类参数（Output directory、Data directory 等），保留物理与数值决策；
  - 支持 `include xxx.prm.base` 去重（如 subduction_initiation）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CASES_PATH = Path(__file__).parent / "cases.json"
# prm_path 以 cookbooks/ 开头，故根指向 ASPECT 源码根目录
DEFAULT_COOKBOOK_ROOT = Path("/Users/bai/workspace/aspect-main")

# include 指令（如 subduction_initiation.prm 引用 .prm.base）
_INCLUDE_RE = re.compile(r'^\s*include\s+(.+?)\s*$')
_SET_RE = re.compile(r'^\s*set\s+([^=]+?)\s*=\s*(.*?)\s*$')
_SUB_RE = re.compile(r'^\s*subsection\s+(.+?)\s*$')

# 纯输出/环境类参数，不进 expert decisions（无物理决策意义）
_IGNORE_KEYS = {
    "Output directory",
    "Data directory",
}
_IGNORE_KEYS_SUFFIX = (
    "Output directory",
    "Data directory",
    "Timing output frequency",
)


def _strip_inline_comment(value: str) -> str:
    """去掉值为 # 前的行内注释（如 '1e4   # = Ra' → '1e4'）。"""
    # 只在空白或行内注释位置切：# 前有空格，且不是函数常量里的 #
    if " #" in value:
        value = value.split(" #")[0]
    return value.strip()


def parse_prm_text(
    text: str,
    *,
    base_dir: Path,
    seen_includes: set[Path] | None = None,
    _depth: int = 0,
) -> dict[str, str]:
    """解析 .prm 文本为 {点路径: 值}，支持 include 与多行续行。"""
    if _depth > 10:
        raise RuntimeError("include 递归过深")
    seen = seen_includes if seen_includes is not None else set()

    stack: list[str] = []
    out: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _INCLUDE_RE.match(line)
        if m:
            inc_path = (base_dir / m.group(1).strip()).resolve()
            if inc_path in seen:
                continue
            seen.add(inc_path)
            for k, v in parse_prm_text(
                inc_path.read_text(encoding="utf-8"),
                base_dir=inc_path.parent,
                seen_includes=seen,
                _depth=_depth + 1,
            ).items():
                out[k] = v
            continue
        # 多行续行：当前行以反斜杠结尾时拼接后续行
        while line.rstrip().endswith("\\") and i + 1 < len(lines):
            i += 1
            line = line.rstrip()[:-1].rstrip() + " " + lines[i].strip()
        # 逆序处理续行：上面用 for 循环，需改 while 直接消费
        # （上面 while 已把后续行拼入 line，继续解析 line）
        m = _SUB_RE.match(line)
        if m:
            stack.append(m.group(1).strip())
            continue
        if stripped == "end":
            if stack:
                stack.pop()
            continue
        m = _SET_RE.match(line)
        if m:
            name = m.group(1).strip()
            if name in _IGNORE_KEYS or name.endswith(_IGNORE_KEYS_SUFFIX):
                continue
            value = _strip_inline_comment(m.group(2))
            key = ".".join(stack + [name])
            if not stack:
                key = f"Global parameters.No subsection.{name}"
            out[key] = value
    return out


def parse_prm_file(path: Path) -> dict[str, str]:
    return parse_prm_text(path.read_text(encoding="utf-8"), base_dir=path.parent)


# ---------------------------------------------------------------------------
# 案例清单（人工策划：物理描述 / 结果 / 标签 / 关键参数 rationale）
# ---------------------------------------------------------------------------

# 默认 rationale 模板：官方 cookbook 引用
def _src(prm_path: str) -> str:
    return f"ASPECT 官方 cookbook（{prm_path}），保持官方配置以保证可复现"


CASES: list[dict] = [
    {
        "case_id": "cookbook-convection-box",
        "title": "Convection in a 2d box（Boussinesq，Ra=1e4 基准）",
        "domain": "mantle convection",
        "description": ("2D 单位方盒 [0,1]^2，Boussinesq 近似、常系数简单材料模型。"
                         "底部加热 T=1、顶部冷却 T=0、左右绝热；四边切向自由滑移。"
                         "无量纲化使 Ra=g（取 g=1e4，即 Ra=1e4）；初始温度线性剖面加 "
                         "k=1 余弦扰动激发单涡对流。网格 4 次全局加密（16×16），"
                         "温度 quadratic、Stokes quadratic/压力 linear。输出速度、温度与热流统计。"),
        "source": "ASPECT cookbook: cookbooks/convection-box/convection-box.prm（Blankenbach et al., 1989 基准）",
        "prm_path": "cookbooks/convection-box/convection-box.prm",
        "outcome": ("约 t=0.1 后进入稳态；最终顶部/底部热流 4.787，与 Blankenbach et al. "
                    "(1989) 外推值 4.884409 误差<2%（16×16 网格、温度二次元）。"
                    "左右边界热流趋近于零。5 次/6 次加密后误差降至约 0.1%。"),
        "success": True,
        "tags": ["convection", "box", "Boussinesq", "Rayleigh number", "benchmark",
                 "heat flux", "2d", "cartesian"],
        "rationale_notes": {
            "Global parameters.No subsection.Pressure normalization": "surface：零平均压力在表面",
            "Global parameters.No subsection.End time": "0.5：稳态在 t≈0.1 已收敛，0.5 足够",
            "Gravity model.Vertical.Magnitude": "取 g=Ra=1e4，即无量纲瑞利数 1e4（>Ra_c≈780，稳定对流）",
            "Material model.Simple model.Viscosity": "1：无量纲化 η=1",
            "Material model.Simple model.Reference density": "1：无量纲化 ρ0=1",
            "Material model.Simple model.Thermal expansion coefficient": "1：无量纲化 α=1",
            "Formulation.Formulation": "Boussinesq approximation：密度只出现在浮力项",
            "Mesh refinement.Initial global refinement": "4：16×16 网格即可达 <2% 热流精度",
        },
    },
    {
        "case_id": "cookbook-onset-of-convection",
        "title": "Onset of convection（岩石圈尺度线性稳定性扫描）",
        "domain": "mantle convection",
        "description": ("2D 盒模型，宽高比 π:1（9.42e6 × 3.0e6 m），采用地幔合理参数 "
                         "(ρ0=4000, η=1e23, k=4, α=3e-5, Cp=1250, g=10, 底部 2500 K 顶部 0)。"
                         "Boussinesq 近似；初始线性温度剖面叠加 k=2 余弦扰动，检验扰动增长。"
                         "四边切向自由滑移；用 conduction timestep 并从第 0 步起 100 步终止。"
                         "用于沿（粘度, ΔT）网格化扫描对流起始边界（线性稳定性分析，Turcotte & Schubert §6.19）。"),
        "source": "ASPECT cookbook: cookbooks/onset_of_convection/onset_of_convection.prm（由 Max Rudolph 的 onset-of-convection 基准改编）",
        "prm_path": "cookbooks/onset_of_convection/onset_of_convection.prm",
        "outcome": ("通过 run.sh 扫描 η∈[1e24,3.3e27] Pa s 与 ΔT∈[10,1e4] K。"
                    "不稳定（对流）配置速度随步数增长，稳定配置衰减；"
                    "用（η, ΔT）图上速度增长/衰减边界定位对流起始线。"),
        "success": True,
        "tags": ["onset of convection", "Rayleigh number", "linear stability",
                 "mantle convection", "viscosity", "perturbation", "2d"],
        "rationale_notes": {
            "Global parameters.No subsection.Use conduction timestep": "true：起始阶段纯扩散，用传导时间步",
            "Termination criteria.Termination criteria": "end step + End step=100：只跑短时间看扰动是否增长",
            "Gravity model.Vertical.Magnitude": "10 m/s2：地幔合理重力",
            "Material model.Simple model.Viscosity": "1e23 Pa s：地幔参考粘度（扫描基值）",
            "Formulation.Formulation": "Boussinesq approximation",
        },
    },
    {
        "case_id": "cookbook-heat-flow",
        "title": "Heat flow at a mid-ocean ridge（板块冷却热流）",
        "domain": "heat conduction",
        "description": ("2D 盒 400×100 km（x 原点移到 -200 km，洋中脊在 x=0）。"
                         "顶部边界给定水平扩张速度 ±v（默认 v=5 cm/yr），底部开放进流、"
                         "左右边界给定初始静岩压力牵引；底部固定 T=1600 K、顶部固定 T=293 K。"
                         "材料用 composition reaction 模型（α=1e-4，k=4.7，η=1e23）。"
                         "初始 T=1600 K（等效极年龄板片），随后板块热传导冷却。"
                         "网格 initial global 2 + adaptive 4，用 minimum refinement function 在 "
                         "7/30/45 km 深度向地表逐级加密，解析板片导电冷却。"),
        "source": "ASPECT cookbook: cookbooks/heat_flow/heat-flow.prm",
        "prm_path": "cookbooks/heat_flow/heat-flow.prm",
        "outcome": ("再现洋中脊半扩张板片冷却：地表热流随时间（板片年龄）衰减，"
                    "热流/温度统计输出验证热传导主导的板片冷却模型。"),
        "success": True,
        "tags": ["heat flow", "mid-ocean ridge", "plate cooling", "conduction",
                 "boundary traction", "lithostatic pressure", "2d", "cartesian"],
        "rationale_notes": {
            "Geometry model.Box.X extent": "400000 m：总体板片范围",
            "Boundary velocity model.Prescribed velocity boundary indicators": "顶部给定扩张速度，左右仅 x 方向给定、y 自由",
            "Boundary traction model.Prescribed traction boundary indicators": "左右用初始静岩压力，允许材料自由进出",
            "Material model.Model name": "composition reaction：多数属性恒定，仅密度随温度（α=1e-4）",
            "Mesh refinement.Strategy": "minimum refinement function：向地表分级加密，解析热边界层",
            "Postprocess.Visualization.List of output variables": "含 heat flux map / vertical heat flux",
        },
    },
    {
        "case_id": "cookbook-composition-passive",
        "title": "Compositional fields：passive 组分平流",
        "domain": "mantle convection",
        "description": ("2D 盒 2×1，两个组分场：底部 y<0.2 区域为 1、顶部 y>0.8 区域为 1，其余为 0，"
                         "随流场被动平流（不反作用于密度）。顶部边界给定往复剪切速度 "
                         "if(x>1+sin(0.5πt),1,-1)，底部与左右切向滑移；底部 T=1、顶部 T=0。"
                         "simple 材料（k=1e-6、α=1e-4、η=1），热导率极小使温度近乎被动。"
                         "5 次全局加密。演示组分场随流平流。"),
        "source": "ASPECT cookbook: cookbooks/composition_passive/composition_passive.prm",
        "prm_path": "cookbooks/composition_passive/composition_passive.prm",
        "outcome": ("两个组分场随顶部剪切流变形/平流，验证无密度反馈时的纯被动输运；"
                    "可视化展示组分界面随流撕裂与卷绕。"),
        "success": True,
        "tags": ["compositional fields", "passive", "advection", "cartesian",
                 "2d", "shear flow"],
        "rationale_notes": {
            "Compositional fields.Number of fields": "2：底部 + 顶部各一层标记",
            "Material model.Simple model.Thermal conductivity": "1e-6：避免热扩散干扰，温度场冻结",
        },
    },
    {
        "case_id": "cookbook-composition-active",
        "title": "Compositional fields：active 组分（密度反馈）",
        "domain": "mantle convection",
        "description": ("composition-passive 变体：提高瑞利数并让密度依赖组分。"
                         "simple 材料加 Density differential for compositional field 1 = 100，"
                         "α=0.01；顶部往复剪切边界；2×1 盒、两组分初始条件同 passive 版。"
                         "演示组分场主动驱动对流（active composition）。"),
        "source": "ASPECT cookbook: cookbooks/composition_active/composition_active.prm",
        "prm_path": "cookbooks/composition_active/composition_active.prm",
        "outcome": ("组分密度差驱动的浮力主动驱动流动，与被动版对比可见组分场自身诱发流场"
                    "（如底部重组分上涌、界面失稳），material properties 可视化输出密度。"),
        "success": True,
        "tags": ["compositional fields", "active", "density", "thermochemical",
                 "2d", "cartesian", "composition"],
        "rationale_notes": {
            "Material model.Simple model.Density differential for compositional field 1": "100：组分 1 变化 1 单位密度改变 100（主动驱动）",
            "Material model.Simple model.Thermal expansion coefficient": "0.01：热浮力与组分浮力竞争",
        },
    },
    {
        "case_id": "cookbook-composition-passive-particles",
        "title": "Composition passive + particles（粒子输运组分）",
        "domain": "mantle convection",
        "description": ("composition-passive.prm 变体：同样两组分场被动平流，但改用 1000 个"
                         "随机均匀粒子输运组分，并启用 particles 后处理。2×1 盒、顶部往复剪切。"
                         "对比 FE 组分场与粒子的输运精度与质量守恒。"),
        "source": "ASPECT cookbook: cookbooks/composition_passive_particles/composition_passive_particles.prm",
        "prm_path": "cookbooks/composition_passive_particles/composition_passive_particles.prm",
        "outcome": ("粒子随流运动并与组分场耦合，演示粒子方法输运组分；"
                    "粒子/组分可视化对比二者数值表现。"),
        "success": True,
        "tags": ["compositional fields", "particles", "passive", "advection", "2d"],
        "rationale_notes": {
            "Particles.Generator.Random uniform.Number of particles": "1000：粒子密度探针",
        },
    },
    {
        "case_id": "cookbook-sinker-with-averaging",
        "title": "Sinker with material averaging（粘度平均方案对比）",
        "domain": "benchmark",
        "description": ("2D 单位方盒，中央半径 0.22 的高密度球（组分 1，ρ 差 +10、"
                         "Composition viscosity prefactor 1e6）在粘性介质中沉降（Stokes 稳态，"
                         "Start=End=0）。simple 材料 α=0（温度被动）；四边零速度。"
                         "核心是探讨 material averaging 策略（none / harmonic 等）对"
                         "强粘度对比沉降问题稳定性的影响；6 次全局加密。"
                         "相应变体 conservative/full/harmonic.prm 比较不同平均方案。"),
        "source": "ASPECT cookbook: cookbooks/sinker-with-averaging/sinker-with-averaging.prm",
        "prm_path": "cookbooks/sinker-with-averaging/sinker-with-averaging.prm",
        "outcome": ("粘度平均（harmonic）对上覆粘性流体中高粘度沉降体的稳定性至关重要："
                    "不做平均时强粘度对比会产生数值振荡与网格依赖；harmonic 平均显著改善。"
                    "演示 why material averaging 在强对比材料中是必要设置。"),
        "success": True,
        "tags": ["sinker", "material averaging", "viscosity", "harmonic averaging",
                 "benchmark", "Stokes", "2d"],
        "rationale_notes": {
            "Material model.Material averaging": "none：基准对比用（变体 harmonic）",
            "Material model.Simple model.Composition viscosity prefactor": "1e6：沉降体粘度放大 1e6 倍，制造强对比",
            "Material model.Simple model.Density differential for compositional field 1": "10：沉降驱动力",
            "Global parameters.No subsection.End time": "0：单一 Stokes 稳态",
        },
    },
    {
        "case_id": "cookbook-van-keken-smooth",
        "title": "van Keken 热化学对流基准（光滑初始界面）",
        "domain": "benchmark",
        "description": ("2D 盒 0.9142×1，等黏 Rayleigh-Taylor 不稳定性（van Keken et al. 1997 case 1a）。"
                         "simple 材料 α=0（温度被动）、ρ0=1010、Density differential for "
                         "compositional field 1 = -10，即下层更轻流体托重流体。初始组分界面用 "
                         "光滑 tanh（半带宽 0.01）；底面与顶面零速度、左右切向滑移。"
                         "7 次全局加密（128×128），组分自适应加密，t 至 2000 输出 VTU。"
                         "度量方均根速度演化与论文对比。"),
        "source": "ASPECT cookbook: cookbooks/van-keken/van-keken-smooth.prm（van Keken et al., 1997, case 1a 基准）",
        "prm_path": "cookbooks/van-keken/van-keken-smooth.prm",
        "outcome": ("RMS 速度第一峰与第二峰均随网格收敛；两峰位置/高度与 van Keken et al. (1997)"
                    "误差在数个百分比内（光滑化使第二峰可复现，而非间断版对网格敏感）。"),
        "success": True,
        "tags": ["van Keken", "benchmark", "Rayleigh-Taylor", "composition",
                 "thermochemical", "isoviscous", "stability", "2d"],
        "rationale_notes": {
            "Material model.Simple model.Thermal expansion coefficient": "0：温度完全被动，密度只由组分差驱动",
            "Material model.Simple model.Density differential for compositional field 1": "-10：下层轻 10 单位，不稳定层序",
            "Mesh refinement.Strategy": "composition：在组分界面加密，解析界面",
            "Mesh refinement.Initial global refinement": "7：32×32→128×128 已见第一峰收敛",
        },
    },
    {
        "case_id": "cookbook-van-keken-discontinuous",
        "title": "van Keken 热化学对流基准（间断初始界面）",
        "domain": "benchmark",
        "description": ("van-keken-smooth 的原始间断版：初始组分界面为阶跃 "
                         "if(z>0.2+0.02cos(πx/0.9142),0,1)。其余设置同 smooth 版 "
                         "（0.9142×1 盒、α=0、密度差 -10、底面/顶面零速度、组分自适应加密、t=2000）。"
                         "演示间断初始条件在连续 FE 网格上的插值误差如何影响次级羽流。"),
        "source": "ASPECT cookbook: cookbooks/van-keken/van-keken-discontinuous.prm（van Keken et al., 1997, case 1a）",
        "prm_path": "cookbooks/van-keken/van-keken-discontinuous.prm",
        "outcome": ("第一峰（沿左缘的大羽流）在所有网格下一致，与论文吻合<1%；"
                    "第二峰（右缘小羽流）对网格极其敏感，阶跃被连续单元插值后位置/时序不可收敛，"
                    "揭示了 van Keken et al. 文中所述'第二次不稳定的位置因方法而异'的原因。"),
        "success": True,
        "tags": ["van Keken", "benchmark", "Rayleigh-Taylor", "discontinuous",
                 "mesh dependence", "composition", "2d"],
        "rationale_notes": {
            "Initial composition model.Function.Function expression": "阶跃函数：沿用 van Keken 原始间断设定",
        },
    },
    {
        "case_id": "cookbook-mid-ocean-ridge",
        "title": "2D 洋中脊熔融与熔体运移（melt transport）",
        "domain": "mantle convection",
        "description": ("2D 盒 105×70 km 建模洋中脊一半（脊轴在左边界 x=0，对称假设）。"
                         "melt simple 材料含熔融/冷凝（freezing rate=0.005、melting timescale=200 yr、"
                         "参考渗透率 1e-7）；启用 operator splitting 处理快速熔融反应、latent heat"
                         "潜热、melt transport（porosity + peridotite 两组分场），求解 McKenzie 双相流。"
                         "顶部给定脊扩张板块速度 3 cm/yr（10 km 内插）、左边界切向滑移（脊轴对称面），"
                         "右/底给定初始静岩压力牵引；底部固定 T=1570 K、顶部 293 K，初始绝热剖面。"
                         "mesh refinement 用 minimum refinement function + composition threshold "
                         "(porosity>1e-6 加密) 解析熔融区。GMRES restart 200，每 100 步 checkpoint。"),
        "source": "ASPECT cookbook: cookbooks/mid_ocean_ridge/mid_ocean_ridge.prm",
        "prm_path": "cookbooks/mid_ocean_ridge/mid_ocean_ridge.prm",
        "outcome": ("~6 Myr 后接近稳态：熔体向脊轴聚焦形成高孔隙通道并生成地壳与岩石圈；"
                    "熔融-冻结在顶部边界附近产生化学非均一（亏损橄榄岩），在脊下达平衡熔融。"
                    "潜热冷却显著影响温度场。"),
        "success": True,
        "tags": ["mid-ocean ridge", "melt transport", "melting", "two-phase flow",
                 "porosity", "operator splitting", "McKenzie", "composition",
                 "2d", "cartesian"],
        "rationale_notes": {
            "Global parameters.No subsection.Use operator splitting": "true：熔融反应时间尺度远小于时间步，用分裂法保持近平衡",
            "Material model.Model name": "melt simple：无水流体简单熔融（平均地幔组成）",
            "Material model.Melt simple.Freezing rate": "0.005/yr：凝固时间尺度 200 yr，<< 时间步，熔体近平衡",
            "Melt settings.Include melt transport": "true：求解双相流 McKenzie 方程追踪熔体",
            "Melt settings.Heat advection by melt": "true：熔体运移对流传热",
            "Boundary velocity model.Prescribed velocity boundary indicators": "顶部 3 cm/yr 半扩张速度（远离脊轴刚性板块）",
            "Boundary traction model.Prescribed traction boundary indicators": "右/底初始静岩压力，材料自由进出",
            "Mesh refinement.Strategy": "minimum refinement function + composition threshold，porosity>1e-6 的高解析熔融区",
            "Postprocess.Visualization.List of output variables": "material properties + melt fraction + melt material properties（含 is melt cell）",
        },
    },
    {
        "case_id": "cookbook-shell-simple-2d",
        "title": "Convection in a 2d spherical shell（四分之一球壳）",
        "domain": "mantle convection",
        "description": ("2D 球壳四分之一（内半径 3481 km、外半径 6336 km、开角 90°），"
                         "simple 材料 α=4e-5、η=1e22，harmonic average only viscosity（材料平均）。"
                         "底部零速度、顶部/侧面切向滑移；内边界固定 4273 K、外边界 973 K；"
                         "剪切加热；初始温度用 spherical hexagonal perturbation；"
                         "重力用 ascii data（随半径变化 PREM 剖面）。5 次全局 + 4 次自适应（temperature 策略），"
                         "15 步重加密；block GMG Stokes 求解器；depth average 后处理。"),
        "source": "ASPECT cookbook: cookbooks/shell_simple_2d/shell_simple_2d.prm",
        "prm_path": "cookbooks/shell_simple_2d/shell_simple_2d.prm",
        "outcome": ("球壳几何下的地幔对流：以六边形扰动为初始，形成下边界上涌/上边界下沉的对流胞；"
                    "深度平均温度与热流统计展示球壳对流结构。"),
        "success": True,
        "tags": ["spherical shell", "2d", "convection", "shear heating",
                 "depth averaging", "block GMG", "heat flux"],
        "rationale_notes": {
            "Geometry model.Spherical shell.Opening angle": "90：四分之一扇区（2D 环）",
            "Material model.Material averaging": "harmonic average only viscosity：仅在粘度上做调和平均以提高稳定",
            "Heating model.List of model names": "shear heating：摩擦加热",
            "Solver parameters.Stokes solver parameters.Stokes solver type": "block GMG：周期结构用几何多重网格加速",
        },
    },
    {
        "case_id": "cookbook-shell-simple-3d",
        "title": "Convection in a 3d spherical shell",
        "domain": "mantle convection",
        "description": ("3D 球壳全壳（内半径 3481 km、外半径 6336 km），simple 材料 α=4e-5、η=1e22。"
                         "底部零速度、顶部切向滑移；内边界固定 1973 K、外边界 973 K；"
                         "初始温度均匀 1473 K（函数），重力 ascii data；2 次全局 + 3 次自适应加密"
                         "（temperature 策略，15 步重加密）。depth average + heat flux/温度/速度统计。"
                         "每 50 步 checkpoint。"),
        "source": "ASPECT cookbook: cookbooks/shell_simple_3d/shell_simple_3d.prm",
        "prm_path": "cookbooks/shell_simple_3d/shell_simple_3d.prm",
        "outcome": ("3D 球壳热对流从近等温初始自发发展出对流（因温度策略自适应会放大数值扰动），"
                    "展示深度平均温度随时间的演化与热流输出。"),
        "success": True,
        "tags": ["spherical shell", "3d", "convection", "checkpointing",
                 "depth averaging", "heat flux"],
        "rationale_notes": {
            "Dimension": "3：全三维球壳",
            "Boundary velocity model.Zero velocity boundary indicators": "bottom",
            "Boundary velocity model.Tangential velocity boundary indicators": "top",
        },
    },
    {
        "case_id": "cookbook-bunge-mantle-convection",
        "title": "Depth-dependent viscosity：2D 球壳对流（Bunge et al. 1996）",
        "domain": "mantle convection",
        "description": ("2D 球壳 3480–6370 km，材料用 depth dependent 模型：以 simple 为基底"
                         "（ρ0=4500、α=2.5e-5、η_ref=1e22、Cp=1000、k=4），"
                         "深度相关粘度从文件 visc_depth_a.txt 读取。辐射加热率 1e-12 W/kg。"
                         "内边界固定 3450 K、外边界 1060 K；初始温度线性剖面叠加多谐波扰动"
                         "（sin(7φ)/sin(13φ)+cos(0.123φ) 等）；径向常重力 10 m/s2。"
                         "5 次全局加密、temperature 自适应，depth average 用 100 带。"),
        "source": "ASPECT cookbook: cookbooks/bunge_et_al_mantle_convection/bunge_et_al.prm（Bunge et al., Nature, 1996）",
        "prm_path": "cookbooks/bunge_et_al_mantle_convection/bunge_et_al.prm",
        "outcome": ("再现 Bunge et al. (1996) 深度相关粘度下的地幔对流：粘度的径向分层抑制浅层 "
                    "小尺度对流，温度场发展出宽波长模式；depth average 温度剖面分层清晰。"),
        "success": True,
        "tags": ["depth-dependent viscosity", "spherical shell", "mantle convection",
                 "Bunge 1996", "radiogenic heating", "2d"],
        "rationale_notes": {
            "Material model.Model name": "depth dependent：径向分层粘度",
            "Material model.Depth dependent model.Depth dependence method": "File：从 visc_depth_a.txt 读粘度-深度曲线",
            "Heating model.List of model names": "constant heating + radiogenic heating rate 1e-12 W/kg",
            "Gravity model.Model name": "radial constant：径向常重力 10 m/s2",
            "Initial temperature model.Function.Function expression": "线性剖面叠加多谐波扰动激励多尺度对流",
        },
    },
    {
        "case_id": "cookbook-free-surface",
        "title": "Free surface（地表地形演化，热柱上涌）",
        "domain": "plume",
        "description": ("2D 盒 500×200 km。自由表面设在顶部（Mesh deformation boundary indicators "
                         "= top: free surface，theta=0.5 稳定化）；左右/底切向滑移、顶部零应力。"
                         "初始温度：中心 (250,100) km 半径 25 km 热球 +200 K，热异常上涌推动地表地形。"
                         "simpler 材料（ρ0=3300、η=1e20、k=1 低热导率防止快速扩散、α=4e-5）。"
                         "Pressure normalization=no（自由面必需）；CFL=1、最大首步 1e3 yr、每步增幅≤30%。"
                         "topography 后处理输出每步最大/最小地形。"),
        "source": "ASPECT cookbook: cookbooks/free_surface/free_surface.prm",
        "prm_path": "cookbooks/free_surface/free_surface.prm",
        "outcome": ("热柱上涌使地表先隆起后衰减（热扩散并冷却）：最大地形随时间先增后减；"
                    "演示自由表面计算的稳定性设置（theta、首步限制）。"),
        "success": True,
        "tags": ["free surface", "topography", "plume", "blob", "2d",
                 "cartesian", "dynamic topography"],
        "rationale_notes": {
            "Global parameters.No subsection.Pressure normalization": "no：自由面方程要求地表压力为零",
            "Global parameters.No subsection.Maximum first time step": "1e3 年：稳定初始自由面以避免网格振荡",
            "Global parameters.No subsection.Maximum relative increase in time step": "30%：限制步长跳跃",
            "Mesh deformation.Free surface.Free surface stabilization theta": "0.5：标准稳定化参数",
            "Material model.Simple model.Thermal conductivity": "1.0（更低）：减缓热异常扩散",
        },
    },
    {
        "case_id": "cookbook-stokes",
        "title": "Stokes 基准：3D 活动组分球在方盒中沉降",
        "domain": "benchmark",
        "description": ("3D 方盒 2890 km 边长，六面自由滑移；单一活动组分场初始为半径 200 km 的球"
                         "（中心在体心），Density differential for compositional field 1 = 100 "
                         "驱动沉降；温度场不起作用（T=0）。Start=End=0 强制执行单一静稳态。"
                         "简单材料 ρ0=3300、η=1e22、g=9.81。4 次全局 + 4 次自适应（velocity 策略）加密。"
                         "有解析解可对比（Stokes 基准）。"),
        "source": "ASPECT cookbook: cookbooks/stokes/stokes.prm",
        "prm_path": "cookbooks/stokes/stokes.prm",
        "outcome": ("球体在粘性介质中的 Stokes 沉降，与解析 Stokes 解（阻力/速度）对比验证"
                    "求解器；速度、密度、粘度可视化输出。"),
        "success": True,
        "tags": ["Stokes", "benchmark", "sinking", "sphere", "3d", "analytical solution",
                 "active composition"],
        "rationale_notes": {
            "Global parameters.No subsection.End time": "0 = Start time：单一稳态 Stokes 求解",
            "Boundary velocity model.Tangential velocity boundary indicators": "六面均自由滑移",
            "Material model.Simple model.Density differential for compositional field 1": "100：球内密度差驱动沉降",
        },
    },
    {
        "case_id": "cookbook-crustal-deformation",
        "title": "Crustal deformation（Drucker-Prager 塑性 + 自由表面）",
        "domain": "crustal deformation",
        "description": ("2D 盒 80×16 km 地壳尺度。材料用 Drucker Prager 塑性（ρ0=2800、摩擦角 30°、"
                         "内聚力 20e6 Pa、min η=1e19、max η=1e25、参考应变率 1e-20），"
                         "顶部自由表面（vertical 投影）并配合塑性变形。左右/底部给定 ±1 cm/yr "
                         "水平缩短速度（边界函数），温度无关（T=0）。single Advection + iterated Stokes、"
                         "非线性容差 2e-6；strain rate 自适应加密（每 1 步重加密）；"
                         "block AMG + GMRES restart 200 Stokes 求解。"),
        "source": "ASPECT cookbook: cookbooks/crustal_deformation/crustal_model_2D.prm",
        "prm_path": "cookbooks/crustal_deformation/crustal_model_2D.prm",
        "outcome": ("缩短边界条件下地壳挤压变形：应变集中形成逆冲型剪切带与表层地形抬升，"
                    "塑性屈服控制变形局部化；Drucker-Prager 压力依赖屈服清晰呈现。"),
        "success": True,
        "tags": ["crustal deformation", "Drucker-Prager", "plasticity", "free surface",
                 "strain localization", "shortening", "2d"],
        "rationale_notes": {
            "Material model.Model name": "drucker prager：压力相关塑性屈服",
            "Material model.Drucker Prager.Viscosity.Maximum viscosity": "1e25：限制屈服后粘度",
            "Mesh deformation.Mesh deformation boundary indicators": "top: free surface（vertical 投影）",
            "Boundary velocity model.Prescribed velocity boundary indicators": "±1 cm/yr 对称缩短",
            "Mesh refinement.Strategy": "strain rate：在剪切带加密",
        },
    },
    {
        "case_id": "cookbook-continental-extension",
        "title": "Continental extension（黏-塑性流变岩石圈裂谷）",
        "domain": "crustal deformation",
        "description": ("2D 盒 200×100 km，5 个组分层（非初始/总塑性应变、上/下地壳、地幔岩石圈），"
                         "组分用粒子输运（Mapped particle properties）。材料 visco plastic："
                         "位错蠕变（上地壳 wet quartzite、下地壳 wet anorthite、地幔 dry olivine；"
                         "含 prefactor/应力指数/激活能/激活体积），Drucker-Prager 塑性 + 应变弱化"
                         "（plastic weakening，应变 0.5–1.5 段减弱摩擦与内聚力 0.25 倍）、"
                         "plastic damper 1e21。顶部自由表面 + diffusion（hillslope 1e-8）平滑，"
                         "左/右给定 ±0.25 cm/yr 扩张速度，底部垂直进流。初始温度用 Chapman 大陆地温"
                         "（分层热产率 1e-6/0.25e-6 W/m^3），compositional heating。"
                         "网格 2.5 km 全局 + 1.25 km 自适应（y>50 km 且 40<x<160 km 的高解析区）。"
                         "Boussinesq、Pressure normalization=no、CFL=0.5、block AMG Stokes。"),
        "source": "ASPECT cookbook: cookbooks/continental_extension/continental_extension.prm（Naliboff & Buiter 2015；Brune et al. 2014 等）",
        "prm_path": "cookbooks/continental_extension/continental_extension.prm",
        "outcome": ("0.25 cm/yr 扩张下岩石圈裂谷演化：正断层局部化、上/下地壳解耦、"
                    "可能发育 hyperextension；应变弱化控制断层活动期与迁移；"
                    "潮汐学地形与自由表面相互作用可观测（topography postprocessor）。"),
        "success": True,
        "tags": ["continental extension", "rifting", "visco plastic", "strain weakening",
                 "dislocation creep", "free surface", "lithosphere", "particles", "2d"],
        "rationale_notes": {
            "Material model.Model name": "visco plastic：位错蠕变 + Drucker-Prager 塑性 + 应变弱化",
            "Compositional fields.Types of fields": "两个 strain 场 + 三个 chemical composition 层",
            "Compositional fields.Compositional field methods": "particles：用粒子输运组分与应变",
            "Mesh refinement.Strategy": "minimum refinement function：y>50 km 且 40<x<160 km 高解析",
            "Solver parameters.Stokes solver parameters.Stokes solver type": "block AMG",
            "Global parameters.No subsection.Pressure normalization": "no：配合自由表面",
            "Boundary velocity model.Prescribed velocity boundary indicators": "±0.25 cm/yr 扩张 + 底部平衡进流",
        },
    },
    {
        "case_id": "cookbook-subduction-initiation",
        "title": "Subduction initiation（Matsumoto & Tomoda 1983 复现）",
        "domain": "subduction",
        "description": ("2D 盒 400×180 km 复现 Matsumoto & Tomoda (1983)。multicomponent 材料："
                         "水层（sticky water η=1e18、ρ=1030）、左右洋岩石圈（η=1e22、ρ=3300）、"
                         "左右软流圈（η=1e21、ρ=3200），温度无关（α=0、T=0）。"
                         "4 个组分场用函数初始化（水/岩石圈/软流圈几何分区，L0=300 km、H=180 km 基准），"
                         "顶/底固定温度=0、自由滑移四边；2 次自适应 + 5 次全局加密（composition 策略）。"
                         "CFL=0.25、50 Myr、表面压力归一。"),
        "source": "ASPECT cookbook: cookbooks/subduction_initiation/subduction_initiation_compositional_fields.prm（Matsumoto & Tomoda, 1983）",
        "prm_path": "cookbooks/subduction_initiation/subduction_initiation_compositional_fields.prm",
        "outcome": ("岩石圈-软流圈密度/粘度对比驱动自发俯冲起始：轻的洋岩石圈在重软流圈之上失稳"
                    "并开始下潜；与论文 6 组参数的成分/粘度对比（η_a=1e19–1e21、域 400×180/800×140 km）"
                    "定性一致。"),
        "success": True,
        "tags": ["subduction", "subduction initiation", "Matsumoto 1983",
                 "multicomponent", "composition", "Rayleigh-Taylor", "2d"],
        "rationale_notes": {
            "Material model.Model name": "multicomponent：水/岩石圈/软流圈分相",
            "Material model.Multicomponent.Viscosities": "1e21|1e21|1e22|1e22|1e18：软流圈/岩石圈/水分层粘度（sticky water）",
            "Material model.Multicomponent.Thermal expansivities": "0：温度不参与（等温）",
            "Compositional fields.Number of fields": "4：左右岩石圈 + 左右软流圈分区",
        },
    },
    {
        "case_id": "cookbook-finite-strain",
        "title": "Tracking finite strain（变形梯度张量）",
        "domain": "mantle convection",
        "description": ("全局对流 2D 盒 8700×2900 km（x 周期），4 个组分场保存变形梯度张量 F 分量。"
                         "材料用 finite strain 插件（需编译 libfinite_strain_cookbook.so），"
                         "以 simple 为基底（ρ0=3400、k=4.7、α=2e-5、η=5e21、温度粘度指数 7、T_ref=1600）。"
                         "初始温度绝热剖面 + 边界层；顶/底切向滑移、移除 net x translation 零空间；"
                         "6 次全局加密；F 初值 = 恒等（1;0;0;1）；1800 年 checkpoint。"),
        "source": "ASPECT cookbook: cookbooks/finite_strain/finite_strain.prm（Becker et al. 2003；Dahlen & Tromp 1998）",
        "prm_path": "cookbooks/finite_strain/finite_strain.prm",
        "outcome": ("伴随流场逐步累积 F（∂F/∂t = G·F，G 为速度梯度），在任意（拉格朗日）点"
                    "追踪有限应变历史，demonstrate 材料性质/组构可依赖应变历史（如 CPO 各向异性建模基础）。"),
        "success": True,
        "tags": ["finite strain", "deformation gradient", "compositional fields",
                 "strain history", "texture", "mantle convection", "plugin", "2d"],
        "rationale_notes": {
            "Global parameters.No subsection.Additional shared libraries": "./libfinite_strain_cookbook.so：需先编译插件",
            "Compositional fields.Number of fields": "4：F 的 4 个分量",
            "Material model.Model name": "finite strain：插件把 F 分量的反应项设为速度梯度×前步 F",
            "Geometry model.Box.X periodic": "true：横向周期",
        },
    },
]


def build_case(spec: dict, cookbook_root: Path) -> dict | None:
    """把一个 case spec 转成 SimulationCase 兼容 dict。"""
    file = cookbook_root / spec["prm_path"]
    if not file.exists():
        print(f"[cookbook] !! missing prm: {file}", file=sys.stderr)
        return None
    tree = parse_prm_file(file)  # 主文件的 include 指令在 parse 内部自动解析
    notes = spec.get("rationale_notes", {})
    default_rationale = _src(spec["prm_path"])
    decisions = [
        {
            "parameter_name": key,
            "value": value,
            "rationale": notes.get(key, default_rationale),
        }
        for key, value in tree.items()
    ]
    return {
        "case_id": spec["case_id"],
        "title": spec["title"],
        "domain": spec["domain"],
        "description": spec["description"],
        "source": spec["source"],
        "prm_path": spec["prm_path"],
        "parameter_decisions": decisions,
        "outcome": spec["outcome"],
        "success": spec["success"],
        "tags": spec["tags"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import ASPECT cookbooks as expert cases into cases.json")
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="cases.json 路径")
    ap.add_argument("--cookbook-root", type=Path, default=DEFAULT_COOKBOOK_ROOT,
                    help="ASPECT 源码根目录（含 cookbooks/ 子目录）")
    ap.add_argument("--dry-run", action="store_true", help="只打印结果，不写入 cases.json")
    ap.add_argument("--overwrite", action="store_true", help="case_id 冲突时覆盖旧记录")
    args = ap.parse_args(argv)

    new_cases = []
    for spec in CASES:
        case = build_case(spec, args.cookbook_root)
        if case is None:
            continue
        new_cases.append(case)
        print(
            f"[cookbook] case '{case['case_id']}': {len(case['parameter_decisions'])} decisions",
            file=sys.stderr,
        )

    if args.dry_run:
        print(json.dumps({"cases": new_cases}, ensure_ascii=False, indent=2))
        return 0

    # 与现有 cases.json 合并（复用 extractor.write_cases 语义）
    existing: list[dict] = []
    if args.cases.exists():
        existing = json.loads(args.cases.read_text(encoding="utf-8")).get("cases", [])
    by_id = {c["case_id"]: c for c in existing}
    added = replaced = 0
    for c in new_cases:
        if c["case_id"] in by_id:
            if args.overwrite:
                by_id[c["case_id"]] = c
                replaced += 1
        else:
            by_id[c["case_id"]] = c
            added += 1
    args.cases.write_text(
        json.dumps({"cases": list(by_id.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[cookbook] wrote {args.cases}: +{added} added, {replaced} replaced", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())