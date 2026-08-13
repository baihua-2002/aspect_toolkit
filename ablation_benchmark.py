#!/usr/bin/env python3
"""消融实验：有工具 vs 无工具 × 限定修改轮次。

对 test_case 下每个 case：
  * 有工具变体：AspectAgent(use_tools=True)，可检索 RAG、查 schema、读写 prm、运行 ASPECT 并修复；
  * 无工具变体：AspectAgent(use_tools=False)，纯 LLM 直接输出完整 .prm；
  * 两种变体都受 max_rounds 限制（无工具变体由本脚本逐轮反馈运行错误；有工具变体在提示词中
    显式约束"运行-修复"轮次上限，同时脚本按轮次记录）。
每轮：
  1. agent 生成 prm（有工具：从磁盘上新增/修改的 .prm 提取；无工具：从输出 ```prm 代码块提取）；
  2. 脚本用 ASPECT 实测该 prm（确定性运行，统一计时）；
  3. 失败则把错误摘要作为下一轮反馈。

评估：
  * 参数写出：agent prm 与参考 prm 的逐参数比对（键存在率 + 值匹配率）；
  * 运行结果偏差：agent 运行 statistics 与参考 statistics（test_case/<case>/output-<case>/statistics）
    共享数值列的时间对齐相对偏差（末行偏差 + 全序列偏差）。

用法：
    .venv/bin/python ablation_benchmark.py --max-rounds 2
    .venv/bin/python ablation_benchmark.py --cases subduction,shell_simple_2d --variants no_tools
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from agent_core.agent import AspectAgent
from agent_core.providers import ProviderRegistry
from connector.ASP_connector import AspectConnector

ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = ROOT / "test_case"
RUNS_DIR = ROOT / "runs"
ABLATION_ROOT = RUNS_DIR / f"ablation_{datetime.now():%Y%m%d-%H%M%S}"

MAX_AGENT_SECONDS = 900  # 单次 agent 调用超时

# ---------------------------------------------------------------------------
# prm 解析：文本 -> {dot_path: value}
# ---------------------------------------------------------------------------


def parse_prm(text: str) -> dict[str, str]:
    """解析 ASPECT prm 文本为 {点路径: 值}（注释剥离、反斜杠续行合并）。"""

    lines = text.splitlines()
    # 合并续行：以 '\' 结尾的行与下一行合并
    merged: list[str] = []
    buf = ""
    for ln in lines:
        stripped = ln.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
        else:
            merged.append(buf + stripped)
            buf = ""
    if buf:
        merged.append(buf)

    params: dict[str, str] = {}
    stack: list[str] = []
    for raw in merged:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^subsection\s+(.+?)\s*$", line)
        if m:
            stack.append(m.group(1).strip())
            continue
        if line == "end":
            if stack:
                stack.pop()
            continue
        m = re.match(r"^set\s+(.+?)\s*=\s*(.*)$", line)
        if m:
            name, value = m.group(1).strip(), m.group(2).strip()
            # 行内注释剥离
            value = re.sub(r"\s+#.*$", "", value).strip()
            # 忽略 include 引用（参考 prm 均为单文件）
            if name.lower() == "include":
                continue
            key = ".".join(stack + [name])
            params[key] = _norm(value)
    return params


def _norm(v: str) -> str:
    """值规范化：折叠空白。"""
    return re.sub(r"\s+", " ", v).strip()


def _values_equal(ref: str, got: str, rtol: float = 1e-6) -> bool:
    try:
        return abs(float(ref) - float(got)) <= rtol * max(1.0, abs(float(ref)))
    except ValueError:
        return _norm(ref) == _norm(got)


def compare_prms(ref_text: str, got_text: str) -> dict:
    ref = parse_prm(ref_text)
    got = parse_prm(got_text)
    missing, mismatched, matched = [], [], []
    for key, rv in ref.items():
        if key not in got:
            missing.append(key)
        elif _values_equal(rv, got[key]):
            matched.append(key)
        else:
            mismatched.append((key, rv, got[key]))
    extra = [k for k in got if k not in ref]
    n = len(ref)
    return {
        "ref_params": n,
        "key_presence": len(matched) + len(mismatched),
        "key_presence_rate": (len(matched) + len(mismatched)) / n if n else 1.0,
        "match_rate": len(matched) / n if n else 1.0,
        "matched": len(matched),
        "mismatched": [{"key": k, "ref": r, "got": g} for k, r, g in mismatched],
        "missing": missing,
        "extra_params": len(extra),
    }


# ---------------------------------------------------------------------------
# statistics 解析与偏差
# ---------------------------------------------------------------------------


def parse_statistics(path: Path) -> dict:
    """解析 ASPECT statistics 文件。

    注意：部分后处理器列（如 Visualization file name）可能是路径或空串 ""，
    因此按列号逐 token 解析，非数值记为 NaN（偏差计算时跳过）。
    """
    names: dict[int, str] = {}
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.rstrip()
        if line.startswith("# "):
            m = re.match(r"# (\d+):\s*(.*)", line)
            if m:
                names[int(m.group(1))] = m.group(2).strip()
            continue
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != len(names):
            continue  # 列数不齐（如带空格的文件名），整行跳过
        row = []
        for tok in parts:
            try:
                row.append(float(tok))
            except ValueError:
                row.append(float("nan"))
        rows.append(row)
    col_names = [names[i + 1] for i in range(len(names))]
    return {"columns": col_names, "rows": rows}


def _time_col(stats: dict) -> str | None:
    for c in stats["columns"]:
        if c.startswith("Time ("):
            return c
    return None


def stats_deviation(ref_stats: dict, got_stats: dict) -> dict:
    tc = _time_col(ref_stats)
    if tc is None or _time_col(got_stats) is None:
        return {"error": "statistics 缺少 Time 列"}
    tc_g = _time_col(got_stats)
    ref_ti, got_ti = ref_stats["columns"].index(tc), got_stats["columns"].index(tc_g)
    common = [
        (i, j)
        for i, c in enumerate(ref_stats["columns"])
        for j, d in enumerate(got_stats["columns"])
        if c == d and c != tc and i != ref_ti
    ]
    if not common:
        return {"error": "无共享数值列"}

    got_by_time: dict[float, list[float]] = {}
    for row in got_stats["rows"]:
        got_by_time.setdefault(row[got_ti], row)

    def nearest(row_ref: list[float]):
        t = row_ref[ref_ti]
        best, best_dt = None, None
        for tg, row in got_by_time.items():
            dt = abs(tg - t) / max(abs(t), 1e-30)
            if dt <= 1e-3 and (best_dt is None or dt < best_dt):
                best, best_dt = row, dt
        return best

    per_col_series: dict[str, list[float]] = {}
    per_col_final: dict[str, float] = {}
    matched_rows = 0
    for ref_row in ref_stats["rows"]:
        got_row = nearest(ref_row)
        if got_row is None:
            continue
        matched_rows += 1
        for i, j in common:
            r, a = ref_row[i], got_row[j]
            name = ref_stats["columns"][i]
            if not (r == r and a == a):  # 跳过 NaN
                continue
            per_col_series.setdefault(name, []).append(
                abs(a - r) / max(abs(r), 1e-30)
            )
            per_col_final[name] = abs(a - r) / max(abs(r), 1e-30)
    if not matched_rows:
        return {"error": "无时间对齐的行", "matched_rows": 0}
    series = {k: sum(v) / len(v) for k, v in per_col_series.items()}
    return {
        "matched_rows": matched_rows,
        "columns": sorted(common, key=lambda p: p[0]) ,
        "dev_series_mean": sum(series.values()) / len(series),
        "dev_final_mean": sum(per_col_final.values()) / len(per_col_final),
        "dev_final_per_column": {k: round(v, 6) for k, v in sorted(per_col_final.items())},
        "dev_series_per_column": {k: round(v, 6) for k, v in sorted(series.items())},
    }


# ---------------------------------------------------------------------------
# agent 运行（带超时）
# ---------------------------------------------------------------------------


def run_agent_with_timeout(
    agent: AspectAgent, prompt: str, timeout: float, max_retries: int = 3
) -> tuple[str, object]:
    """运行 agent，带连接错误重试（网络抖动/API 超时）与总时长上限。"""
    holder: dict = {}

    def _work() -> None:
        try:
            holder["result"] = agent.run_sync(
                prompt, request_limit=200, tool_calls_limit=200
            )
        except Exception as e:  # noqa: BLE001
            holder["error"] = f"{type(e).__name__}: {e}"

    for attempt in range(1, max_retries + 1):
        holder.clear()
        th = threading.Thread(target=_work, daemon=True)
        th.start()
        th.join(timeout)
        if th.is_alive():
            return "timeout", None
        if "error" in holder:
            err = holder["error"]
            if attempt < max_retries:
                time.sleep(30 * attempt)
                continue
            return "error", err
        return "ok", holder["result"]
    return "error", "unknown"


def snapshot_prms() -> dict[Path, float]:
    snap = {}
    for p in ROOT.rglob("*.prm"):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(x in parts for x in (".venv", ".git", "node_modules")):
            continue
        snap[p] = p.stat().st_mtime
    return snap


def extract_fenced_prm(output: str) -> str | None:
    blocks = re.findall(r"```prm\s*\n(.*?)```", output, re.S)
    if not blocks:
        return None
    return blocks[-1].strip()


def _prm_completeness(path: Path) -> int:
    """按内容完整度评分：set/subsection 行数加权。agent 可能先写探针/临时文件。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return -1
    sets = len(re.findall(r"^\s*set\s+", text, re.M))
    subs = len(re.findall(r"^\s*subsection\s+", text, re.M))
    return sets * 2 + subs


