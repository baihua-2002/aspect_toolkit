from __future__ import annotations

import re
from pathlib import Path

from RAG import ParameterSearcher, CaseSearcher
from aspect_prm_builder import assembler, schema, validator
from connector import AspectConnector, ConnectorError

_param_searcher = ParameterSearcher()
_case_searcher = CaseSearcher()
_schema = schema.build_schema()
_connector = AspectConnector()


def search_parameters(keyword: str, limit: int = 10) -> str:
    """Search ASPECT parameter definitions by keyword.
    Returns a list of matching parameters with name, type, default, and brief documentation.
    """
    results = _param_searcher.search_summary(keyword, limit=limit)
    if not results:
        return "No parameters found."
    lines = []
    for p in results:
        lines.append(f"- {p.section}.{p.name} | type={p.type} | default={p.default}")
        if p.doc_brief:
            lines.append(f"  doc: {p.doc_brief}")
    return "\n".join(lines)


def search_cases(keyword: str, domain: str | None = None, limit: int = 5) -> str:
    """Search expert simulation cases by keyword.
    Returns matching cases with title, domain, parameter decisions, and outcome.
    """
    results = _case_searcher.search(keyword, domain=domain, limit=limit)
    if not results:
        return "No cases found."
    lines = []
    for c in results:
        lines.append(f"[{c.case_id}] {c.title} (domain: {c.domain})")
        lines.append(f"  description: {c.description[:200]}")
        if c.parameter_decisions:
            for d in c.parameter_decisions[:5]:
                lines.append(f"  param: {d.parameter_name} = {d.value} ({d.rationale[:80]})")
        lines.append(f"  outcome: {c.outcome[:100]}")
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


def run_aspect_simulation(prm_path: str, timeout: float = 600) -> str:
    """Run an ASPECT simulation with the given .prm file.
    Returns simulation result including success status, elapsed time, and any errors.
    """
    try:
        _connector.validate()
    except ConnectorError as e:
        return f"ASPECT binary not available: {e}"

    result = _connector.run(prm_path, timeout=timeout)
    lines = [
        f"success: {result.success}",
        f"return_code: {result.returncode}",
        f"elapsed: {result.elapsed_seconds:.1f}s",
    ]
    if result.output_directory:
        lines.append(f"output_dir: {result.output_directory}")
    if not result.success:
        stderr_tail = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
        lines.append(f"errors:\n{stderr_tail}")
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
