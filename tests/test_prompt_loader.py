from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_debugger.core.prompt_loader import (
    PromptFormatError,
    PromptLoader,
    PromptNotFoundError,
)


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "greet.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "greet",
                "version": 2,
                "system": "You are kind.",
                "user_template": "Hello {{ name }}. Context: {{ ctx | default('none') }}",
            }
        ),
        encoding="utf-8",
    )
    return d


def test_render_ok(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    p = loader.render("greet", name="An", ctx="X")
    assert p.system == "You are kind."
    assert "Hello An." in p.user
    assert "Context: X" in p.user
    assert p.version == 2


def test_render_default(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    p = loader.render("greet", name="An")  # ctx missing → default kicks in
    assert "Context: none" in p.user


def test_missing_variable_raises(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    with pytest.raises(PromptFormatError):
        loader.render("greet")  # 'name' missing, no default → StrictUndefined


def test_missing_file(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    with pytest.raises(PromptNotFoundError):
        loader.load("nope")


def test_missing_required_field(tmp_path: Path) -> None:
    d = tmp_path / "p"
    d.mkdir()
    (d / "bad.yaml").write_text(yaml.safe_dump({"name": "bad"}), encoding="utf-8")
    loader = PromptLoader(d)
    with pytest.raises(PromptFormatError):
        loader.load("bad")


def test_cache_reused(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    a = loader.load("greet")
    b = loader.load("greet")
    assert a is b  # same object from cache


def test_to_messages(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    p = loader.render("greet", name="An")
    msgs = p.to_messages()
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
