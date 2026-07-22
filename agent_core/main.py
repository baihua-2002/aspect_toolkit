from pathlib import Path
from agent_core.providers import ProviderRegistry
from agent_core.tui import AspectTUI


def main() -> None:
    config_path = Path(__file__).parent / "providers.yaml"
    registry = ProviderRegistry(config_path)
    tui = AspectTUI(registry)
    tui.run()


if __name__ == "__main__":
    main()
