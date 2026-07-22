from __future__ import annotations

from collections import deque
from queue import Empty, Queue
from typing import Any

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from agent_core.agent import AspectAgent, StreamingRun
from agent_core.providers import ProviderRegistry
from agent_core.tools import set_log_queue


class _RunState:
    """Accumulated render state for one agent run."""

    def __init__(self) -> None:
        self.thinking: dict[int, str] = {}
        self.text: dict[int, str] = {}
        self.tools: list[dict[str, Any]] = []
        self.aspect_logs: deque[str] = deque(maxlen=200)
        self.finished: bool = False

    def apply(self, ev: dict[str, Any]) -> None:
        t = ev.get("type")
        if t == "thinking_start":
            self.thinking[ev["index"]] = ev.get("content", "")
        elif t == "thinking_delta":
            self.thinking[ev["index"]] = self.thinking.get(ev["index"], "") + (ev.get("delta", "") or "")
        elif t == "thinking_end":
            self.thinking[ev["index"]] = ev.get("content", "") or self.thinking.get(ev["index"], "")
        elif t == "text_start":
            self.text[ev["index"]] = ev.get("content", "")
        elif t == "text_delta":
            self.text[ev["index"]] = self.text.get(ev["index"], "") + (ev.get("delta", "") or "")
        elif t == "text_end":
            self.text[ev["index"]] = ev.get("content", "") or self.text.get(ev["index"], "")
        elif t == "tool_call":
            self.tools.append({
                "name": ev.get("tool_name", "?"),
                "call_id": ev.get("tool_call_id"),
                "args": ev.get("args", ""),
                "result": None,
                "done": False,
            })
        elif t == "tool_result":
            self._match_result(ev.get("tool_call_id"), ev.get("tool_name", "?"), ev.get("content", ""))
        elif t == "final_result":
            self.finished = True

    def _match_result(self, call_id: str | None, name: str, content: str) -> None:
        if call_id is not None:
            for tc in self.tools:
                if tc["call_id"] == call_id:
                    tc["result"], tc["done"] = content, True
                    return
        for tc in reversed(self.tools):
            if tc["name"] == name and not tc["done"]:
                tc["result"], tc["done"] = content, True
                return
        # No matching call recorded; show the result standalone.
        self.tools.append({"name": name, "call_id": call_id, "args": "", "result": content, "done": True})

    def render(self, running: bool) -> Any:
        parts: list[Any] = []

        thinking_blob = "\n".join(s for s in self.thinking.values() if s).strip()
        if thinking_blob:
            parts.append(Panel(
                Text(thinking_blob, style="dim italic magenta"),
                title="Thinking",
                border_style="magenta",
                title_align="left",
            ))

        text_blob = "\n".join(s for s in self.text.values() if s).strip()
        if text_blob:
            parts.append(Panel(
                Text(text_blob, style="cyan"),
                title="Assistant",
                border_style="cyan",
                title_align="left",
            ))

        if self.tools:
            table = Table(title="Tool Calls", border_style="yellow",
                          show_lines=True, expand=True)
            table.add_column("#", style="dim", width=3)
            table.add_column("Tool", style="bold yellow", no_wrap=True)
            table.add_column("Arguments", style="white", ratio=2, overflow="fold")
            table.add_column("Result", style="green", ratio=3, overflow="fold")
            for i, tc in enumerate(self.tools, 1):
                status = "" if tc["done"] else " [dim]…running[/dim]"
                args_txt = Text(tc["args"] or "—")
                res_txt = Text(tc["result"] if tc["result"] is not None else "…")
                table.add_row(str(i), tc["name"] + status, args_txt, res_txt)
            parts.append(table)

        if self.aspect_logs:
            log_text = Text("\n".join(self.aspect_logs))
            parts.append(Panel(
                log_text,
                title=f"ASPECT Output ({len(self.aspect_logs)} lines)",
                border_style="green",
                title_align="left",
                height=min(len(self.aspect_logs) + 2, 25),
            ))

        if running:
            parts.append(Spinner("dots", text="[dim]Working…[/dim]"))
        elif self.finished:
            parts.append(Text("✓ Done", style="bold green"))

        return Group(*parts) if parts else Text("…", style="dim")


