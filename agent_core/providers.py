from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic_ai.models import Model


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    type: str
    model: str
    api_key_env: str
    base_url: str | None = None


class ProviderRegistry:
    def __init__(self, config_path: Path | str = "providers.yaml") -> None:
        load_dotenv()
        self._path = Path(config_path)
        self._configs: dict[str, ProviderConfig] = {}
        self._default: str = ""
        self._current: str = ""
        self._load()

    def _load(self) -> None:
        with open(self._path) as f:
            data = yaml.safe_load(f)
        for name, cfg in data["providers"].items():
            self._configs[name] = ProviderConfig(
                name=name,
                type=cfg["type"],
                model=cfg["model"],
                api_key_env=cfg["api_key_env"],
                base_url=cfg.get("base_url"),
            )
        self._default = data["default"]
        self._current = self._default

    def list_providers(self) -> list[str]:
        return list(self._configs.keys())

    @property
    def default(self) -> str:
        return self._default

    @property
    def current(self) -> str:
        return self._current

    @property
    def current_config(self) -> ProviderConfig:
        return self._configs[self._current]

    def switch(self, name: str) -> None:
        if name not in self._configs:
            raise ValueError(f"Unknown provider: {name}. Available: {self.list_providers()}")
        self._current = name

    def get_model(self, name: str | None = None) -> Model:
        cfg = self._configs[name] if name else self.current_config
        api_key = os.environ.get(cfg.api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"API key not set. Set environment variable: {cfg.api_key_env}"
            )

        if cfg.type == "openai":
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                base_url=cfg.base_url or "https://api.openai.com/v1",
                api_key=api_key,
            )
            return OpenAIChatModel(cfg.model, provider=provider)

        elif cfg.type == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModel

            return AnthropicModel(cfg.model, api_key=api_key)

        elif cfg.type == "gemini":
            from pydantic_ai.models.google import GoogleModel

            return GoogleModel(cfg.model, api_key=api_key)

        else:
            raise ValueError(f"Unsupported provider type: {cfg.type}")

    @property
    def current_model(self) -> Model:
        return self.get_model()
