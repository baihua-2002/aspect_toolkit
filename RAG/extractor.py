"""
OCR 清洗文本 → 结构化专家案例（cases.json）抽取器。

流程：
    OCR markdown → (按页分块，可选) → LLM 按 SimulationCase schema 抽取
    → JSON 健壮解析 → 数值归一化兜底 → 校验/强转 → 合并写入 cases.json

用法：
    uv run python -m RAG.extractor test_case/OCR_xxx.md --dry-run   # 只看结果不落盘
    uv run python -m RAG.extractor test_case/OCR_xxx.md             # 合并进 cases.json

设计要点：
  - 抽取而非摘要：要求 LLM 严格输出 schema JSON，未知字段显式 "not stated"，
    禁止编造，从源头消除"信息缺失"；
  - 表格是参数的主要来源：要求把参数表逐行转成 parameter_decisions；
  - 科学计数法统一为 e-notation（1.0e22），LLM 输出后再用正则兜底；
  - 参数名映射到 ASPECT 官方点路径（命中提示表时），保证案例↔参数可关联；
  - 长文档按 `<!-- Page N -->` 边界分块抽取，再按标题相似度合并。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_CASES_PATH = Path(__file__).parent / "cases.json"
DEFAULT_PROVIDERS_PATH = Path(__file__).parent.parent / "agent_core" / "providers.yaml"

# 单 pass 直接抽取的最大字符数；超过则按页分块
MAX_SINGLE_PASS_CHARS = 45_000
DEFAULT_CHUNK_CHARS = 40_000

# ---------------------------------------------------------------------------
# ASPECT 官方参数名提示表（已逐条核对 RAG/parameters.json，section 点路径约定
# 与 tools.search_parameters 输出一致）
# ---------------------------------------------------------------------------
ASPECT_PARAM_HINT = """\
| 物理概念 | ASPECT 官方参数名 |
|---|---|
| 维度 | Global parameters.No subsection.Dimension |
| 使用年作为时间单位 | Global parameters.No subsection.Use years instead of seconds |
| 终止时间 | Global parameters.No subsection.End time |
| 几何模型选择 | Geometry model.Model name |
| 盒模型 X 方向长度 | Geometry model.Box.X extent |
| 盒模型 Y 方向长度 | Geometry model.Box.Y extent |
| 材料模型选择 | Material model.Model name |
| 参考密度 | Material model.Simple model.Reference density |
| 热膨胀系数 | Material model.Simple model.Thermal expansion coefficient |
| 参考比热容 | Material model.Simple model.Reference specific heat |
| 热导率 | Material model.Simple model.Thermal conductivity |
| 参考粘滞系数 | Material model.Simple model.Viscosity |
| 粘滞系数的温度指数 | Material model.Simple model.Thermal viscosity exponent |
| 重力模型选择 | Gravity model.Model name |
| 重力加速度大小 | Gravity model.Vertical.Magnitude |
| 顶部温度 | Boundary temperature model.Box.Top temperature |
| 底部温度 | Boundary temperature model.Box.Bottom temperature |
| 固定温度边界 | Boundary temperature model.Fixed temperature boundary indicators |
| 零速度/自由滑移边界 | Boundary velocity model.Zero velocity boundary indicators |
| 初始温度模型 | Initial temperature model.Model name |
| 初始全局网格加密 | Mesh refinement.Initial global refinement |
| 初始自适应加密 | Mesh refinement.Initial adaptive refinement |
| 终止步数 | Termination criteria.End step |
| 方程形式（Boussinesq 等） | Formulation.Formulation |
| Stokes 线性求解器容差 | Solver parameters.Stokes solver parameters.Linear solver tolerance |"""

EXTRACTION_PROMPT = """\
你是地球动力学文献清洗专家。下面是一篇论文经 OCR 清洗后的 markdown 文本，
其中包含 OCR 噪声：页眉页脚混入、LaTeX 公式、HTML 表格、跨页断句、个别数字识别错误。

你的任务：把文中的数值模拟实验抽取为结构化的专家案例记录，供 RAG 检索使用。

【案例粒度】
- 一个"案例"= 一组独立的模型设置。若文中有多种目的不同的实验
  （如 benchmark 验证 vs 正式模型、明显不同的几何/物理设置），拆成多个案例；
  仅参数取值不同的系列扫描（如改变底边界温度）属于同一案例，放入同一案例的
  parameter_decisions / outcome 中说明。

