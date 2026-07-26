# Warm-starting from an existing timetable — rejected

**Status: EXPLORED, REJECTED.** Source: chat sessions, measured on 2025 vs
2026 JSON.

## Question

Can last year's timetable seed this year's solve?

## Answer: no.

* Year-to-year **cell-placement Jaccard similarity is only ~0.19** despite the
structure (columns, bands, M-values) being stable. The solution surface moves
almost completely even when the problem barely does.
* A warm start **biases toward last year's teacher count** — the very number
we are trying to minimise. Seeding with the incumbent makes the solver
defend it.

Also recorded as CLAUDE.md correction 9. If hints are wanted, they must come
from Phase 2's own heuristic placements (`AddHint`), never from a prior year.
