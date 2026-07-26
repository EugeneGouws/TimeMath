# PRODUCT.md — Repeatable Timetable Solver

## Desired outcome
Given, for any school/year:

1. **Students + their subject choices** — raw roster, one row per student
2. **Teachers + their qualification pools** — what each *could* teach, per grade
3. **The shape of the timetable** — columns, periods per column
4. **Caps** — class size, teacher load (school default plus per-teacher overrides)

...produce a feasible timetable with **minimal teacher usage**, in minimal time
and with minimal manual effort, on a **repeatable** basis — new intake, new
staff, new subject list, same pipeline, no re-derivation from scratch.

## Why this doc exists
Five prior attempts at automating this failed. The working hypothesis is that
implementation was attempted before the underlying structure was understood.
This project gets the mathematical model right first — variables, constraints,
bounds, what is precoloured versus solved — so the implementation is a
straightforward encoding of an already-proven model, not another exploratory
rewrite.

## Definition of done
- A CP-SAT formulation that takes the four inputs above and either returns a
  feasible timetable or a **specific, actionable reason** it cannot
  (understaffed subject, oversized basket, saturated teacher) — never a silent
  failure. "Actionable" is a testable claim: assert on the named culprit, not
  just on the infeasible status.
- Every produced timetable passes an **independent verifier** that shares no
  code with the solver.
- Validated end-to-end against at least two real years, not just toy examples.
- The path from raw data to model inputs — baskets, pools, precoloured skeleton
  — is itself repeatable and tested, not hand-curated per school.

## Scope
- All grades, since teacher exclusivity couples them and they cannot be solved
  independently. Senior grades are the proving ground and are done first.
- Implementation is now in scope; the model is settled enough to encode.

## The pipeline (end-to-end mental model)

Where every decision lives, and in what order. Sections are created early by
arithmetic; the hard decisions are columns (Phase 3) and teachers (Phase 4);
Phase 2 exists to make Phase 3 fail loudly-early instead of silently-late.

```
PHASE 0  Read + validate
         roster → students, baskets, subject-grade existence
         TT<year> → qualification pools
         conversion table; unknown codes hard-fail

PHASE 1  Counting + bounds
         enrolments → sections created here (floors: ceil(n/cap))
         lower bounds: max basket size, clique
         verdict: "not yet proven infeasible" or named blocker
         (a verdict over zero students in scope is an error, never a pass)

EXCEPTIONS  oversized baskets → P1–P4 / quarantine
            incomplete records → report loudly, drop from model

PHASE 2  Feasibility screen + domain reduction
         pin universal block (EN column + MA/PE/LO band)
         basket SDR: prune which columns each section can take
         output: shrunk domains, or named Hall violator
         — nothing is placed yet; only impossibilities are removed

PHASE 3  Column assignment
         each section → one column, inside Phase 2 domains
         spread is costed, not merely bounded
         student→section partition lives here: trivial for floor=1;
         for floor≥2 it is entangled with column choice (post-hoc vs
         in-model is an open question, see CLAUDE.md)

PHASE 4  Teacher assignment
         each section → one qualified teacher
         cross-grade exclusivity is a hard constraint here
         objective: fewest teachers / fewest lessons
         coupled with Phase 3 — may iterate 3↔4

PHASE 5  Output
         full grid per grade, student, teacher
         reinstate quarantined students (else they silently get nothing)
```

Corrections this model bakes in: the unit placed in a column is a *section*,
not a subject (a multi-section subject may span columns); teacher
*qualifications* enter early (pools, exclusivity) even though teacher
*identity per section* is decided last.

## Non-goals (for now)
- UI, deployment, or productised tooling. Command-line and data files are enough.
- Optimising anything beyond teacher count and manual effort — room allocation,
  teacher preferences, and period-of-day quality are out until the core solves.

See **CLAUDE.md** for established facts and corrections, **PLAN.md** for the
build order.