def find_authored_prm(snap: dict[Path, float], t0: float, t1: float) -> Path | None:
    touched = []
    for p in snap:
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        if t0 <= mt <= t1:  # 重新 stat：快照里存在但被改写的文件也能命中
            touched.append(p)
    for p in ROOT.rglob("*.prm"):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(x in parts for x in (".venv", ".git", "node_modules")):
            continue
        if p in snap:
            continue
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        if t0 <= mt <= t1:
            touched.append(p)
    candidates = [p for p in touched if _prm_completeness(p) >= 12]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (_prm_completeness(p), p.stat().st_mtime))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def discover_cases() -> list[str]:
    names = []
    for sub in sorted(p for p in TEST_CASE_DIR.iterdir() if p.is_dir()):
        if (sub / f"{sub.name}_task.md").exists() and (sub / f"{sub.name}.prm").exists():
            names.append(sub.name)
    return names


def run_aspect(connector: AspectConnector, prm_path: Path, work_dir: Path, timeout: float) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        res = connector.run(prm_path, timeout=timeout, working_dir=work_dir)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"{type(e).__name__}: {e}", "elapsed": None}
    out = {
        "success": res.success,
        "returncode": res.returncode,
        "elapsed": round(res.elapsed_seconds, 1),
        "timed_out": res.timed_out,
        "output_dir": str(res.output_directory) if res.output_directory else None,
    }
    if not res.success:
        err = (res.stderr or res.stdout or "")
        out["error_excerpt"] = err[:2000]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="有工具 vs 无工具消融实验")
    ap.add_argument("--cases", default=None, help="逗号分隔的 case 名，默认全部")
    ap.add_argument("--variants", default="tools,no_tools")
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    cases = args.cases.split(",") if args.cases else discover_cases()
    variants = [v.strip() for v in args.variants.split(",")]
    ABLATION_ROOT.mkdir(parents=True, exist_ok=True)

    registry = ProviderRegistry(ROOT / "agent_core" / "providers.yaml")
    model = registry.get_model(args.provider)
    connector = AspectConnector()

    summary: dict = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "provider": args.provider,
        "max_rounds": args.max_rounds,
        "results": {},
    }

    for case in cases:
        case_dir = TEST_CASE_DIR / case
        task_text = (case_dir / f"{case}_task.md").read_text(encoding="utf-8")
        ref_prm_text = (case_dir / f"{case}.prm").read_text(encoding="utf-8")
        ref_stats_path = next((case_dir / f"output-{case}").glob("statistics"), None)
        ref_stats = parse_statistics(ref_stats_path) if ref_stats_path else None

        for variant in variants:
            use_tools = variant == "tools"
            agent = AspectAgent(model, use_tools=use_tools)
            vdir = ABLATION_ROOT / case / variant
            vdir.mkdir(parents=True, exist_ok=True)

            rounds_used, last_run, final_prm_text, final_prm_path = 0, None, None, None
            feedback = ""
            for rnd in range(1, args.max_rounds + 1):
                rounds_used = rnd
                rdir = vdir / f"round{rnd}"
                rdir.mkdir(parents=True, exist_ok=True)

                prompt = task_text
                if use_tools:
                    prompt += (
                        "\n\n【实验约束】本次任务最多允许 "
                        f"{args.max_rounds} 轮\"运行-修复\"循环"
                        "（每轮 = 一次 run_aspect_simulation + 修改；本轮是第 "
                        f"{rnd} 轮）。若运行成功请立即停止；若轮次耗尽仍未成功，"
                        "请直接写出你认为最完善的 prm 文件，并注明剩余问题。"
                    )
                if feedback:
                    prompt += "\n\n## 上一轮运行反馈（请据此修复）\n" + feedback
                (rdir / "prompt.txt").write_text(prompt, encoding="utf-8")

                t0 = time.time()
                snap = snapshot_prms() if use_tools else None
                status, result = run_agent_with_timeout(agent, prompt, MAX_AGENT_SECONDS)
                t1 = time.time()
                agent_out = ""
                messages: list[str] = []
                if status == "ok":
                    agent_out = result.output or ""
                    messages = result.messages or []
                elif status == "timeout":
                    agent_out = "<agent timeout>"
                else:
                    agent_out = f"<agent error: {result}>"
                (rdir / "agent_output.txt").write_text(agent_out, encoding="utf-8")

                # 提取 prm
                prm_text = None
                authored = find_authored_prm(snap, t0, t1) if snap else None
                if authored:
                    prm_text = authored.read_text(encoding="utf-8", errors="replace")
                    final_prm_path = authored
                else:
                    fenced = extract_fenced_prm(agent_out)
                    if fenced:
                        prm_text = fenced
                        final_prm_path = rdir / "agent.prm"
                        final_prm_path.write_text(prm_text, encoding="utf-8")
                if prm_text is not None:
                    final_prm_text = prm_text
                    (rdir / "agent.prm").write_text(prm_text, encoding="utf-8")

                # 实测：把 case 的依赖文件（world builder、插件）复制进隔离目录，
                # 使相对路径引用（*.wb、plugin/build_mac/*.so）在运行目录内可解析
                for dep in case_dir.glob("*.wb"):
                    shutil.copy(dep, rdir / dep.name)
                plugin_dir = case_dir / "plugin"
                if plugin_dir.is_dir():
                    shutil.copytree(plugin_dir, rdir / "plugin", dirs_exist_ok=True)

                run = None
                if prm_text is not None:
                    target = rdir / "agent.prm"
                    run = run_aspect(connector, target, rdir, args.timeout)
                    stats_paths = list(rdir.glob("output-*/statistics"))
                    if stats_paths:
                        run["stats"] = str(stats_paths[0])
                        shutil.copy(stats_paths[0], rdir / "statistics.txt")
                (rdir / "round.json").write_text(
                    json.dumps(
                        {
                            "round": rnd,
                            "status": status,
                            "tool_calls": sum(1 for m in messages if "[Tool:" in m),
                            "elapsed_agent": round(t1 - t0, 1),
                            "prm_extracted": prm_text is not None,
                            "authored_path": str(final_prm_path) if final_prm_path else None,
                            "run": run,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                last_run = run
                if run and run["success"]:
                    break
                if run and run.get("error_excerpt"):
                    feedback = run["error_excerpt"][:2000]
                elif prm_text is None:
                    feedback = (
                        "上一轮你没有产出任何可用的 .prm（未写出文件或输出为空）。"
                        "请务必在本轮直接生成完整可运行的 .prm 并确保写入磁盘。"
                    )

            # 评估
            eval_res = {
                "rounds_used": rounds_used,
                "run_success": bool(last_run and last_run["success"]),
                "run_elapsed": (last_run or {}).get("elapsed"),
                "prm_extracted": final_prm_text is not None,
                "final_agent_output": (final_prm_text or "")[:200],
            }
            if final_prm_text is not None:
                eval_res["param_compare"] = compare_prms(ref_prm_text, final_prm_text)
            if last_run and last_run["success"] and ref_stats:
                got_path = last_run.get("stats")
                if got_path:
                    got_stats = parse_statistics(Path(got_path))
                    eval_res["result_deviation"] = stats_deviation(ref_stats, got_stats)
            else:
                eval_res["result_deviation"] = {"error": "agent prm 运行未成功，无偏差可比"}

            (vdir / "evaluation.json").write_text(
                json.dumps(eval_res, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            summary["results"][case] = summary["results"].get(case, {})
            summary["results"][case][variant] = eval_res
            print(f"[{case}/{variant}] rounds={rounds_used} "
                  f"run_ok={eval_res['run_success']} "
                  f"param_match={eval_res.get('param_compare', {}).get('match_rate')}")

    (ABLATION_ROOT / "ablation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_markdown(summary, ABLATION_ROOT / "ablation_summary.md")
    print(f"\n完成：{ABLATION_ROOT}")


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        f"# 消融实验：有工具 vs 无工具（max_rounds={summary['max_rounds']}，provider={summary['provider']}）",
        "",
        f"> 生成时间: {summary['generated']}",
        "> 参数匹配率 = agent prm 与参考 prm 逐参数比对（键存在 + 值相等）；",
        "> 结果偏差 = agent 运行 statistics 与参考 statistics 共享数值列的时间对齐相对偏差（0 = 完全一致）。",
        "",
        "| 用例 | 变体 | 轮次 | 运行成功 | 参数匹配率 | 键存在率 | 结果偏差(末行均值) | 结果偏差(序列均值) |",
        "|------|------|------|---------|-----------|---------|-------------------|-------------------|",
    ]
    for case, vs in summary["results"].items():
        for variant in ("tools", "no_tools"):
            r = vs.get(variant, {})
            pc = r.get("param_compare", {})
            dev = r.get("result_deviation", {})
            dev_final = dev.get("dev_final_mean") if isinstance(dev, dict) else None
            dev_series = dev.get("dev_series_mean") if isinstance(dev, dict) else None
            fmt = lambda v: "-" if v is None else f"{v:.2%}"  # noqa: E731
            lines.append(
                f"| {case} | {variant} | {r.get('rounds_used', '-')} | "
                f"{'✅' if r.get('run_success') else '❌'} | "
                f"{fmt(pc.get('match_rate'))} | {fmt(pc.get('key_presence_rate'))} | "
                f"{'-' if dev_final is None else f'{dev_final:.4f}'} | "
                f"{'-' if dev_series is None else f'{dev_series:.4f}'} |"
            )
    lines.append("")
    lines.append("## 参数偏差明细（匹配失败的参考参数）")
    for case, vs in summary["results"].items():
        for variant in ("tools", "no_tools"):
            r = vs.get(variant, {})
            pc = r.get("param_compare", {})
            if not pc:
                continue
            lines.append(f"\n### {case} / {variant}")
            lines.append(f"- 参考参数总数: {pc['ref_params']}，匹配: {pc['matched']}，"
                         f"缺失: {len(pc['missing'])}，值不符: {len(pc['mismatched'])}，多余: {pc['extra_params']}")
            for m in pc["missing"]:
                lines.append(f"  - 缺失: `{m}`")
            for m in pc["mismatched"]:
                lines.append(f"  - 不符: `{m['key']}`  参考=`{m['ref']}`  实际=`{m['got']}`")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