class AspectTUI:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry
        self._console = Console()
        self._agent: AspectAgent | None = None
        self._history = InMemoryHistory()

    def _ensure_agent(self) -> AspectAgent:
        if self._agent is None:
            self._agent = AspectAgent(self._registry.current_model)
        return self._agent

    def _rebuild_agent(self) -> None:
        self._agent = AspectAgent(self._registry.current_model)

    def _print_banner(self) -> None:
        self._console.print(
            Panel(
                "[bold cyan]ASPECT Agent[/bold cyan]\n"
                "Intelligent .prm configuration assistant\n\n"
                f"Provider: [green]{self._registry.current}[/green] "
                f"({self._registry.current_config.model})\n"
                f"Available: {', '.join(self._registry.list_providers())}\n\n"
                "Commands: /switch <provider>  /status  /quit",
                title="Welcome",
                border_style="cyan",
            )
        )

    def _handle_command(self, text: str) -> bool:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/quit" or cmd == "/exit":
            self._console.print("[dim]Goodbye![/dim]")
            return True

        elif cmd == "/switch":
            if not arg:
                self._console.print("[yellow]Usage: /switch <provider_name>[/yellow]")
                self._console.print(f"Available: {self._registry.list_providers()}")
                return False
            try:
                self._registry.switch(arg)
                self._rebuild_agent()
                cfg = self._registry.current_config
                self._console.print(
                    f"[green]Switched to {arg}[/green] (model: {cfg.model})"
                )
            except (ValueError, RuntimeError) as e:
                self._console.print(f"[red]Error: {e}[/red]")

        elif cmd == "/status":
            table = Table(title="Current Configuration")
            table.add_column("Provider", style="cyan")
            table.add_column("Type")
            table.add_column("Model")
            table.add_column("Base URL")
            for name in self._registry.list_providers():
                cfg = self._registry._configs[name]
                marker = " <--" if name == self._registry.current else ""
                table.add_row(
                    f"{name}{marker}",
                    cfg.type,
                    cfg.model,
                    cfg.base_url or "(default)",
                )
            self._console.print(table)

        else:
            self._console.print(f"[yellow]Unknown command: {cmd}[/yellow]")

        return False

    def _run_agent(self, user_text: str) -> None:
        agent = self._ensure_agent()

        log_queue: Queue[str] = Queue()
        set_log_queue(log_queue)

        run = agent.run_streaming(user_text)
        state = _RunState()

        self._console.print()
        with Live(state.render(running=True), console=self._console,
                  refresh_per_second=12, transient=False) as live:
            while True:
                try:
                    ev = run.events.get(timeout=0.1)
                except Empty:
                    if not run.is_running:
                        break
                    # drain ASPECT logs even when no agent events
                    self._drain_logs(log_queue, state)
                    live.update(state.render(running=True))
                    continue
                if ev is None:
                    break
                state.apply(ev)
                self._drain_logs(log_queue, state)
                live.update(state.render(running=True))

        # final drain
        self._drain_logs(log_queue, state)
        set_log_queue(None)

        result = run.wait()

        # Final, non-streaming render of the full trace.
        self._console.print(state.render(running=False))

        if result.success and result.output:
            self._console.print(
                Panel(
                    Markdown(result.output),
                    title="Agent Response",
                    border_style="green",
                )
            )
        elif not result.success:
            self._console.print(f"[red]{result.output}[/red]")
        else:
            self._console.print("[dim](no textual response)[/dim]")

    @staticmethod
    def _drain_logs(log_queue: Queue[str], state: _RunState) -> None:
        try:
            while True:
                line = log_queue.get_nowait()
                state.aspect_logs.append(line)
        except Empty:
            pass

    def run(self) -> None:
        self._print_banner()

        while True:
            try:
                text = prompt(
                    "\n> ",
                    history=self._history,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                self._console.print("\n[dim]Goodbye![/dim]")
                break

            if not text:
                continue

            if text.startswith("/"):
                if self._handle_command(text):
                    break
                continue

            try:
                self._run_agent(text)
            except Exception as e:  # noqa: BLE001 - never crash the TUI
                self._console.print(f"[red]Agent error: {e}[/red]")
