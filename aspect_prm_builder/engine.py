"""Interactive conversation engine for building ASPECT .prm files.

The engine is intentionally simple: it walks the schema and asks one concrete
question at a time.  Answers are stored in a plain Python dictionary.  The engine
supports both a *direct* mode (a human/LLM types answers) and a *programmatic*
mode (answers are supplied as a dict), which is ideal for LLM backends that can
produce structured JSON.

Key design decisions:

* **One question at a time** keeps the LLM's context window focused on a single
  concrete value.
* **Defaults are always shown** so the LLM can accept a sensible preset by
  pressing return.
* **Conditional subsections** are asked only when the parent choice matches
  (e.g. ``Box`` parameters only for ``Geometry model`` = ``box``).
* **Optional subsections** are asked only when the user explicitly wants them.

The engine returns a configuration dictionary that the ``assembler`` module can
serialize into a valid ASPECT .prm file.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .schema import (
    BoolParameter,
    ChoiceParameter,
    ListParameter,
    ParameterType,
    RawParameter,
    ScalarParameter,
    Subsection,
    build_schema,
)

AskFn = Callable[[str], str]


def default_ask(prompt: str) -> str:
    """Default interactive prompt using Python's built-in input."""
    try:
        return input(prompt + "\n> ")
    except EOFError:
        return ""


class BuildSession:
    """A single interactive session that collects answers for a .prm file."""

    def __init__(
        self,
        schema: Optional[List[ParameterType]] = None,
        ask: AskFn = default_ask,
    ):
        self.schema = schema or build_schema()
        self.ask = ask
        self.answers: Dict[str, Any] = {}
        # Stores the current value of choice parameters for dependency resolution.
        # Keys are the dotted section path containing the choice parameter.
        self._choices: Dict[Tuple[str, ...], str] = {}
        # Stores the value of 'List of model names' parameters for branch selection.
        self._list_choices: Dict[Tuple[str, ...], List[str]] = {}

    def run(self) -> Dict[str, Any]:
        """Run the full interactive session and return the answer dictionary."""
        self._walk(self.schema)
        return self.answers

    def run_from_dict(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Bypass interactivity and use a pre-populated answer dictionary.

        This is the primary integration path for LLMs: the LLM can produce a
        JSON object with concrete values and the engine only validates and
        normalizes it.
        """
        self.answers = dict(answers)
        return self.answers

    def _walk(self, items: List[ParameterType], path: Tuple[str, ...] = ()):
        for item in items:
            if isinstance(item, Subsection):
                self._walk_subsection(item, path)
            else:
                self._ask_parameter(item, path)

    def _walk_subsection(self, section: Subsection, path: Tuple[str, ...]):
        full_path = path + (section.name,)
        dotted = ".".join(full_path)

        if section.optional:
            answer = self.ask(
                f"\nSubsection '{section.name}' is optional. Include it? (yes/no) [no]"
            ).strip().lower()
            if answer not in ("yes", "y", "true", "1"):
                return

        # For choice-based subsections (e.g. Box vs Spherical shell), only the
        # branch that matches the selected Model name is explored.
        if not self._subsection_active(section, path):
            return

        self._walk(section.parameters, full_path)

    def _subsection_active(self, section: Subsection, path: Tuple[str, ...]) -> bool:
        """Return True if a subsection should be visited.

        A subsection is active if:
        * It is a branch of a choice section (e.g. ``Box`` under
          ``Geometry model``) and the corresponding choice matches the
          subsection name.
        * It is a branch selected by a ``List of model names`` parameter.
        * It is a regular subsection (always active unless optional).
        """
        if not path:
            return True
        parent_choice = self._choices.get(path)
        if parent_choice is not None:
            return section.name.lower() == parent_choice.lower()
        list_models = self._list_choices.get(path)
        if list_models is not None:
            return section.name.lower() in [m.lower() for m in list_models]
        return True

    def _ask_parameter(self, param: ParameterType, path: Tuple[str, ...]):
        dotted = ".".join(path + (param.name,))
        prompt = self._format_prompt(param)
        raw = self.ask(prompt)
        value = param.parse(raw)
        self.answers[dotted] = value

        if isinstance(param, ChoiceParameter):
            # Record which branch was selected for the current parent section.
            self._choices[path] = value
        elif isinstance(param, ListParameter) and param.name == "List of model names":
            self._list_choices[path] = value

    def _format_prompt(self, param: ParameterType) -> str:
        lines = ["", param.ask_text()]
        if param.doc:
            lines.append(f"  ({param.doc})")
        return "\n".join(lines)


class GuidedBuildSession(BuildSession):
    """A higher-level session that starts with a user intent and picks defaults.

    This is the recommended entry point for LLM integrations: the LLM only needs
    to say something like "convection in a 2D box" and the system will propose
    a sensible baseline, then ask only the remaining questions.
    """

    def __init__(
        self,
        schema: Optional[List[ParameterType]] = None,
        ask: AskFn = default_ask,
    ):
        super().__init__(schema, ask)
        self.intent: Optional[str] = None

    def run(self) -> Dict[str, Any]:
        intent = self.ask(
            "\nDescribe the simulation you want to build (e.g. 'convection in a 2D box')."
        )
        self.intent = intent.strip()
        self._apply_intent_defaults(self.intent)
        self._walk(self.schema)
        return self.answers

    def _apply_intent_defaults(self, intent: str):
        """Pre-fill common answers based on a short natural-language intent."""
        intent_lower = intent.lower()
        if "spherical" in intent_lower or "shell" in intent_lower or "3d" in intent_lower:
            self.answers["Geometry model.Model name"] = "spherical shell"
            self.answers["Dimension"] = 3
            self.answers["Use years instead of seconds"] = True
            self._choices[("Geometry model",)] = "spherical shell"
        else:
            self.answers["Geometry model.Model name"] = "box"
            self._choices[("Geometry model",)] = "box"
            self.answers["Dimension"] = 2

        if "visco plastic" in intent_lower or "rift" in intent_lower or "extension" in intent_lower:
            self.answers["Material model.Model name"] = "visco plastic"
            self.answers["Nonlinear solver scheme"] = "iterated Advection and Stokes"

        if "multicomponent" in intent_lower or "subduction" in intent_lower:
            self.answers["Material model.Model name"] = "multicomponent"

        if "van keken" in intent_lower or "benchmark" in intent_lower:
            self.answers["Initial temperature model.Model name"] = "function"
            self.answers["Initial temperature model.Function.Function expression"] = "0"
            self.answers["Material model.Model name"] = "simple"
            self.answers["Boundary velocity model.Tangential velocity boundary indicators"] = ["left", "right"]
            self.answers["Boundary velocity model.Zero velocity boundary indicators"] = ["bottom", "top"]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def interactive_build() -> Dict[str, Any]:
    """Run an interactive CLI session and return the answers dictionary."""
    return GuidedBuildSession().run()


def build_from_answers(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate a dictionary of answers.

    Currently this mainly stores the answers. Future extensions may add schema
    validation, coercion, and dependency checks.
    """
    session = BuildSession()
    return session.run_from_dict(answers)
