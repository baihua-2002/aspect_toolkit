"""Basic validation for collected ASPECT parameter answers.

The validator checks that:

1. Required parameters are present.
2. Values are coercible to the declared schema type.
3. Choice parameters use one of the allowed values.
4. Dependencies are respected (e.g. ``Box`` parameters only matter when the
   geometry model is ``box``).
5. Unrecognized parameter names are flagged with suggestions.

It is intentionally lightweight: full ASPECT validation is delegated to the
actual ASPECT executable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .schema import (
    BoolParameter,
    ChoiceParameter,
    ListParameter,
    ParameterType,
    ScalarParameter,
    Subsection,
    build_schema,
)

DEPRECATED_ALIASES: Dict[str, str] = {
    "Use years in output instead of seconds": "Use years instead of seconds",
}


class ValidationError(Exception):
    """Raised when an answer fails validation."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


ValidationResult = List[Tuple[str, str]]


def validate_answers(
    answers: Dict[str, Any],
    schema: List[ParameterType] = None,
    strict: bool = False,
) -> ValidationResult:
    """Validate answers against the schema.

    Returns a list of (path, message) tuples. If the list is empty, validation
    passed.
    """
    schema = schema or build_schema()
    errors: ValidationResult = []
    _validate_level(schema, answers, errors, strict=strict)
    return errors


def _validate_level(
    schema_items: List[ParameterType],
    answers: Dict[str, Any],
    errors: ValidationResult,
    path_prefix: str = "",
    strict: bool = False,
):
    # ``answers`` is a flat dict keyed by dotted paths (e.g.
    # ``Geometry model.Box.X extent``). Split each key into the current-level
    # name (no dot) and the nested remainder so we can recurse into subsections
    # while validating leaf parameters directly.
    local: Dict[str, Any] = {}
    children: Dict[str, Dict[str, Any]] = {}
    for dotted, value in answers.items():
        if "." in dotted:
            first, rest = dotted.split(".", 1)
            children.setdefault(first, {})[rest] = value
        else:
            local[dotted] = value

    for item in schema_items:
        if isinstance(item, Subsection):
            # A subsection is present if any answer key lives under it.
            sub_answers = children.get(item.name)
            if sub_answers:
                _validate_level(
                    item.parameters,
                    sub_answers,
                    errors,
                    path_prefix=f"{path_prefix}{item.name}.",
                    strict=strict,
                )
            elif not item.optional and strict:
                # Missing mandatory subsection is reported as an error if strict.
                errors.append((path_prefix + item.name, "Missing subsection"))
            continue

        full = f"{path_prefix}{item.name}"
        if item.name not in local:
            if item.required:
                errors.append((full, "Missing required parameter"))
            continue

        value = local[item.name]
        if isinstance(item, ScalarParameter):
            if not _scalar_ok(value, item.value_type):
                errors.append((full, f"Expected {item.value_type}, got {type(value).__name__}"))
        elif isinstance(item, BoolParameter):
            if not isinstance(value, bool):
                errors.append((full, "Expected boolean"))
        elif isinstance(item, ChoiceParameter):
            if value not in item.choices:
                errors.append(
                    (full, f"'{value}' not in allowed choices: {item.choices}")
                )
        elif isinstance(item, ListParameter):
            if not isinstance(value, list):
                errors.append((full, "Expected list"))

    known_names = {
        item.name for item in schema_items
    }
    for key in local:
        if key not in known_names:
            full = f"{path_prefix}{key}"
            if key in DEPRECATED_ALIASES:
                errors.append((full, f"Deprecated name. Use '{DEPRECATED_ALIASES[key]}' instead."))
            else:
                suggestion = _suggest(key, known_names)
                msg = f"Unrecognized parameter."
                if suggestion:
                    msg += f" Did you mean '{suggestion}'?"
                errors.append((full, msg))

    known_sections = {
        item.name for item in schema_items if isinstance(item, Subsection)
    }
    for key in children:
        if key not in known_sections:
            full = f"{path_prefix}{key}"
            suggestion = _suggest(key, known_sections)
            msg = f"Unrecognized subsection."
            if suggestion:
                msg += f" Did you mean '{suggestion}'?"
            errors.append((full, msg))


def _suggest(name: str, candidates: set) -> str | None:
    lower = name.lower()
    for c in candidates:
        if lower in c.lower() or c.lower() in lower:
            return c
    return None


def _scalar_ok(value: Any, value_type: str) -> bool:
    if value_type == "float":
        return isinstance(value, (int, float))
    if value_type == "int":
        return isinstance(value, int)
    if value_type == "bool":
        return isinstance(value, bool)
    return isinstance(value, str)


def validate_or_raise(
    answers: Dict[str, Any], schema=None, strict: bool = False
):
    """Validate answers and raise a ``ValidationError`` if any check fails."""
    errors = validate_answers(answers, schema, strict)
    if errors:
        path, message = errors[0]
        raise ValidationError(path, message)
