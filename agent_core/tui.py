from __future__ import annotations

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

from agent_core.agent import AspectAgent
from agent_core.providers import ProviderRegistry


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

            agent = self._ensure_agent()
            self._console.print()
            with Live(
                Spinner("dots", text="Thinking..."),
                console=self._console,
                transient=True,
            ):
                try:
                    result = agent.run_sync(text)
                except Exception as e:
                    self._console.print(f"[red]Agent error: {e}[/red]")
                    continue

            for msg in result.messages:
                if msg.startswith("[Tool:"):
                    self._console.print(f"  [dim]{msg}[/dim]")
                elif msg.startswith("[Agent]"):
                    pass

            if result.output:
                self._console.print(
                    Panel(
                        Markdown(result.output),
                        title="Agent Response",
                        border_style="green",
                    )
                )
            elif not result.success:
                self._console.print(f"[red]{result.output}[/red]")
