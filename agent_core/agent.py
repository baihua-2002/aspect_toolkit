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

from agent_core.tools import (
    search_parameters,
    search_cases,
    get_schema_overview,
    validate_answers,
    assemble_prm,
    write_prm_file,
    run_aspect_simulation,
    parse_aspect_errors,
    read_prm_file,
    write_raw_prm,
)

SYSTEM_PROMPT = """\
You are an expert ASPECT simulation configuration assistant.
ASPECT is a scientific software for simulating mantle convection and geodynamic processes.

Your workflow for creating new .prm files:
1. Understand the user's simulation requirements (geometry, physics, boundary conditions, etc.)
2. Use `get_schema_overview` to understand available parameters
3. Use `search_parameters` to look up specific parameter definitions and their valid values
4. Use `search_cases` to find similar expert simulation cases for reference
5. Generate a complete answer dictionary mapping dotted parameter paths to values
6. Use `validate_answers` to check your answers before assembling
7. Use `assemble_prm` or `write_prm_file` to generate the .prm file
8. Optionally use `run_aspect_simulation` to test the simulation
9. If errors occur, use `parse_aspect_errors` to analyze them and fix the answers

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

When responding, always explain your reasoning and the steps you took.\
"""


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
                read_prm_file,
                write_raw_prm,
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

    def run_streaming(self, user_request: str) -> StreamingRun:
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
                result = await self._agent.run(user_request, event_stream_handler=_handler)
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
