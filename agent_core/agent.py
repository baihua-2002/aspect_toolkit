from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models import Model

from agent_core.tools import (
    search_parameters,
    search_cases,
    get_schema_overview,
    validate_answers,
    assemble_prm,
    write_prm_file,
    run_aspect_simulation,
    parse_aspect_errors,
)

SYSTEM_PROMPT = """\
You are an expert ASPECT simulation configuration assistant.
ASPECT is a scientific software for simulating mantle convection and geodynamic processes.

Your workflow:
1. Understand the user's simulation requirements (geometry, physics, boundary conditions, etc.)
2. Use `get_schema_overview` to understand available parameters
3. Use `search_parameters` to look up specific parameter definitions and their valid values
4. Use `search_cases` to find similar expert simulation cases for reference
5. Generate a complete answer dictionary mapping dotted parameter paths to values
6. Use `validate_answers` to check your answers before assembling
7. Use `assemble_prm` or `write_prm_file` to generate the .prm file
8. Optionally use `run_aspect_simulation` to test the simulation
9. If errors occur, use `parse_aspect_errors` to analyze them and fix the answers

Key conventions:
- Answer dict keys are dotted paths like "Geometry model.Box.X extent"
- Always set "Geometry model.Model name" and "Material model.Model name"
- Required parameters must be included
- Use search_parameters to verify parameter names and valid choices before generating answers

When responding, always explain your reasoning and the steps you took.\
"""


@dataclass
class AgentResult:
    success: bool
    output: str = ""
    prm_path: Path | None = None
    prm_content: str | None = None
    messages: list[str] = field(default_factory=list)


class AspectAgent:
    def __init__(self, model: Model) -> None:
        self._agent = Agent(
            model,
            tools=[
                search_parameters,
                search_cases,
                get_schema_overview,
                validate_answers,
                assemble_prm,
                write_prm_file,
                run_aspect_simulation,
                parse_aspect_errors,
            ],
            system_prompt=SYSTEM_PROMPT,
        )

    def run_sync(self, user_request: str) -> AgentResult:
        try:
            result = self._agent.run_sync(user_request)
        except Exception as e:
            return AgentResult(success=False, output=f"Agent error: {e}")

        messages = []
        for msg in result.all_messages():
            role = "User" if type(msg).__name__ == "ModelRequest" else "Agent"
            for part in msg.parts:
                part_type = type(part).__name__
                if part_type == "ToolCallPart":
                    messages.append(f"[Tool:{part.tool_name}] called")
                elif hasattr(part, "content") and isinstance(part.content, str):
                    if part.content.strip():
                        messages.append(f"[{role}] {part.content}")

        return AgentResult(
            success=True,
            output=result.output,
            messages=messages,
        )
