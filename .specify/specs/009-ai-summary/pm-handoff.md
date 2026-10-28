# PM Handoff: AI Commissioner memory (spec 009 amendment)

- Spec: `.specify/specs/009-ai-summary/spec.md` — **v0.26**
- Plan / tasks: `plan.md`, `tasks.md` — **v2.2**, frozen
- Branch: `ai-memory` · Commits: `cb4aac3` (spec/plan/tasks), `84c8733` (Phase A), `7e2517c` (Phase B) · Tree clean, nothing pushed

## Phase

Both phases built and conformance-approved · Next: owner supplies a gist + token, one live run verifies the real API shape, then PR/merge · Blocked: nothing

## Delivered

- **Phase A** — `services/ai_history.py` (week-by-week rank anchored to the printed standings, head-to-head, streak, ±1.0 trend, best/worst week, signed margin) and `services/rankings.py` (one comparator; the console table and the prompt cannot disagree). Digest gains `history`, `overall_standings`, `weekly_extremes`; provenance gains `history_weeks`.
- **Phase B** — `services/ai_memory.py` (archive parse/merge/serialize, gist store with its own injectable transport) and `MemorySession` (status map, warnings, week guard). One gist, one `memory.json`, append-only, whole season in the prompt, two voice rules. Provenance gains `memory_read`, `memory_write`, `memory_weeks`.
- 1106 tests, ruff/format/mypy clean. Memory-off output is byte-identical to the committed Phase-A golden (`tests/fixtures/ai_summary_phase1_golden.json`).

## Owner actions before this is live

1. Create a secret gist and a fine-grained token with **Gists: read and write** only.
2. Repository variable `AI_MEMORY_GIST_ID`, secret `AI_MEMORY_GIST_TOKEN`; the workflow's guard turns memory on when both exist.
3. One live run (LV-005) to confirm the documented API shape — the suite uses fakes, so the real read/patch shape is the only unverified piece.
4. Run the throwaway backfill script once; generating a week and appending are callable outside the CLI, proven by a subprocess test.

## Known follow-up

`services/ai_client.py` has the same error-body read inside `except HTTPError` that Phase B just fixed in the memory store: a provider that resets mid-error-body escapes as a bare `OSError` and turns the FR-006 notice into exit 1. Pre-existing, outside this amendment, wants its own small change with the same guard and a matching fixture.

## User preferences

- A sportscaster with a persona and a running theme, not a data readout; league patterns over self-commentary.
- One 24+ person league split across divisions; the shared headline is what makes them one league.
- Full-season memory in the prompt, no caps, no compaction, single season, accuracy over token count.
- Alliance to simplicity: every extra mechanism asked for was cut once the simpler shape was found. Dislikes process talk and detail that does not change a decision.
