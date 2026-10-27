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


def _workflow() -> dict[str | bool, Any]:
    """Parse the workflow, failing on duplicate keys.

    Keys are ``str | bool`` because YAML 1.1 reads the top-level ``on`` as ``True``.
    """
    with WORKFLOW.open(encoding="utf-8") as handle:
        document = yaml.load(handle, Loader=_UniqueKeyLoader)
    assert isinstance(document, dict)
    return document


def _env() -> dict[str, Any]:
    env = _workflow()["env"]
    assert isinstance(env, dict)
    return env


def _report_step_env() -> dict[str, Any]:
    """The prompt lives on the report step, its only consumer."""
    steps = _workflow()["jobs"]["generate-report"]["steps"]
    step = next(step for step in steps if step.get("id") == "generate-report")
    env = step.get("env") or {}
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
            index
            for index, line in enumerate(lines)
            if 'if [ "$AI_SUMMARY_ENABLED" = "true" ]' in line
        )
        end_index = next(
            index for index in range(guard_index + 1, len(lines)) if lines[index].strip() == "fi"
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

    def test_prompt_reads_the_input_then_variable_then_secret(self) -> None:
        prompt = _report_step_env()[PROMPT_KEY]
        assert prompt == (
            "${{ inputs.ai_summary_prompt || vars.AI_SUMMARY_USER_PROMPT"
            " || secrets.AI_SUMMARY_USER_PROMPT }}"
        )
        assert "vars.AI_SUMMARY_USER_PROMPT" in prompt
        assert "secrets.AI_SUMMARY_USER_PROMPT" in prompt

    def test_prompt_is_scoped_to_the_report_step(self) -> None:
        """A prompt held in a secret must not reach checkout or the setup steps."""
        assert PROMPT_KEY not in _env()
        assert PROMPT_KEY in _report_step_env()

    def test_no_block_scalar_remains_for_the_prompt(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert f"{PROMPT_KEY}: |" not in raw
        prompt = _report_step_env()[PROMPT_KEY]
        assert isinstance(prompt, str)
        assert prompt.startswith("${{")

    def test_comments_sit_above_the_keys(self) -> None:
        lines = _lines()
        for key in (*VARIABLE_KEYS, PROMPT_KEY):
            index = next(i for i, line in enumerate(lines) if line.strip().startswith(f"{key}:"))
            assert not lines[index].strip().startswith(f"{key}: #"), f"{key} has an inline comment"


class TestDispatchInput:
    """The one-run prompt input, with input -> variable -> secret precedence."""

    def _inputs(self) -> dict[str, Any]:
        # PyYAML reads the key `on` as the boolean True (YAML 1.1), so look for
        # either spelling rather than assuming one.
        document = _workflow()
        dispatch = document.get("on") or document.get(True)
        assert isinstance(dispatch, dict)
        values = dispatch["workflow_dispatch"]["inputs"]
        assert isinstance(values, dict)
        return values

    def test_input_exists_and_is_an_optional_string(self) -> None:
        prompt = self._inputs()["ai_summary_prompt"]
        assert prompt["type"] == "string"
        assert prompt["required"] is False
        assert "One-run AI summary instructions" in prompt["description"]

    def test_report_step_prefers_input_then_variable_then_secret(self) -> None:
        prompt = _report_step_env()[PROMPT_KEY]
        assert prompt == (
            "${{ inputs.ai_summary_prompt || vars.AI_SUMMARY_USER_PROMPT"
            " || secrets.AI_SUMMARY_USER_PROMPT }}"
        )

    def test_input_is_referenced_only_in_that_expression(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert raw.count("inputs.ai_summary_prompt") == 1


MEMORY_FLAG = "AI_MEMORY_ENABLED"
MEMORY_GUARD = "${{ secrets.AI_MEMORY_GIST_TOKEN != '' && vars.AI_MEMORY_GIST_ID != '' }}"
MEMORY_STEP_VALUES = {
    "AI_MEMORY_GIST_ID": "${{ vars.AI_MEMORY_GIST_ID }}",
    "AI_MEMORY_GIST_TOKEN": "${{ secrets.AI_MEMORY_GIST_TOKEN }}",
}


class TestMemoryWorkflowGuard:
    """WC-002: the memory flag is an env expression, its settings live on the report step."""

    def test_the_guard_references_the_token_and_the_gist_id(self) -> None:
        expression = _env()[MEMORY_FLAG]

        assert expression == MEMORY_GUARD
        assert "secrets.AI_MEMORY_GIST_TOKEN" in expression
        assert "vars.AI_MEMORY_GIST_ID" in expression

    def test_the_flag_is_never_set_unconditionally(self) -> None:
        flag = _env()[MEMORY_FLAG]

        assert flag not in ("true", "false", "")

    def test_no_if_condition_mentions_the_flag(self) -> None:
        offenders = [
            line for line in _lines() if line.strip().startswith("if:") and MEMORY_FLAG in line
        ]
        assert offenders == []

    def test_both_settings_are_forwarded_on_the_report_step(self) -> None:
        env = _report_step_env()

        for key, expression in MEMORY_STEP_VALUES.items():
            assert env.get(key) == expression, f"{key} is not forwarded on the report step"

    def test_the_settings_never_reach_the_workflow_level_env(self) -> None:
        """The token must not reach checkout or any setup step."""
        env = _env()

        for key in MEMORY_STEP_VALUES:
            assert key not in env

    def test_no_memory_value_is_written_to_dot_env(self) -> None:
        lines = _lines()
        step_start = next(
            index for index, line in enumerate(lines) if "Create .env file from secrets" in line
        )
        step_end = next(
            index
            for index in range(step_start + 1, len(lines))
            if lines[index].strip() == "- name:" or lines[index].strip().startswith("- name:")
        )
        env_step = "\n".join(lines[step_start:step_end])

        assert "AI_MEMORY" not in env_step

    def test_comments_sit_above_the_keys(self) -> None:
        lines = _lines()
        for key in (*MEMORY_STEP_VALUES, MEMORY_FLAG):
            index = next(i for i, line in enumerate(lines) if line.strip().startswith(f"{key}:"))
            assert not lines[index].strip().startswith(f"{key}: #"), f"{key} has an inline comment"
