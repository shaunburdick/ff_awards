# PM Handoff: AI Commissioner memory (spec 009 amendment)

- Spec: `.specify/specs/009-ai-summary/spec.md` — **v0.29**
- Plan / tasks: `plan.md`, `tasks.md` — **v2.5**
- Ledger: `challenge-ledger.md`
- Branch: `ai-memory`, **7 commits, pushed, PR https://github.com/shaunburdick/ff_awards/pull/13**
- Tree: clean apart from this file's refresh

## State

Both phases are built, reviewed and on the branch. The feature is live against the owner's real gist and has been exercised end to end.

- **Phase A** — season history per league and the league-wide view in the digest. `services/ai_history.py`, `services/rankings.py`.
- **Phase B** — the memory log: one gist, one `memory.json`, one entry per week holding the published summary verbatim, read before generation, appended after. `services/ai_memory.py`, `MemorySession`.
- **Read-only mode** — `AI_MEMORY_WRITE` (default true) and the `update_memory` dispatch input: reads and uses memory, writes nothing, records `skipped`. Added so a test dispatch to the owner's own address does not advance the archive.
- 1141 tests; ruff, format and mypy clean. Memory-off output is byte-identical to the committed Phase-A golden.

## What has been proven against the real thing

- The gist holds **weeks 1–7**, one entry each, 21.7 KB, reading back as `ok` with no warnings.
- Weeks 6 and 7 are the takes the league actually received; weeks 1–5 were reconstructed with a throwaway script in `/tmp` (never committed) that rebuilt each week's records from games up to that week, so a week-1 take could not quote a week-7 record.
- A week-7 dry run with weeks 1–6 behind it produced visible continuity — "six weeks of mockery", the Belt arc, the driveway motif — with no figures contradicting the week's data.

## Before it runs for real on Tuesday

1. **CI does not have the credentials yet.** `.env` covers local runs only. Add repository variable `AI_MEMORY_GIST_ID` and secret `AI_MEMORY_GIST_TOKEN` (fine-grained, Gists read and write only); the workflow's guard enables memory when both exist.
2. Confirm the scheduled run writes week 8 and leaves weeks 1–7 untouched.
3. The unproven piece is a scheduled CI run against the live gist — everything so far used the local `.env`.

## Owner preferences

- A sportscaster with a persona and a running theme; league patterns over self-commentary.
- One 24+ person league split across divisions; the shared headline is what makes them one league.
- Full season in the prompt, no caps, no compaction, single season, accuracy over token count.
- Allergic to bloat and to process talk. Every mechanism he did not ask for was cut; do not restore one.
