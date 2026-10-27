# PM Handoff: AI Commissioner memory (spec 009 amendment)

- Spec: `.specify/specs/009-ai-summary/spec.md` — **v0.25**
- Plan / tasks: `.specify/specs/009-ai-summary/plan.md`, `tasks.md` — **v2.1** (Phase A 5 tasks, Phase B 9)
- Ledger: `.specify/specs/009-ai-summary/challenge-ledger.md`
- Constitution: `.specify/memory/constitution.md`
- Branch: `ai-memory` (worktree). Modified: spec.md, plan.md, tasks.md, challenge-ledger.md; untracked: pm-handoff.md. No code written, nothing committed.

## Phase

Gate 2 verification in progress · Completed: intake, ideation, spec (v0.15 → v0.25 through three Gate 1 rounds), plan + tasks, Gate 2 fixes · Next: owner approval, then Phase A build · Blocked: none

## What the feature is

**Phase A — prompt input, no store (5 tasks).** Season history per league (rank by week, head-to-head, streak, trend, best/worst week, signed average margin) and the league-wide view (every team across divisions in one ranking that copies the console's order; highest/lowest score, biggest margin, closest game across all divisions). Both derive from games the report already loads. Adds `provenance.history_weeks`.

**Phase B — the memory log (9 tasks).** One gist, one file `memory.json`, one entry per week holding that week's published summary verbatim (headline, season note, every league's paragraphs and bullets). Read before generation, append after, whole archive in the prompt as "what you published", two prompt rules: quote it as your own words rather than league fact, and continue a bit rather than repeat it. Off by default; off is byte-identical to the Phase-A golden. Adds `memory_read`, `memory_write`, `memory_weeks`.

## Decisions the owner made (do not reopen)

- Memory is a log of what was published — nothing new is generated for it, no model-authored memory field.
- One gist = one commissioner setup; one file; append-only; same-week replacement is the only mutation. This is what keeps the 24+ person league from crossing divisions.
- Full season in the prompt, no caps, no compaction, no rollover, single season only. Accuracy over token count; cost is a few cents a season.
- Backfill is a throwaway local script the owner runs once, not a product feature — but generating a week and appending must be callable outside the CLI.
- The shared headline exists because one 24+ person league was split across divisions; it needs cross-division material, which is what the league-wide view provides.
- Two rules carry the voice: quotation (past takes are its own words, the current data is truth) and continue-don't-repeat (the owner's explicit ask).
- Stance/persona schemas, per-league files, aliasing, `source` markers, caps and season summaries were all designed and deleted. Do not restore them.

## Next

1. Gate 2 verification closes (challenger confirms B1–B4, S1–S10, cuts, spec wordings).
2. Owner approves; Phase A goes to one `modern-architect-engineer` pass, then a conformance check.
3. Phase B after a real Phase-A report is read; gist + fine-grained PAT (Gists read/write only) set up before its first live run.
4. The owner's backfill script runs once after Phase B lands.

## User preferences

- Wants a sportscaster with a persona and a running theme, not a data readout; league patterns over the AI talking about itself.
- Wants full-season context and voice continuity; team data outside the repo, in a gist.
- Irritated by over-engineering and by detail that does not change a decision. Talk about the thing, not about the process.
