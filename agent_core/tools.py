from __future__ import annotations

import re
from pathlib import Path
from queue import Queue

from RAG import ParameterSearcher, CaseSearcher
from aspect_prm_builder import assembler, schema, validator
from connector import AspectConnector, ConnectorError

_param_searcher = ParameterSearcher()
_case_searcher = CaseSearcher()
_schema = schema.build_schema()
_connector = AspectConnector()

_log_queue: Queue[str] | None = None


def set_log_queue(q: Queue[str] | None) -> None:
    global _log_queue
    _log_queue = q


def _push_log(line: str) -> None:
    if _log_queue is not None:
        _log_queue.put(line)


def search_parameters(keyword: str, limit: int = 10) -> str:
    """Search ASPECT parameter definitions by keyword.
    Returns matching parameters with their exact dotted key (for use in answers dict),
    type, default, and brief documentation.
    """
    results = _param_searcher.search_summary(keyword, limit=limit)
    if not results:
        return "No parameters found."
    lines = []
    for p in results:
        dotted_key = p.section.replace(" / ", ".") + "." + p.name
        lines.append(f"- {dotted_key} | type={p.type} | default={p.default}")
        if p.doc_brief:
            lines.append(f"  doc: {p.doc_brief}")
    return "\n".join(lines)


_CASE_DESC_EXCERPT = 300
_CASE_DECISIONS_SHOWN = 8
_CASE_RATIONALE_EXCERPT = 120
_CASE_OUTCOME_EXCERPT = 200


