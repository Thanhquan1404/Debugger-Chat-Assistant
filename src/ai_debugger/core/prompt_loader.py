"""
YAML prompt loader + Jinja2 renderer.

Design:
- StrictUndefined: missing variable → immediate error (no silent blanks).
- Cache compiled template by (name, version) — reload only on content change.
- validate() is called at startup for fail-fast.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml
from jinja2 import Environment, StrictUndefined, Template, TemplateError

log = structlog.get_logger(__name__)


class PromptError(RuntimeError):
    pass


class PromptNotFoundError(PromptError):
    pass


class PromptFormatError(PromptError):
    pass


@dataclass(frozen=True)
class RenderedPrompt:
    name: str
    version: int
    system: str
    user: str

    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


class PromptLoader:
    REQUIRED_FIELDS = ("name", "version", "system", "user_template")

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._env = Environment(undefined=StrictUndefined, autoescape=False)
        self._raw_cache: dict[str, dict[str, Any]] = {}
        self._tpl_cache: dict[str, Template] = {}

    # ---------- load ----------

    def load(self, name: str) -> dict[str, Any]:
        if name in self._raw_cache:
            return self._raw_cache[name]

        path = self._dir / f"{name}.yaml"
        if not path.exists():
            raise PromptNotFoundError(f"prompt file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise PromptFormatError(f"{path.name}: invalid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise PromptFormatError(f"{path.name}: root must be a mapping")

        missing = [k for k in self.REQUIRED_FIELDS if k not in data]
        if missing:
            raise PromptFormatError(f"{path.name}: missing fields {missing}")

        self._raw_cache[name] = data
        log.info("prompt.loaded", name=name, version=data.get("version"))
        return data

    # ---------- render ----------

    def render(self, prompt_name: str, **variables: Any) -> RenderedPrompt:
        data = self.load(prompt_name)
        user_tpl = self._compile(prompt_name, data["user_template"])
        try:
            user_text = user_tpl.render(**variables)
        except TemplateError as exc:
            raise PromptFormatError(f"prompt {prompt_name!r} render failed: {exc}") from exc

        return RenderedPrompt(
            name=data["name"],
            version=int(data["version"]),
            system=str(data["system"]).strip(),
            user=user_text.strip(),
        )

    def validate(self, name: str) -> None:
        """Fail-fast check for use at startup."""
        self.load(name)

    def _compile(self, name: str, source: str) -> Template:
        key = f"{name}:{abs(hash(source))}"
        tpl = self._tpl_cache.get(key)
        if tpl is None:
            tpl = self._env.from_string(source)
            self._tpl_cache[key] = tpl
        return tpl