【每个案例的字段】
{{
  "case_id": "英文短横线 slug，如 ncc-thermal-thinning-2013",
  "title": "案例标题（可用中文）",
  "domain": "领域分类，从受控词表选择或新增英文短语：mantle convection / subduction /
             heat conduction / craton evolution / plume / benchmark / postglacial rebound",
  "description": "物理模型描述：几何、边界条件、流变、数值方法、网格。200-500字。",
  "source": "文献引用（作者. 题名. 期刊, 年, 卷: 页码），找不到则填 \\"not stated\\"",
  "prm_path": "\\"not stated\\"（论文通常无 prm 文件）",
  "outcome": "定量结果：误差、减薄量、速率、结论。含具体数字。",
  "success": true 或 false（计算是否完成/验证是否通过）,
  "parameter_decisions": [
    {{
      "parameter_name": "参数名：概念命中下方提示表时必须用表中的 ASPECT 官方参数名；
                        否则用简洁的英文描述性名字（如 Grid resolution, Time step）",
      "value": "数值+单位，科学计数法一律写成 e-notation，如 1.0e22 Pa s、5 mm/a、
               700 km；系列扫描写全取值，如 1773|1873|1973|2073 K",
      "rationale": "选值依据或作用 + 出处定位，如 (表1, p.3)。文中未说明依据就写 (表1, p.3)"
    }}
  ],
  "tags": ["检索关键词，中英混合，如 华北克拉通, 岩石圈减薄, thermal convection, i2vis"]
}}

【硬性规则】
1. 只抽取文中真实存在的信息；任何字段未知就写 "not stated"，禁止编造数字。
2. 表格是参数的第一来源：把每张参数表逐行转成 parameter_decisions；
   正文与表格数字冲突时以表格为准，并在 rationale 注明（如 "正文误作 1.93e-3，以表6为准"）。
   结果表（如不同温度对应的厚度/速率）必须完整保留到 outcome 中：
   逐行列出每个扫描取值对应的结果对，禁止只写范围概括。
3. value 中的 LaTeX 科学计数法（如 $1.0 \\times 10^{{22}}$、${{2.5}} \\times {{10}}^{{-5}}$）
   必须转换为 e-notation（1.0e22、2.5e-5），单位保留 SI 写法（Pa s、m/a、kg/m3、W/(m K)）。
4. 论文可能使用非 ASPECT 软件（如 I2VIS/Citcom）：照常抽取物理参数，
   概念对应时使用提示表中的 ASPECT 参数名，软件名写入 tags。
5. OCR 可能造成跨页断句，请按语义拼合；明显的 OCR 数字错误（与上下文/表格矛盾）
   按规则 2 处理，不要照抄错误值。

【ASPECT 参数名提示表】
{hint}

【输出】
只输出一个 JSON 对象 {{"cases": [...]}}，不要输出任何其他文字、不要用 markdown 代码块包裹。

【OCR 文本】
{text}"""


# ---------------------------------------------------------------------------
# 文本工具
# ---------------------------------------------------------------------------
_PAGE_RE = re.compile(r"<!--\s*Page\s+(\d+)\s*-->")
# 注意：¹²³ 在 Latin-1 区（U+00B9/B2/B3），其余上标在 U+2070–2079
_SUPERSCRIPT_MAP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻¹²³", "0123456789-123")
# 兼容 LaTeX 写法（$1.0 \times 10^{22}$ / ${2.5} \times {10}^{-5}$）与 Unicode 上标写法（1.0×10²³）
_SCI_RE = re.compile(
    r"\{?(-?\d+(?:\.\d+)?)\}?\s*(?:\\times|\\cdot|×|⋅|\*)\s*\{?10\}?\s*"
    r"(?:\^\{?\s*(-?\d+)\s*\}?|([⁰-⁹⁻¹²³][⁰-⁹⁻¹²³\d]*))"
)


def split_pages(text: str) -> list[str]:
    """按 <!-- Page N --> 标记切页；无标记时返回整篇。"""
    parts = _PAGE_RE.split(text)
    if len(parts) <= 1:
        return [text]
    pages: list[str] = []
    # parts = [prelude, num, body, num, body, ...]
    for i in range(1, len(parts), 2):
        pages.append(parts[i + 1])
    return pages or [text]


def make_chunks(pages: list[str], max_chars: int) -> list[str]:
    """把相邻页打包成不超过 max_chars 的块，块间重叠 1 页防止跨页断句丢失。"""
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for page in pages:
        if current and size + len(page) > max_chars:
            chunks.append("\n".join(current))
            current = [current[-1]]  # 1 页重叠
            size = len(current[0])
        current.append(page)
        size += len(page)
    if current:
        chunks.append("\n".join(current))
    return chunks


def normalize_value(value: str) -> str:
    """数值归一化兜底：LaTeX 科学计数法 → e-notation，去残留 LaTeX 包裹。

    注意顺序：必须先把 Unicode 上标指数（10²³）替换掉，再做 NFKC，
    否则 NFKC 会把上标压平成普通数字（10²³ → 1023）。
    """

    def _sub(m: re.Match) -> str:
        exp = m.group(2) if m.group(2) is not None else m.group(3).translate(_SUPERSCRIPT_MAP)
        return f"{m.group(1)}e{int(exp)}"

    v = value
    prev = None
    while prev != v:  # 处理嵌套/多重写法
        prev = v
        v = _SCI_RE.sub(_sub, v)
    v = unicodedata.normalize("NFKC", v)
    v = re.sub(r"\\(?:mathrm|text|mathbf|,\s*|;\s*)\{([^{}]*)\}", r"\1", v)
    v = re.sub(r"\\[,;! ]", " ", v)
    v = v.replace("$", "").replace("\\", "")
    return re.sub(r"\s{2,}", " ", v).strip()


# ---------------------------------------------------------------------------
# JSON 健壮解析
# ---------------------------------------------------------------------------

def parse_llm_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON：容忍 markdown 围栏、首尾杂音、尾随逗号。"""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("LLM output contains no JSON object")
    depth = 0
    end = -1
    in_str = False
    esc = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        raise ValueError("Unbalanced braces in LLM output")
    payload = cleaned[start : end + 1]
    payload = re.sub(r",(\s*[}\]])", r"\1", payload)  # 去尾随逗号
    return json.loads(payload)