def _clip(text: str, limit: int) -> str:
    """Clip long text, marking truncation explicitly so the agent knows more exists."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…[truncated]"


def search_cases(keyword: str, domain: str | None = None, limit: int = 5) -> str:
    """Search expert simulation cases by keyword.
    Returns matching cases with title, domain, an excerpt of the parameter
    decisions, and outcome. Call get_case_detail(case_id) for the full record
    before reusing any values from a case.
    """
    results = _case_searcher.search(keyword, domain=domain, limit=limit)
    if not results:
        return "No cases found."
    lines = []
    for c in results:
        lines.append(f"[{c.case_id}] {c.title} (domain: {c.domain}, success: {c.success})")
        lines.append(f"  description: {_clip(c.description, _CASE_DESC_EXCERPT)}")
        for d in c.parameter_decisions[:_CASE_DECISIONS_SHOWN]:
            lines.append(
                f"  param: {d.parameter_name} = {d.value} ({_clip(d.rationale, _CASE_RATIONALE_EXCERPT)})"
            )
        remaining = len(c.parameter_decisions) - _CASE_DECISIONS_SHOWN
        if remaining > 0:
            lines.append(
                f'  … {remaining} more parameter decision(s) — call get_case_detail("{c.case_id}")'
            )
        lines.append(f"  outcome: {_clip(c.outcome, _CASE_OUTCOME_EXCERPT)}")
    return "\n".join(lines)


def get_case_detail(case_id: str) -> str:
    """Get the complete record of an expert simulation case by its case_id.
    Returns ALL parameter decisions (name, value, rationale with source location),
    full description, outcome, source and tags. Use this after search_cases to
    ground parameter values in the case before generating answers.
    """
    c = _case_searcher.get(case_id)
    if c is None:
        available = ", ".join(x.case_id for x in _case_searcher.all_cases()[:10]) or "(none)"
        return f"Case not found: '{case_id}'. Available case_ids: {available}"
    lines = [
        f"[{c.case_id}] {c.title}",
        f"domain: {c.domain} | success: {c.success}",
        f"source: {c.source}",
        f"tags: {', '.join(c.tags) if c.tags else '(none)'}",
        "description:",
        c.description,
        f"parameter_decisions ({len(c.parameter_decisions)}):",
    ]
    for d in c.parameter_decisions:
        lines.append(f"  - {d.parameter_name} = {d.value}")
        if d.rationale:
            lines.append(f"    rationale: {d.rationale}")
    lines.append("outcome:")
    lines.append(c.outcome)
    if c.prm_path and c.prm_path != "not stated":
        lines.append(f"prm_path: {c.prm_path}")
    return "\n".join(lines)


def get_schema_overview() -> str:
    """Get an overview of the ASPECT .prm parameter schema.
    Returns the top-level sections and their key parameters with names, types, and defaults.
    """
    flat = schema.flatten_schema(_schema)
    sections: dict[str, list[str]] = {}
    for path, param in flat:
        section = path[0] if len(path) > 1 else "(global)"
        if section not in sections:
            sections[section] = []
        if len(sections[section]) < 20:
            full_name = ".".join(path)
            ptype = getattr(param, "value_type", None)
            default = getattr(param, "default", None)
            choices = getattr(param, "choices", None)
            required = getattr(param, "required", False)

            type_str = ptype if ptype else type(param).__name__.replace("Parameter", "").lower()
            if choices:
                type_str = f"choice: {'|'.join(choices[:4])}"
            default_str = f" = {default}" if default is not None else ""
            req_str = " [required]" if required else ""
            sections[section].append(f"  {full_name} ({type_str}){default_str}{req_str}")

    lines = []
    for sec, params in sections.items():
        lines.append(f"[{sec}]")
        lines.extend(params)
        if len(params) == 20:
            lines.append("  ... (more parameters available via search_parameters)")
    return "\n".join(lines)


def list_subsection(section_path: str) -> str:
    """List ALL parameters under a given subsection path.
    Use this to see every available parameter in a subsection at once.
    Example: list_subsection("Material model.Simple model") returns all Simple model parameters.
    The returned keys are the exact dotted paths to use in the answers dictionary.
    """
    flat = schema.flatten_schema(_schema)
    prefix = section_path.rstrip(".")
    matches = []
    for path, param in flat:
        full_name = ".".join(path)
        if full_name.startswith(prefix + ".") or full_name == prefix:
            ptype = getattr(param, "value_type", None)
            default = getattr(param, "default", None)
            choices = getattr(param, "choices", None)
            required = getattr(param, "required", False)
            doc = getattr(param, "doc", "")

            type_str = ptype if ptype else type(param).__name__.replace("Parameter", "").lower()
            if choices:
                type_str = f"choice: {'|'.join(choices)}"
            default_str = f" = {default}" if default is not None else ""
            req_str = " [required]" if required else ""
            doc_str = f" | {doc[:80]}" if doc else ""
            matches.append(f"  {full_name} ({type_str}){default_str}{req_str}{doc_str}")

    if not matches:
        available = sorted(set(".".join(p[:2]) for p, _ in flat if len(p) > 1))
        return (
            f"No parameters found under '{section_path}'.\n"
            f"Available subsections: {', '.join(available[:20])}"
        )
    return f"[{section_path}] ({len(matches)} parameters)\n" + "\n".join(matches)


def validate_answers(answers: dict) -> str:
    """Validate an answer dictionary against the ASPECT schema.
    Returns a list of validation errors, or 'OK' if valid.
    """
    errors = validator.validate_answers(answers, _schema)
    if not errors:
        return "OK - no validation errors"
    lines = [f"Found {len(errors)} error(s):"]
    for path, msg in errors:
        lines.append(f"  - {path}: {msg}")
    return "\n".join(lines)


def assemble_prm(answers: dict, title: str | None = None) -> str:
    """Assemble a .prm file content string from an answer dictionary.
    The answers dict maps dotted parameter paths to values.
    """
    try:
        return assembler.assemble_prm(answers, _schema, title=title)
    except Exception as e:
        return f"Assembly error: {e}. Please check that your answer keys are valid dotted parameter paths."


def write_prm_file(answers: dict, filename: str, title: str | None = None) -> str:
    """Write a .prm file to disk from an answer dictionary.
    Returns the path of the written file.
    """
    try:
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        assembler.write_prm(str(path), answers, _schema, title=title)
        return f"Written to {path.resolve()}"
    except Exception as e:
        return f"Write error: {e}. Please check that your answer keys are valid."


def _excerpt(text: str, head: int = 2000, tail: int = 2000) -> str:
    """Return a head+tail excerpt for very long text, preserving the
    error-bearing start and the abort-bearing end that ASPECT/deal.II emits."""
    if len(text) <= head + tail:
        return text
    return f"{text[:head]}\n... [truncated {len(text) - head - tail} chars] ...\n{text[-tail:]}"


def run_aspect_simulation(prm_path: str, timeout: float = 600) -> str:
    """Run an ASPECT simulation with the given .prm file.
    Returns simulation result including success status, elapsed time, and any errors.

    All failures (missing binary, missing file, subprocess crashes, timeouts) are
    returned as a string so the LLM can read them and react — exceptions never
    propagate, which would otherwise abort the whole agent run.
    """
    try:
        result = _connector.run_streaming(
            prm_path, timeout=timeout, on_output=_push_log
        )
    except ConnectorError as e:
        _push_log(f"[error] {type(e).__name__}: {e}")
        return f"ASPECT run failed before launch: {type(e).__name__}: {e}"
    except Exception as e:  # noqa: BLE001 - surface any subprocess error to the LLM
        _push_log(f"[error] {type(e).__name__}: {e}")
        return f"ASPECT run raised an unexpected error: {type(e).__name__}: {e}"

    lines = [
        f"success: {result.success}",
        f"return_code: {result.returncode}",
        f"elapsed: {result.elapsed_seconds:.1f}s",
    ]
    if result.timed_out:
        lines.append(f"timed_out: True (limit={timeout}s)")
    if result.output_directory:
        lines.append(f"output_dir: {result.output_directory}")
    if not result.success:
        err = result.stderr
        if not err.strip() and result.stdout.strip():
            err = result.stdout  # ASPECT occasionally prints diagnostics to stdout
        lines.append(f"errors:\n{_excerpt(err)}")
    return "\n".join(lines)


def parse_aspect_errors(stderr: str) -> str:
    """Parse ASPECT stderr into structured error findings.
    Identifies error categories and suggests parameter paths to fix.
    """
    findings = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue

        if "not found" in line.lower() and "parameter" in line.lower():
            match = re.search(r"parameter\s+['\"]([^'\"]+)['\"]", line)
            param = match.group(1) if match else "unknown"
            findings.append(f"unknown_parameter: {param} | {line[:120]}")

        elif "could not convert" in line.lower() or "invalid value" in line.lower():
            findings.append(f"wrong_type: {line[:150]}")

        elif "doesn't match" in line.lower() or "does not match" in line.lower():
            findings.append(f"invalid_choice: {line[:150]}")

        elif "subsections" in line.lower() and ("not allowed" in line.lower() or "required" in line.lower()):
            findings.append(f"subsection_error: {line[:150]}")

        elif "exception" in line.lower() or "abort" in line.lower() or "error" in line.lower():
            findings.append(f"runtime_error: {line[:150]}")

    if not findings:
        return "No structured errors parsed from stderr."
    return "\n".join(findings)


def read_prm_file(path: str) -> str:
    """Read and return the content of a .prm file."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Read error: {e}"


