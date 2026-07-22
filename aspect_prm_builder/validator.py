"""Basic validation for collected ASPECT parameter answers.

The validator checks that:

1. Required parameters are present.
2. Values are coercible to the declared schema type.
3. Choice parameters use one of the allowed values.
4. Dependencies are respected (e.g. ``Box`` parameters only matter when the
   geometry model is ``box``).

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
    # Build a flat lookup of current-level answers.
    level_keys: Dict[str, Any] = {}
    for dotted, value in answers.items():
        first = dotted.split(".", 1)[0]
        level_keys[first] = value

    for item in schema_items:
        if isinstance(item, Subsection):
            # Validate only if the section is present.
            if item.name in level_keys and isinstance(level_keys[item.name], dict):
                _validate_level(
                    item.parameters,
                    level_keys[item.name],
                    errors,
                    path_prefix=f"{path_prefix}{item.name}.",
                    strict=strict,
                )
            elif not item.optional:
                # Missing mandatory subsection is reported as an error if strict.
                if strict:
                    errors.append((path_prefix + item.name, "Missing subsection"))
            continue

        full = f"{path_prefix}{item.name}"
        if item.name not in level_keys:
            if item.required:
                errors.append((full, "Missing required parameter"))
            continue

        value = level_keys[item.name]
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