# ---------------------------------------------------------------------------
# 案例校验 / 强转 / 合并
# ---------------------------------------------------------------------------
_STR_FIELDS = ("case_id", "title", "domain", "description", "source", "prm_path", "outcome")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w一-鿿]+", "-", title.lower()).strip("-")
    return slug[:60] or "case-unnamed"


def _norm_title(title: str) -> str:
    return re.sub(r"[^\w一-鿿]+", "", title.lower())


def coerce_case(raw: dict, *, existing_ids: set[str]) -> dict | None:
    """把 LLM 输出强转为 SimulationCase 兼容 dict；结构太差则丢弃并告警。"""
    if not isinstance(raw, dict):
        return None
    case: dict = {}
    for f in _STR_FIELDS:
        v = raw.get(f)
        case[f] = str(v).strip() if v not in (None, "") else "not stated"
    if case["case_id"] in ("", "not stated"):
        case["case_id"] = _slugify(case["title"])
    case["case_id"] = re.sub(r"\s+", "-", case["case_id"].strip().lower())
    base, n = case["case_id"], 2
    while case["case_id"] in existing_ids:
        case["case_id"] = f"{base}-{n}"
        n += 1
    existing_ids.add(case["case_id"])

    case["success"] = bool(raw.get("success", False))

    decisions = []
    for d in raw.get("parameter_decisions") or []:
        if not isinstance(d, dict) or not d.get("parameter_name"):
            continue
        value = normalize_value(str(d.get("value", "")).strip())
        if value in ("", "not stated"):
            continue  # 无值决策是噪声，缺失信息由 description 承载
        decisions.append(
            {
                "parameter_name": str(d["parameter_name"]).strip(),
                "value": value,
                "rationale": str(d.get("rationale", "")).strip(),
            }
        )
    case["parameter_decisions"] = decisions

    tags = raw.get("tags") or []
    case["tags"] = [str(t).strip() for t in tags if str(t).strip()]

    if case["title"] == "not stated" and not decisions:
        return None
    return case


def _same_case(a: dict, b: dict) -> bool:
    ta, tb = _norm_title(a["title"]), _norm_title(b["title"])
    if not ta or not tb:
        return False
    return SequenceMatcher(None, ta, tb).ratio() >= 0.75


def merge_case(target: dict, extra: dict) -> None:
    """把 extra 合并进 target（分块抽取时同一案例出现在多个块中）。"""
    for f in ("description", "outcome"):
        if len(extra.get(f, "")) > len(target.get(f, "")):
            target[f] = extra[f]
    for f in ("domain", "source"):
        if target.get(f) in ("", "not stated"):
            target[f] = extra.get(f, target[f])
    target["success"] = target["success"] or extra.get("success", False)
    seen = {(d["parameter_name"], d["value"]) for d in target["parameter_decisions"]}
    for d in extra.get("parameter_decisions", []):
        if (d["parameter_name"], d["value"]) not in seen:
            target["parameter_decisions"].append(d)
            seen.add((d["parameter_name"], d["value"]))
    target["tags"] = sorted(set(target["tags"]) | set(extra.get("tags", [])))


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------