def write_raw_prm(path: str, content: str) -> str:
    """Write raw .prm file content directly to disk.
    Use this when fixing existing .prm files where you know the exact text changes needed.
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {p.resolve()}"
    except Exception as e:
        return f"Write error: {e}"


def patch_prm(path: str, changes: dict) -> str:
    """Incrementally edit an existing .prm file by changing specific parameter values.
    The changes dict maps dotted parameter paths to new values.
    Example: patch_prm("model.prm", {"Material model.Simple model.Viscosity": 1e21})
    This is more efficient than write_raw_prm when you only need to change a few parameters.
    """
    try:
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        content = p.read_text(encoding="utf-8")
        lines = content.splitlines()
        patched = []
        not_found = []

        for dotted_key, new_value in changes.items():
            parts = dotted_key.split(".")
            param_name = parts[-1]
            subsections = parts[:-1]

            found = False
            depth = 0
            target_depth = len(subsections)
            matched_sections: list[str] = []

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("subsection "):
                    sec_name = stripped[len("subsection "):]
                    matched_sections.append(sec_name)
                    depth += 1
                elif stripped == "end":
                    if matched_sections:
                        matched_sections.pop()
                    depth -= 1
                elif stripped.startswith("set ") and depth == target_depth:
                    if matched_sections == subsections or (not subsections and depth == 0):
                        set_match = re.match(r"^(\s*set\s+)(.+?)(\s*=\s*)(.*)$", line)
                        if set_match and set_match.group(2).strip() == param_name:
                            lines[i] = f"{set_match.group(1)}{param_name}{set_match.group(3)}{new_value}"
                            found = True
                            break

            if not found:
                not_found.append(dotted_key)

        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result_parts = [f"Patched {len(changes) - len(not_found)}/{len(changes)} parameter(s) in {p.resolve()}"]
        if not_found:
            result_parts.append(f"Not found (not changed): {', '.join(not_found)}")
            result_parts.append("Use write_raw_prm to add missing parameters or check the parameter names.")
        return "\n".join(result_parts)
    except Exception as e:
        return f"Patch error: {e}"
