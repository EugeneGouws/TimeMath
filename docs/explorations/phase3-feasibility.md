# Phase 3 feasibility — column + student assignment

**Status: EXPLORED, NOT IMPLEMENTED.** Source: chat sessions with throwaway
CP-SAT scripts against 2025/2026 workbook data.

## Question

Is the Phase 3 model sound as specified, and is CP-SAT fast enough?

## Findings

1. **The original PLAN.md §5 model was structurally infeasible as written.**
It performed basket SDR over *subjects* — impossible once any subject runs
multiple sections. The working model assigns **students to sections**
(`y[student, section]`) with per-student all-different over assigned sections'
columns. PLAN.md §5 has been rewritten to this form.
2. **Speed is a non-issue:** the corrected model solves feasibility in
**< 1.2 s for every grade-year combination**. Phase 3 is not the bottleneck.
3. **SDR soundness boundary** (also recorded in CLAUDE.md): subject-level
all-different is sound only for floor=1 subjects; multi-section subjects
contribute to Hall counting only. This is what broke the original
formulation.
4. A forward-checking domain tracker in Phase 2 would re-implement CP-SAT's
own propagation — use assumption literals in Phase 3 instead.

## Caveat

These runs used provisional teacher data and hand-prepared inputs. Timings
validate direction only; re-measure with the rebuilt qualification files.