def load_llm_config(providers_path: Path, provider_name: str | None) -> tuple[str, str, str]:
    """返回 (api_key, base_url, model)。复用 agent_core 的 providers.yaml + .env。"""
    load_dotenv()
    data = yaml.safe_load(providers_path.read_text(encoding="utf-8"))
    name = provider_name or data["default"]
    cfg = data["providers"][name]
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        raise RuntimeError(f"API key not set: {cfg['api_key_env']} (provider={name})")
    base_url = cfg.get("base_url") or "https://api.openai.com/v1"
    return api_key, base_url, cfg["model"]


def call_llm(prompt: str, *, api_key: str, base_url: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=16000,
    )
    try:
        resp = client.chat.completions.create(
            **kwargs, response_format={"type": "json_object"}
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)  # 模型不支持 JSON mode 时降级
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# 抽取主流程
# ---------------------------------------------------------------------------

def extract_cases(
    text: str,
    *,
    llm,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    verbose: bool = True,
) -> list[dict]:
    """整篇/分块抽取 → 合并去重 → 返回 SimulationCase 兼容 dict 列表。"""
    pages = split_pages(text)
    chunks = (
        [text]
        if len(text) <= MAX_SINGLE_PASS_CHARS
        else make_chunks(pages, chunk_chars)
    )
    if verbose:
        print(
            f"[extractor] {len(pages)} page(s), {len(text)} chars, "
            f"{len(chunks)} chunk(s)",
            file=sys.stderr,
        )

    cases: list[dict] = []
    seen_ids: set[str] = set()
    for i, chunk in enumerate(chunks, 1):
        prompt = EXTRACTION_PROMPT.format(hint=ASPECT_PARAM_HINT, text=chunk)
        raw_text = llm(prompt)
        payload = parse_llm_json(raw_text)
        raw_cases = payload.get("cases", [])
        if verbose:
            print(f"[extractor] chunk {i}: {len(raw_cases)} raw case(s)", file=sys.stderr)
        for raw in raw_cases:
            case = coerce_case(raw, existing_ids=seen_ids)
            if case is None:
                continue
            for existing in cases:
                if _same_case(existing, case):
                    merge_case(existing, case)
                    break
            else:
                cases.append(case)
    return cases


def write_cases(new_cases: list[dict], cases_path: Path, *, overwrite: bool) -> tuple[int, int]:
    """合并写入 cases.json，返回 (新增数, 覆盖数)。"""
    existing: list[dict] = []
    if cases_path.exists():
        existing = json.loads(cases_path.read_text(encoding="utf-8")).get("cases", [])
    by_id = {c["case_id"]: c for c in existing}
    added = replaced = 0
    for c in new_cases:
        if c["case_id"] in by_id:
            if overwrite:
                by_id[c["case_id"]] = c
                replaced += 1
        else:
            by_id[c["case_id"]] = c
            added += 1
    cases_path.write_text(
        json.dumps({"cases": list(by_id.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return added, replaced


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract structured simulation cases from OCR text")
    ap.add_argument("input", type=Path, help="OCR markdown 文件路径")
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="cases.json 路径")
    ap.add_argument("--providers", type=Path, default=DEFAULT_PROVIDERS_PATH, help="providers.yaml 路径")
    ap.add_argument("--provider", default=None, help="供应商名（默认取 providers.yaml 的 default）")
    ap.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    ap.add_argument("--dry-run", action="store_true", help="只打印结果，不写入 cases.json")
    ap.add_argument("--overwrite", action="store_true", help="case_id 冲突时覆盖旧记录")
    args = ap.parse_args(argv)

    text = args.input.read_text(encoding="utf-8")
    api_key, base_url, model = load_llm_config(args.providers, args.provider)
    print(f"[extractor] provider model={model} base_url={base_url}", file=sys.stderr)

    cases = extract_cases(
        text,
        llm=lambda p: call_llm(p, api_key=api_key, base_url=base_url, model=model),
        chunk_chars=args.chunk_chars,
    )

    print(json.dumps({"cases": cases}, ensure_ascii=False, indent=2))
    for c in cases:
        print(
            f"[extractor] case '{c['case_id']}': {len(c['parameter_decisions'])} decisions, "
            f"success={c['success']}, tags={c['tags']}",
            file=sys.stderr,
        )

    if args.dry_run:
        print("[extractor] dry-run, not writing", file=sys.stderr)
        return 0
    added, replaced = write_cases(cases, args.cases, overwrite=args.overwrite)
    print(f"[extractor] wrote {args.cases}: +{added} added, {replaced} replaced", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
