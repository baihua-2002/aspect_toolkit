"""Serialize a structured answer dictionary into an ASPECT .prm file.

The assembler is the bridge between the middleware and ASPECT. It takes the
simple key/value pairs produced by the engine and writes them using the exact
format that ASPECT expects:

* Top-level parameters are written with ``set Name = value``.
* Subsections are written with ``subsection Name`` ... ``end``.
* Indentation is 2 spaces.
* Lists are joined with commas.
* Comments are taken from the schema when available.

The assembler also provides a round-trip-ish parser to read existing .prm files
into the same answer dictionary, which is useful for importing a cookbook and
editing it interactively.
"""

from __future__ import annotations

import re
import textwrap
from typing import Any, Dict, List, Optional, Tuple

from .schema import (
    BoolParameter,
    ChoiceParameter,
    ListParameter,
    ParameterType,
    RawParameter,
    ScalarParameter,
    Subsection,
    build_schema,
    get_parameter,
)


# ---------------------------------------------------------------------------
# .prm writer
# ---------------------------------------------------------------------------

def assemble_prm(
    answers: Dict[str, Any],
    schema: Optional[List[ParameterType]] = None,
    title: Optional[str] = None,
    header: Optional[str] = None,
) -> str:
    """Build a .prm file string from answers.

    Args:
        answers: Flat dictionary keyed by dotted path (e.g.
                 ``Geometry model.Model name``).
        schema: Optional schema used to add comments and guide serialization.
        title: Optional header title comment.
        header: Optional free-form header text.

    Returns:
        A string containing the complete .prm file content.
    """
    schema = schema or build_schema()
    lines: List[str] = []
    if header:
        lines.extend(_comment_block(header))
    elif title:
        lines.append(f"# {title}")
        lines.append("")

    # Sort answers so that top-level keys come first, then subsections.
    sorted_items = sorted(answers.items(), key=lambda kv: (_depth(kv[0]), kv[0]))

    # Build a hierarchical tree for easier rendering.
    tree: Dict[str, Any] = {}
    for dotted, value in sorted_items:
        _set_in_tree(tree, dotted.split("."), value)

    _render_tree(tree, schema, lines, depth=0)
    return "\n".join(lines).rstrip() + "\n"


def _depth(dotted: str) -> int:
    return len(dotted.split("."))


def _set_in_tree(tree: Dict[str, Any], parts: List[str], value: Any):
    if len(parts) == 1:
        tree[parts[0]] = value
    else:
        subtree = tree.setdefault(parts[0], {})
        _set_in_tree(subtree, parts[1:], value)


def _render_tree(
    tree: Dict[str, Any],
    schema: List[ParameterType],
    lines: List[str],
    depth: int,
    path: Tuple[str, ...] = (),
):
    # First, render top-level parameters in the schema order, then any extras.
    param_order = {item.name: i for i, item in enumerate(schema)}
    keys = sorted(tree.keys(), key=lambda k: (param_order.get(k, 999), k))

    for key in keys:
        value = tree[key]
        item = _find_schema_item(schema, key)
        full_path = path + (key,)

        if isinstance(item, Subsection):
            if not value:
                continue
            lines.append("")
            lines.append(f"{'  ' * depth}subsection {key}")
            _render_tree(value, item.parameters, lines, depth + 1, full_path)
            lines.append(f"{'  ' * depth}end")
        elif isinstance(item, (ListParameter,)) and isinstance(value, list):
            lines.append(f"{'  ' * depth}set {key} = {', '.join(str(v) for v in value)}")
        elif isinstance(item, BoolParameter) and isinstance(value, bool):
            lines.append(f"{'  ' * depth}set {key} = {str(value).lower()}")
        elif isinstance(item, RawParameter) and key == "raw_parameters" and value:
            lines.append(value)
        else:
            if value is None or value == "":
                continue
            if isinstance(value, bool):
                lines.append(f"{'  ' * depth}set {key} = {str(value).lower()}")
            else:
                lines.append(f"{'  ' * depth}set {key} = {value}")


def _find_schema_item(schema: List[ParameterType], name: str) -> Optional[ParameterType]:
    for item in schema:
        if item.name == name:
            return item
    return None


def _comment_block(text: str) -> List[str]:
    lines = []
    for line in textwrap.wrap(text, width=78):
        lines.append(f"# {line}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# .prm reader (round-trip support)
# ---------------------------------------------------------------------------

RE_SET = re.compile(r"^\s*set\s+(\S[\s\S]*?)\s*=\s*(.+)$")
RE_SUBSECTION = re.compile(r"^\s*subsection\s+(.+)$")
RE_END = re.compile(r"^\s*end\s*$")


def parse_prm(text: str, schema: Optional[List[ParameterType]] = None) -> Dict[str, Any]:
    """Parse a .prm file into a flat answer dictionary.

    This is a best-effort parser. It understands nested subsections and simple
    ``set`` lines. Comments and multi-line values are ignored.

    If a schema is provided, values are coerced using the schema parameter types
    (e.g. lists are split only for ``ListParameter`` entries). Without a schema,
    values are left as strings.
    """
    schema = schema or build_schema()
    raw: Dict[str, str] = {}
    stack: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m_sub = RE_SUBSECTION.match(line)
        if m_sub:
            stack.append(m_sub.group(1).strip())
            continue
        if RE_END.match(line):
            if stack:
                stack.pop()
            continue
        m_set = RE_SET.match(line)
        if m_set:
            key = ".".join(stack + [m_set.group(1).strip()])
            value = m_set.group(2).split("#", 1)[0].strip()
            raw[key] = value

    return _coerce_with_schema(raw, schema)


def _coerce_with_schema(raw: Dict[str, str], schema: List[ParameterType]) -> Dict[str, Any]:
    """Coerce raw string values into schema-aware Python types."""
    answers: Dict[str, Any] = {}
    for key, value in raw.items():
        param = _lookup_schema(schema, key.split("."))
        if param is None:
            # Unknown parameter: keep as string.
            answers[key] = value
        elif isinstance(param, BoolParameter):
            answers[key] = value.lower() in ("true", "yes", "y", "1", "on")
        elif isinstance(param, ChoiceParameter):
            answers[key] = value
        elif isinstance(param, ListParameter):
            answers[key] = [v.strip() for v in value.split(",")]
        elif isinstance(param, ScalarParameter):
            answers[key] = param.parse(value)
        elif isinstance(param, RawParameter):
            answers[key] = value
        else:
            answers[key] = value
    return answers


def _lookup_schema(
    items: List[ParameterType], parts: List[str]
) -> Optional[ParameterType]:
    """Find the schema parameter matching a dotted path."""
    if not parts:
        return None
    head, tail = parts[0], parts[1:]
    for item in items:
        if isinstance(item, Subsection):
            if item.name == head:
                return _lookup_schema(item.parameters, tail)
        elif item.name == head:
            return item
    return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def write_prm(
    path: str,
    answers: Dict[str, Any],
    schema: Optional[List[ParameterType]] = None,
    title: Optional[str] = None,
    header: Optional[str] = None,
):
    """Write a .prm file from answers."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(assemble_prm(answers, schema, title, header))


def read_and_render(path: str, schema: Optional[List[ParameterType]] = None) -> str:
    """Read an existing .prm file and re-render it through the middleware."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    answers = parse_prm(text, schema)
    return assemble_prm(answers, schema, header=f"Re-rendered from {path}")
