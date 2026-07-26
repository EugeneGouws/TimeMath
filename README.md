# TimeMath

Model-first school-timetable solver. Sixth attempt at this problem — five
prior attempts failed by writing code before the underlying combinatorial
structure was understood. This one gets the model right first (checked
against real data, verified by hand) before any implementation.

See **[docs/PRODUCT.md](docs/PRODUCT.md)** for what "done" looks like,
**[docs/PLAN.md](docs/PLAN.md)** for the build order, and **[CLAUDE.md](CLAUDE.md)**
for the current record of established facts and open questions.

## Status

Phase 0 (normalise) and Phase 1 (bounds) done and validated in Excel. Phase 2
(precolour) is the active coding front, scoped to Grade 12 first. Phases 3–5
are analytically explored only — see [docs/explorations/](docs/explorations/).
Nothing beyond Phase 2 exists as code yet.

## Data policy — no student data in this repo

**Raw student/teacher rosters (`data/`) are git-ignored and must never be
committed.** They contain real names and are sensitive. Student **IDs** are
fine to commit/reference — they're hashed on this machine only and carry no
identifying information on their own — but **names never leave `data/`**.

`Phase01_<year>.xlsx` at the repo root is safe to track: it's a derived
working fixture containing only `Id | Grade | subject codes`, no names.

If you're setting this up fresh: put `Students<year>.xlsx` and
`TT<year>.xlsx` under `data/<year>/` locally — `.gitignore` already excludes
that directory.

## Setup

Python 3.11, dependency: `openpyxl`.

```
pip install openpyxl
```

## Working mode

Guided coding: the project owner writes all code; Claude coaches (see
`.claude/skills/guided-coding`). Token economy conventions for Claude
sessions are in [docs/TOKENS.md](docs/TOKENS.md).
