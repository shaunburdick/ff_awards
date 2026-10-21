"""Static checks on the weekly workflow's AI summary configuration (WC-001)."""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "weekly-report.yml"

GUARD = 'AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != \'\' }}'
PROMPT_KEY = "AI_SUMMARY_USER_PROMPT: |"


def _lines() -> list[str]:
    return WORKFLOW.read_text(encoding="utf-8").splitlines()


class TestWorkflowGuard:
    """FR-007 and WC-001: the flag is an env expression, never an if."""

    def test_guard_is_an_env_expression_on_the_key(self) -> None:
        assert any(line.strip() == GUARD for line in _lines())

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


class TestWorkflowPrompt:
    """FR-008: the committed prompt is a block scalar with comments above it."""

    def test_prompt_is_a_committed_block_scalar(self) -> None:
        assert any(line.strip() == PROMPT_KEY for line in _lines())

    def test_comment_sits_above_the_key_not_inside_the_block(self) -> None:
        lines = _lines()
        key_index = next(
            index for index, line in enumerate(lines) if line.strip() == PROMPT_KEY
        )

        preceding = [line for line in lines[:key_index] if line.strip()]
        assert preceding[-1].strip().startswith("#"), "the explanation belongs above the key"

        index = key_index + 1
        while index < len(lines) and (not lines[index].strip() or lines[index].startswith("    ")):
            stripped = lines[index].strip()
            assert not stripped.startswith("#"), "comments inside a block scalar become prompt text"
            assert stripped == "", "the default prompt must be empty"
            index += 1

    def test_model_is_not_pinned_in_the_workflow(self) -> None:
        """The model comes from the code default or repository settings, not here."""
        assert "AI_SUMMARY_MODEL" not in WORKFLOW.read_text(encoding="utf-8")
