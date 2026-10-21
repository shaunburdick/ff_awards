"""Static checks on the weekly workflow's AI summary configuration (WC-001)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "weekly-report.yml"

ENV_EXPRESSION = "${{ secrets.AI_SUMMARY_API_KEY != '' }}"

# Every optional setting, and the exact expression each one must carry.
VARIABLE_KEYS = {
    "AI_SUMMARY_BASE_URL": "${{ vars.AI_SUMMARY_BASE_URL }}",
    "AI_SUMMARY_MODEL": "${{ vars.AI_SUMMARY_MODEL }}",
    "AI_SUMMARY_TIMEOUT": "${{ vars.AI_SUMMARY_TIMEOUT }}",
    "AI_SUMMARY_MAX_TOKENS": "${{ vars.AI_SUMMARY_MAX_TOKENS }}",
    "AI_SUMMARY_REASONING_EFFORT": "${{ vars.AI_SUMMARY_REASONING_EFFORT }}",
    "AI_SUMMARY_MAX_PROMPT_CHARS": "${{ vars.AI_SUMMARY_MAX_PROMPT_CHARS }}",
}

PROMPT_KEY = "AI_SUMMARY_USER_PROMPT"


class _UniqueKeyLoader(yaml.SafeLoader):
    """A loader that refuses duplicate mapping keys instead of silently keeping the last."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate key in YAML: {key}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _workflow() -> dict[str, Any]:
    """Parse the workflow, failing on duplicate keys."""
    with WORKFLOW.open(encoding="utf-8") as handle:
        document = yaml.load(handle, Loader=_UniqueKeyLoader)
    assert isinstance(document, dict)
    return document


def _env() -> dict[str, Any]:
    env = _workflow()["env"]
    assert isinstance(env, dict)
    return env


def _lines() -> list[str]:
    return WORKFLOW.read_text(encoding="utf-8").splitlines()


class TestWorkflowGuard:
    """FR-007 and WC-001: the flag is an env expression, never an if."""

    def test_guard_is_an_env_expression_on_the_key(self) -> None:
        assert _env()["AI_SUMMARY_ENABLED"] == ENV_EXPRESSION

    def test_flag_is_never_set_unconditionally(self) -> None:
        enabled = _env()["AI_SUMMARY_ENABLED"]
        assert enabled == ENV_EXPRESSION
        assert enabled not in ("true", "false", "")

    def test_no_if_condition_mentions_the_flag(self) -> None:
        offenders = [
            line
            for line in _lines()
            if line.strip().startswith("if:") and "AI_SUMMARY_ENABLED" in line
        ]
        assert offenders == []

    def test_env_appends_are_inside_the_guard(self) -> None:
        lines = _lines()
        guard_index = next(
            index for index, line in enumerate(lines) if 'if [ "$AI_SUMMARY_ENABLED" = "true" ]' in line
        )
        end_index = next(
            index
            for index in range(guard_index + 1, len(lines))
            if lines[index].strip() == "fi"
        )
        guarded = "\n".join(lines[guard_index:end_index])

        assert 'echo "AI_SUMMARY_ENABLED=true" >> .env' in guarded
        assert 'echo "AI_SUMMARY_API_KEY=${{ secrets.AI_SUMMARY_API_KEY }}" >> .env' in guarded

    def test_no_ai_variable_is_written_unconditionally(self) -> None:
        """The .env step must not set an AI_SUMMARY_* value outside the guard."""
        lines = _lines()
        step_start = next(
            index for index, line in enumerate(lines) if "Create .env file from secrets" in line
        )
        step = "\n".join(lines[step_start:])
        guarded = step.split('if [ "$AI_SUMMARY_ENABLED" = "true" ]', 1)
        assert len(guarded) == 2, "the guard must exist"
        before_guard, after_guard = guarded
        after_guard_body = after_guard.split("fi", 1)[0]

        assert "AI_SUMMARY_" not in before_guard
        assert "AI_SUMMARY_ENABLED=true" in after_guard_body
        assert "AI_SUMMARY_API_KEY=" in after_guard_body


class TestOptionalSettings:
    """The optional settings come from repository variables, parsed from the YAML."""

    def test_every_optional_setting_is_forwarded_from_a_variable(self) -> None:
        env = _env()
        for key, expression in VARIABLE_KEYS.items():
            assert env.get(key) == expression, f"{key} is not forwarded from its variable"

    def test_prompt_reads_the_variable_then_the_secret(self) -> None:
        prompt = _env()[PROMPT_KEY]
        assert prompt == (
            "${{ vars.AI_SUMMARY_USER_PROMPT || secrets.AI_SUMMARY_USER_PROMPT }}"
        )
        assert "vars.AI_SUMMARY_USER_PROMPT" in prompt
        assert "secrets.AI_SUMMARY_USER_PROMPT" in prompt

    def test_no_block_scalar_remains_for_the_prompt(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert f"{PROMPT_KEY}: |" not in raw
        assert isinstance(_env()[PROMPT_KEY], str)
        assert _env()[PROMPT_KEY].startswith("${{")

    def test_no_duplicate_env_keys(self) -> None:
        """The loader raises on duplicates; reaching here proves the env block is clean."""
        assert _env()

    def test_comments_sit_above_the_keys(self) -> None:
        lines = _lines()
        for key in (*VARIABLE_KEYS, PROMPT_KEY):
            index = next(i for i, line in enumerate(lines) if line.strip().startswith(f"{key}:"))
            assert not lines[index].strip().startswith(f"{key}: #"), f"{key} has an inline comment"

    def test_no_optional_value_is_wrapped_in_a_shell_guard(self) -> None:
        """A blank variable is the intended signal; guards would hide it."""
        lines = _lines()
        env_start = next(i for i, line in enumerate(lines) if line.strip() == "env:")
        env_end = next(i for i in range(env_start + 1, len(lines)) if lines[i] and not lines[i].startswith(" "))
        env_block = "\n".join(lines[env_start:env_end])
        for key in (*VARIABLE_KEYS, PROMPT_KEY):
            assert 'if [ -n "$' not in env_block, "no shell guard belongs in env:"
            assert f"{key}:-" not in env_block, "no default-expansion guard belongs in env:"
