from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from agent_core.tools import (
    search_parameters,
    search_cases,
    get_case_detail,
    get_schema_overview,
    list_subsection,
    validate_answers,
    assemble_prm,
    write_prm_file,
    run_aspect_simulation,
    parse_aspect_errors,
    read_prm_file,
    write_raw_prm,
    patch_prm,
)

SYSTEM_PROMPT = """\
You are an expert ASPECT simulation configuration assistant.
ASPECT is a scientific software for simulating mantle convection and geodynamic processes.

Your workflow for creating new .prm files:
1. Understand the user's simulation requirements (geometry, physics, boundary conditions, etc.)
2. Use `get_schema_overview` to understand available sections
3. Use `list_subsection` to see ALL parameters in a specific subsection (e.g. "Material model.Simple model")
4. Use `search_parameters` only when you need to find a parameter by keyword across sections
5. Use `search_cases` to find similar expert simulation cases, then
   `get_case_detail(case_id)` to read the full parameter decisions before reusing any values
6. Generate a complete answer dictionary mapping dotted parameter paths to values
7. Use `validate_answers` to check your answers before assembling
8. Use `assemble_prm` or `write_prm_file` to generate the .prm file
9. Optionally use `run_aspect_simulation` to test the simulation
10. If errors occur, use `parse_aspect_errors` to analyze them and fix the answers

Your workflow for fixing existing .prm files:
1. Read the file with `read_prm_file`
2. Run it with `run_aspect_simulation` to see the error
3. Analyze the error with `parse_aspect_errors`
4. Use `search_parameters` to find the correct parameter name or valid values
5. Fix the file with `write_raw_prm` (write the complete corrected content)
6. Verify by running `run_aspect_simulation` again
7. Repeat until the simulation succeeds

Key conventions:
- Answer dict keys are dotted paths like "Geometry model.Box.X extent"
- Always set "Geometry model.Model name" and "Material model.Model name"
- Required parameters must be included
- Use search_parameters to verify parameter names and valid choices before generating answers
- In 2D simulations, use x and y coordinates (NOT z)
- Common mistakes: "Reference viscosity" should be "Viscosity" in Simple model
- When reusing a value from a retrieved case, state which case_id it came from
- If information needed is absent from retrieved cases/parameters, say so explicitly
  instead of inventing values

When responding, always explain your reasoning and the steps you took.\
"""


# 无工具变体：纯 LLM、不暴露任何工具，直接输出完整 .prm 文件内容。
# 用于 benchmark 对照实验（有工具 vs 无工具）评估工具链对 ASPECT 终产物的精度贡献。
NO_TOOLS_SYSTEM_PROMPT = (
    "You are an expert ASPECT simulation configuration assistant. "
    "ASPECT is a scientific software for simulating mantle convection and geodynamic processes.\n"
    "You have NO tools available: you cannot search a parameter database, cannot run ASPECT, "
    "and cannot write files. You must answer purely from your own knowledge.\n\n"
    "Your single task: given a user's simulation requirement, produce a *complete, valid ASPECT "
    ".prm parameter file* directly. Output ONLY the .prm content, wrapped in a single fenced code "
    "block with the ```prm language tag.\n\n"
    "Rules for the .prm you generate:\n"
    "- Include every required parameter; ASPECT .prm syntax uses 'set Name = value' at top level and "
    "'subsection Name ... end' blocks for grouped settings.\n"
    "- Always choose and set 'Geometry model' 'Model name', 'Material model' 'Model name', etc. with "
    "the concrete parameters needed by the chosen model.\n"
    "- For a 2D box in ASPECT, use x and y extents/coordinates (NOT z).\n"
    "- Set 'set End time' to a sensible value and a 'Nonlinear solver scheme'.\n"
    "- Keep values physically reasonable and self-consistent; if the user gives specific numbers, "
    "use exactly those numbers; otherwise use standard ASPECT defaults or typical geophysical values.\n"
    "- If a required value is unknowable from the request, state it explicitly in a short comment "
    "line (#) rather than silently inventing a value.\n"
    "Do not output any prose before or after the fenced .prm block.\n"
)


@dataclass
class AgentResult:
    success: bool
    output: str = ""
    prm_path: Path | None = None
    prm_content: str | None = None
    messages: list[str] = field(default_factory=list)


