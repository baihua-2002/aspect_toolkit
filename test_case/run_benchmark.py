#!/usr/bin/env python3
"""自动化 benchmark 测试用例运行器（详细版 / 模糊版）。

功能：
  * 自动发现 test_case 下全部用例（扁平 *_task.md 与子目录形式）；
  * 单用例 / 多用例 / 全量批量跑（--case / --cases / --all），支持详细版与模糊版；
  * 详细版自动评分：与 *_answers.json 逐项比对（运行 40 + 参数 40 + 关键项 10 + 越界 10）；
  * 模糊版生成人工评分辅助（运行成功信号 + 假设披露抽取），不设机器分数；
  * 每次运行产物归档 runs/<case>_<version>_<ts>/，并更新 runs/benchmark_summary.{json,md}；
  * 支持单用例超时保护、失败继续、--report 重新汇总历史结果。

用法：
    uv run python test_case/run_benchmark.py --list
    uv run python test_case/run_benchmark.py --case mckenzie_3_1_stokes --version detailed
    uv run python test_case/run_benchmark.py --case mckenzie_3_4_solitary_wave --version vague
    uv run python test_case/run_benchmark.py --cases mckenzie_3_1_stokes,ncc_thermal_thinning_minimal --versions detailed,vague
    uv run python test_case/run_benchmark.py --all --versions vague --provider deepseek
    uv run python test_case/run_benchmark.py --report

评分细则见 test_case/README.md §3/§4。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_CASE_DIR = ROOT / "test_case"
RUNS_DIR = ROOT / "runs"
SUMMARY_JSON = RUNS_DIR / "benchmark_summary.json"
SUMMARY_MD = RUNS_DIR / "benchmark_summary.md"

# 详细版评分权重（与 README §3 一致）
W_RUN, W_PARAM, W_CRITICAL, W_EXTRAS = 40, 40, 10, 10

# 判定"改变物理本质"的越界参数所在段落（其余段落的冗余参数不扣分）
CRITICAL_SECTIONS = (
    "Formulation",
    "Heating model",
    "Material model",
    "Geometry model",
    "Gravity model",
    "Boundary velocity model",
    "Boundary temperature model",
    "Initial temperature model",
    "Initial composition model",
    "Melt model",
    "Boundary traction model",
)

# 模糊版假设披露的关键词（用于抽取"覆盖报告"）
ASSUMPTION_KEYWORDS = (
    "假设", "依据", "默认值", "文献", "论文", "检索", "案例", "未明确", "not stated",
    "assumption", "default", "from the paper", "from paper", "retrieved", "case_",
)

RUN_SUCCESS_MARKER = "Termination requested by criterion"


# ---------------------------------------------------------------------------
# 用例发现
# ---------------------------------------------------------------------------

def discover_cases() -> dict[str, dict]:
    """扫描 test_case，返回 {case_name: {detailed|vague|answers|acceptance|reference_prm: path}}"""
    cases: dict[str, dict] = {}

    def _register(name: str, **kw) -> None:
        cases.setdefault(name, {}).update(kw)

    for p in sorted(TEST_CASE_DIR.glob("*_task.md")):
        _register(p.name[: -len("_task.md")], detailed=str(p))
    for p in sorted(TEST_CASE_DIR.glob("*_task_vague.md")):
        _register(p.name[: -len("_task_vague.md")], vague=str(p))
    for p in sorted(TEST_CASE_DIR.glob("*_vague_acceptance.md")):
        _register(p.name[: -len("_vague_acceptance.md")], acceptance=str(p))
    for p in sorted(TEST_CASE_DIR.glob("*_answers.json")):
        _register(p.name[: -len("_answers.json")], answers=str(p))

    for sub in sorted(p for p in TEST_CASE_DIR.iterdir() if p.is_dir()):
        name = sub.name
        for cand in (sub / f"{name}_task.md", sub / "task.md"):
            if cand.exists():
                _register(name, detailed=str(cand))
        for cand in (sub / f"{name}_task_vague.md", sub / f"{name}_vague_task.md"):
            if cand.exists():
                _register(name, vague=str(cand))
        for cand in (sub / f"{name}_answers.json",):
            if cand.exists():
                _register(name, answers=str(cand))
        ref = sub / f"{name}.prm"
        if ref.exists():
            _register(name, reference_prm=str(ref))
    return cases


def list_cases(cases: dict[str, dict]) -> None:
    print(f"{'case':<36} detailed   vague   answers   acceptance")
    for name in sorted(cases):
        c = cases[name]
        print(f"{name:<36} "
              f"{'✅' if c.get('detailed') else '❌'}       "
              f"{'✅' if c.get('vague') else '❌'}      "
              f"{'✅' if c.get('answers') or c.get('reference_prm') else '❌'}      "
              f"{'✅' if c.get('acceptance') else '❌'}")


# ---------------------------------------------------------------------------
# 任务文件定位
# ---------------------------------------------------------------------------

def task_text(case: str, version: str, cases: dict[str, dict]) -> str:
    key = "detailed" if version == "detailed" else "vague"
    path = cases.get(case, {}).get(key)
    if not path:
        raise SystemExit(f"用例 {case!r} 缺少 {version} 版任务文件（--list 可查看就绪状态）")
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent 运行（带超时）
# ---------------------------------------------------------------------------

def run_agent_with_timeout(agent, prompt: str, timeout: float):
    """在守护线程中运行 agent，超时则返回 ("timeout", None)。"""
    holder: dict = {}

    def _work() -> None:
        try:
            holder["result"] = agent.run_sync(prompt)
        except Exception as e:  # noqa: BLE001
            holder["error"] = f"{type(e).__name__}: {e}"

    th = threading.Thread(target=_work, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive():
        return "timeout", None
    if "error" in holder:
        return "error", None
    return "ok", holder["result"]


# ---------------------------------------------------------------------------
# 产物发现：agent 写出的 .prm 与 ASPECT 运行证据
# ---------------------------------------------------------------------------

def _snapshot_prm_files() -> dict[Path, float]:
    """记录运行前所有 .prm 文件的 mtime，用于事后归属 agent 产物。"""
    snap = {}
    for p in ROOT.rglob("*.prm"):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(x in parts for x in (".venv", ".git", "runs", "node_modules")):
            continue
        snap[p] = p.stat().st_mtime
    return snap


def find_authored_prm(snap: dict[Path, float], t0: float, t1: float) -> Path | None:
    """在运行窗口内被新增/修改的 .prm 中，挑出 agent 亲笔写的那个。"""
    touched = []
    for p, mt in snap.items():
        if not p.exists():
            continue  # 新增文件不在快照里，另行扫描
        if t0 <= mt <= t1:
            touched.append(p)
    # 运行窗口内新增的文件
    for p in ROOT.rglob("*.prm"):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(x in parts for x in (".venv", ".git", "node_modules")):
            continue
        if not p.exists():
            continue
        mt = p.stat().st_mtime
        if t0 <= mt <= t1 and p not in touched:
            touched.append(p)

    if not touched:
        return None
    # 优先：不在 runs/、不在 output*/ 目录里的（即 agent 用 write_prm_file 亲笔写的）
    authored = [p for p in touched
                if "runs" not in p.relative_to(ROOT).parts
                and not any(part.startswith("output") for part in p.relative_to(ROOT).parts)]
    if authored:
        return max(authored, key=lambda p: p.stat().st_mtime)
    return max(touched, key=lambda p: p.stat().st_mtime)


def find_run_evidence(t0: float, t1: float) -> dict:
    """在 runs/ 下寻找窗口内的 ASPECT 运行日志，判定是否真正跑通。"""
    logs = []
    for p in RUNS_DIR.rglob("log.txt"):
        if not p.exists():
            continue
        mt = p.stat().st_mtime
        if t0 <= mt <= t1:
            logs.append(p)
    if not logs:
        return {"ran": False, "success": False, "output_dirs": [], "log_tail": ""}
    newest = max(logs, key=lambda p: p.stat().st_mtime)
    text = newest.read_text(encoding="utf-8", errors="replace")
    output_dirs = sorted({str(newest.parent) for _ in logs})
    return {
        "ran": True,
        "success": RUN_SUCCESS_MARKER in text,
        "output_dirs": output_dirs,
        "log_tail": text[-800:],
    }


# ---------------------------------------------------------------------------
# 详细版评分
# ---------------------------------------------------------------------------

def _values_equal(got, exp, tol: float = 1e-6) -> bool:
    if isinstance(exp, bool):
        return isinstance(got, bool) and got == exp
    if isinstance(exp, (int, float)):
        try:
            return abs(float(got) - float(exp)) <= tol * max(1.0, abs(float(exp)))
        except (TypeError, ValueError):
            return False
    if isinstance(exp, list):
        if not isinstance(got, list) or len(got) != len(exp):
            return False
        return all(_values_equal(a, b, tol) for a, b in zip(got, exp))
    if isinstance(exp, str):
        return str(got).strip().lower() == exp.strip().lower()
    return got == exp


def _load_truth(answers_path: str) -> dict:
    data = json.loads(Path(answers_path).read_text(encoding="utf-8"))
    params = data.get("parameters", data)
    return {k: v for k, v in params.items()
            if k not in ("benchmark_id", "title", "reference")}


def grade_detailed(prm_path: Path | None, answers_path: str,
                   evidence: dict) -> dict:
    from aspect_prm_builder import assembler

    truth = _load_truth(answers_path)
    if prm_path is None:
        return {
            "grade": 0,
            "run_score": W_RUN if evidence["success"] else 0,
            "param_score": 0,
            "critical_score": 0,
            "extras_score": 0,
            "matched": 0, "total": len(truth),
            "mismatches": [f"{k}: 期望 {v} / 未产出可解析的 .prm" for k, v in truth.items()],
            "run_success": evidence["success"],
            "note": "未找到 agent 产出的 .prm 文件，无法评分",
        }

    got = assembler.parse_prm(prm_path.read_text(encoding="utf-8", errors="replace"))

    mismatches, matched = [], 0
    for key, exp in truth.items():
        if key in got and _values_equal(got[key], exp):
            matched += 1
        else:
            mismatches.append(f"{key}: 期望 {exp!r} / 实际 {got.get(key)!r}")

    # 关键项：模型选择类参数，错一个即全扣
    critical_keys = [k for k in truth if "Model name" in k] + \
                    [k for k in truth if k == "Formulation.Formulation"]
    critical_miss = [k for k in critical_keys
                     if k not in got or not _values_equal(got.get(k), truth[k])]

    # 越界项：物理本质相关段落里出现答案之外的新参数
    extras = [k for k in got if k not in truth
              and any(k.startswith(sec) for sec in CRITICAL_SECTIONS)]

    total = max(1, len(truth))
    param_score = W_PARAM * matched / total
    run_score = W_RUN if evidence["success"] else (W_RUN // 2 if evidence["ran"] else 0)
    return {
        "grade": round(run_score + param_score +
                       (W_CRITICAL if not critical_miss else 0) +
                       (W_EXTRAS if not extras else 0), 1),
        "run_score": run_score,
        "param_score": round(param_score, 1),
        "critical_score": W_CRITICAL if not critical_miss else 0,
        "extras_score": W_EXTRAS if not extras else 0,
        "matched": matched, "total": len(truth),
        "critical_miss": critical_miss,
        "extras": extras,
        "mismatches": mismatches[:20],
        "run_success": evidence["success"],
        "ran_aspect": evidence["ran"],
    }


def vague_grade_aid(output: str, transcript: str, evidence: dict,
                    prm_path: Path | None) -> dict:
    """模糊版不设机器分数，只产出人工评分辅助材料。"""
    corpus = f"{output}\n{transcript}"
    hits = []
    for line in corpus.splitlines():
        if any(kw in line for kw in ASSUMPTION_KEYWORDS):
            hits.append(line.strip()[:200])
    return {
        "score": None,
        "run_success": evidence["success"],
        "ran_aspect": evidence["ran"],
        "prm_produced": str(prm_path) if prm_path else None,
        "assumption_lines_found": len(hits),
        "assumption_excerpt": hits[:25],
        "output_dirs": evidence["output_dirs"],
        "note": "模糊版按 test_case/README.md §4 与 *_vague_acceptance.md 人工评分",
    }


# ---------------------------------------------------------------------------
# 单用例执行
# ---------------------------------------------------------------------------

def run_one(case: str, version: str, agent, *, timeout: float,
            cases: dict[str, dict]) -> dict:
    from agent_core.agent import AgentResult

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{case}_{version}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    task = task_text(case, version, cases)
    (run_dir / "task.md").write_text(task, encoding="utf-8")
    prompt = f"生成并运行以下需求（生成 .prm 并实际运行验证）:\n{task}"
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    t0 = time.time()
    snap = _snapshot_prm_files()
    status, result = run_agent_with_timeout(agent, prompt, timeout)
    t1 = time.time()
    elapsed = round(t1 - t0, 1)

    report: dict = {
        "case": case, "version": version,
        "model": getattr(agent, "_model_name", None),
        "status": status, "elapsed_seconds": elapsed,
        "run_dir": str(run_dir.relative_to(ROOT)),
        "timestamp": stamp,
    }
    if status != "ok":
        report["agent_error"] = None
        (run_dir / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [{case}/{version}] {status}（{elapsed}s）→ 归档 {run_dir.name}")
        return report

    assert result is not None
    report["success"] = result.success
    report["output"] = result.output
    (run_dir / "agent_output.txt").write_text(
        result.output or "(无输出)", encoding="utf-8")
    (run_dir / "transcript.txt").write_text(
        "\n".join(result.messages or []), encoding="utf-8")

    prm_path = find_authored_prm(snap, t0, t1)
    evidence = find_run_evidence(t0, t1)

    if version == "detailed":
        answers_path = cases.get(case, {}).get("answers")
        if answers_path:
            grading = grade_detailed(prm_path, answers_path, evidence)
        else:
            grading = {
                "grade": None, "note": "该用例无 answers.json（或仅有参考 .prm），无法机器评分",
                "run_success": evidence["success"],
            }
        report["grading"] = grading
        if prm_path:
            shutil.copy2(prm_path, run_dir / prm_path.name)
        print(f"  [{case}/detailed] 评分 {grading.get('grade')}/100 "
              f"(匹配 {grading.get('matched')}/{grading.get('total')}, "
              f"run={'OK' if grading.get('run_success') else 'FAIL'}) {elapsed}s")
    else:
        transcript = "\n".join(result.messages or [])
        aid = vague_grade_aid(result.output or "", transcript, evidence, prm_path)
        report["grading_aid"] = aid
        if prm_path:
            shutil.copy2(prm_path, run_dir / prm_path.name)
        print(f"  [{case}/vague] 运行={'OK' if aid['run_success'] else 'FAIL'}, "
              f"假设披露片段 {aid['assumption_lines_found']} 行（{elapsed}s）")

    (run_dir / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# 汇总报告
# ---------------------------------------------------------------------------

def collect_results() -> list[dict]:
    results = []
    for p in sorted(RUNS_DIR.glob("*_*_*/result.json")):
        try:
            results.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return results


def write_summary() -> None:
    results = collect_results()
    SUMMARY_JSON.write_text(
        json.dumps({"generated": datetime.now().isoformat(), "runs": results},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Benchmark 运行汇总",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}；共 {len(results)} 次运行。",
        "",
        "| 用例 | 版本 | 状态 | 运行 | 评分 | 匹配 | 耗时(s) | 运行目录 |",
        "|------|------|------|------|------|------|---------|----------|",
    ]
    for r in results:
        grading = r.get("grading") or {}
        aid = r.get("grading_aid") or {}
        score = grading.get("grade")
        score_txt = f"{score}/100" if isinstance(score, (int, float)) else "-"
        match = (f"{grading.get('matched')}/{grading.get('total')}"
                 if grading.get("matched") is not None else "-")
        run_ok = ("OK" if (grading.get("run_success") or aid.get("run_success")) else
                  "FAIL" if (grading.get("ran_aspect") or aid.get("ran_aspect") or
                             r.get("status") == "ok") else "N/A")
        lines.append(
            f"| {r.get('case','?')} | {r.get('version','?')} | {r.get('status','?')} "
            f"| {run_ok} | {score_txt} | {match} | {r.get('elapsed_seconds','-')} "
            f"| `{r.get('run_dir','-')}` |")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"==> 汇总已写入: {SUMMARY_JSON.name} / {SUMMARY_MD.name}（{len(results)} 次运行）")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="自动化跑 benchmark 测试用例（详细版/模糊版）")
    p.add_argument("--list", action="store_true", help="列出所有用例及双版本就绪状态")
    p.add_argument("--report", action="store_true", help="仅汇总历史运行结果")
    p.add_argument("--case", help="单个用例名（与 --version 配合）")
    p.add_argument("--cases", help="逗号分隔的用例列表")
    p.add_argument("--all", action="store_true", help="跑全部用例")
    p.add_argument("--version", "--versions", dest="versions",
                   default=None, help="逗号分隔：detailed,vague（默认 detailed）")
    p.add_argument("--provider", default=None, help="覆盖 providers.yaml 中的模型名")
    p.add_argument("--timeout", type=float, default=3600.0,
                   help="单用例 agent 超时（秒），默认 3600")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cases = discover_cases()

    if args.list:
        list_cases(cases)
        return
    if args.report:
        write_summary()
        return

    # 解析目标用例与版本
    if args.all:
        targets = sorted(cases)
    elif args.cases:
        targets = [c.strip() for c in args.cases.split(",") if c.strip()]
    elif args.case:
        targets = [args.case]
    else:
        print(__doc__)
        return

    versions = [v.strip() for v in (args.versions or "detailed").split(",")
                if v.strip() in ("detailed", "vague")]

    from agent_core.providers import ProviderRegistry
    from agent_core.agent import AspectAgent

    reg = ProviderRegistry(ROOT / "agent_core" / "providers.yaml")
    model = reg.get_model(args.provider) if args.provider else reg.current_model
    agent = AspectAgent(model)
    setattr(agent, "_model_name", str(model))  # 供报告记录

    print(f"==> 模型: {model} | 用例: {len(targets)} 个 | 版本: {versions} | "
          f"超时: {args.timeout:.0f}s")

    ok, fail = 0, 0
    for case in targets:
        if case not in cases:
            print(f"  !! 未知用例 {case!r}，跳过（--list 查看全部）")
            fail += 1
            continue
        for version in versions:
            try:
                run_one(case, version, agent, timeout=args.timeout,
                        cases=cases)
                ok += 1
            except SystemExit as e:
                print(f"  !! {case}/{version} 跳过: {e}")
                fail += 1
            except Exception as e:  # noqa: BLE001
                print(f"  !! {case}/{version} 异常: {type(e).__name__}: {e}")
                fail += 1

    write_summary()
    print(f"==> 完成：成功 {ok} / 失败或跳过 {fail}")


if __name__ == "__main__":
    main()