def _stringify(value: Any) -> str:
    """Render a tool arg / return value into a readable string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _normalize_event(event: Any) -> dict[str, Any]:
    """Convert a pydantic-ai event into a plain dict for the TUI to render.

    Shapes emitted:
      thinking_start/thinking_delta/thinking_end, text_start/text_delta/text_end,
      tool_call, tool_result, final_result.
    A trailing ``None`` is pushed by the runner to signal completion.
    """
    kind = getattr(event, "event_kind", None)

    if kind == "part_start":
        part = getattr(event, "part", None)
        pk = getattr(part, "part_kind", None)
        idx = getattr(event, "index", 0)
        if pk == "thinking":
            return {"type": "thinking_start", "index": idx,
                    "content": getattr(part, "content", "") or ""}
        if pk == "text":
            return {"type": "text_start", "index": idx,
                    "content": getattr(part, "content", "") or ""}
        return {"type": "ignored", "event_kind": str(kind)}

    if kind == "part_delta":
        delta = getattr(event, "delta", None)
        dk = getattr(delta, "part_delta_kind", None)
        idx = getattr(event, "index", 0)
        if dk == "thinking":
            return {"type": "thinking_delta", "index": idx,
                    "delta": getattr(delta, "content_delta", "") or ""}
        if dk == "text":
            return {"type": "text_delta", "index": idx,
                    "delta": getattr(delta, "content_delta", "") or ""}
        if dk == "tool_call":
            return {"type": "tool_call_delta", "index": idx,
                    "args_delta": _stringify(getattr(delta, "args_delta", None))}
        return {"type": "ignored", "event_kind": str(kind)}

    if kind == "part_end":
        part = getattr(event, "part", None)
        pk = getattr(part, "part_kind", None)
        idx = getattr(event, "index", 0)
        if pk == "thinking":
            return {"type": "thinking_end", "index": idx,
                    "content": getattr(part, "content", "") or ""}
        if pk == "text":
            return {"type": "text_end", "index": idx,
                    "content": getattr(part, "content", "") or ""}
        return {"type": "ignored", "event_kind": str(kind)}

    if kind == "function_tool_call":
        part = getattr(event, "part", None)
        return {
            "type": "tool_call",
            "tool_name": getattr(part, "tool_name", "?"),
            "tool_call_id": getattr(part, "tool_call_id", None),
            "args": _stringify(getattr(part, "args", None)),
        }

    if kind == "function_tool_result":
        part = getattr(event, "part", None)
        return {
            "type": "tool_result",
            "tool_name": getattr(part, "tool_name", "?"),
            "tool_call_id": getattr(part, "tool_call_id", None),
            "content": _stringify(getattr(event, "content", None)),
        }

    if kind == "final_result":
        return {"type": "final_result",
                "tool_name": getattr(event, "tool_name", None)}

    return {"type": "ignored", "event_kind": str(kind)}


@dataclass
class StreamingRun:
    """Handle returned by ``AspectAgent.run_streaming``.

    The TUI drains ``events`` (a ``queue.Queue`` of normalized event dicts,
    terminated by a ``None`` sentinel) and then calls ``wait()`` to obtain the
    final ``AgentResult``.
    """
    events: Queue
    _thread: threading.Thread
    _holder: dict

    def wait(self) -> AgentResult:
        self._thread.join()
        if "error" in self._holder:
            return AgentResult(success=False, output=f"Agent error: {self._holder['error']}")
        return self._holder.get("result") or AgentResult(
            success=False, output="Agent produced no result."
        )

    @property
    def is_running(self) -> bool:
        return self._thread.is_alive()


class AspectAgent:
    def __init__(self, model: Model, use_tools: bool = True) -> None:
        """Build the ASPECT configuration agent.

        Args:
            model: The pydantic-ai model to use.
            use_tools: True (default) exposes the full 14-tool chain
                (RAG search, schema overview, validate/assemble/write, run,
                error repair). False builds a pure-LLM variant with no tools
                that must output a complete .prm from knowledge alone — used
                by benchmark_tools_compare.py for the with/without-tools
                precision contrast.
        """
        self._use_tools = use_tools
        if use_tools:
            self._agent = Agent(
                model,
                tools=[
                    search_parameters,
                    search_cases,
                    get_case_detail,
                    get_schema_overview,
                    list_subsection,
                    validate_answers,
                    assemble_prm,
                    write_prm_file,
                    run_aspect_simulation,
                    parse_aspect_errors,
                    read_prm_file,
                    write_raw_prm,
                    patch_prm,
                ],
                system_prompt=SYSTEM_PROMPT,
            )
        else:
            self._agent = Agent(
                model,
                tools=[],
                system_prompt=NO_TOOLS_SYSTEM_PROMPT,
            )

    def run_sync(
        self,
        user_request: str,
        *,
        request_limit: int = 30,
        tool_calls_limit: int = 50,
    ) -> AgentResult:
        try:
            result = self._agent.run_sync(
                user_request,
                usage_limits=UsageLimits(
                    request_limit=request_limit, tool_calls_limit=tool_calls_limit
                ),
            )
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

    def run_streaming(
        self,
        user_request: str,
        *,
        request_limit: int = 30,
        tool_calls_limit: int = 50,
    ) -> StreamingRun:
        """Run the agent in a background thread, streaming normalized events.

        Events are pushed onto ``StreamingRun.events``; a ``None`` sentinel
        marks the end. Call ``StreamingRun.wait()`` after draining the queue.
        """
        event_queue: Queue = Queue()
        holder: dict = {}

        async def _handler(_ctx: Any, events: Any) -> None:
            async for ev in events:
                event_queue.put(_normalize_event(ev))

        def _worker() -> None:
            async def _run() -> None:
                result = await self._agent.run(
                    user_request,
                    event_stream_handler=_handler,
                    usage_limits=UsageLimits(
                        request_limit=request_limit, tool_calls_limit=tool_calls_limit
                    ),
                )
                holder["result"] = AgentResult(success=True, output=result.output)
            try:
                asyncio.run(_run())
            except Exception as e:  # noqa: BLE001 - surface to TUI
                holder["error"] = str(e)
            finally:
                event_queue.put(None)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return StreamingRun(events=event_queue, _thread=thread, _holder=holder)
