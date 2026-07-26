# CLAUDE.md — Timetable Solver (model-first project)

## Mode of work

Model-first. Five prior attempts failed by building before the structure was
understood, so the rule is: **nothing goes into code until it has been checked
against real data and is small enough to verify by hand.**

Companion docs: **PRODUCT.md** (what done looks like) and **PLAN.md** (how to
build it). Analytical deep-dives live in **docs/explorations/** — each is
flagged EXPLORED, NOT IMPLEMENTED. This file is the record of what is
*established* and what is *open*. **A fact is not established until it is
committed here.** Chat-side memory is scratch; this file is law.

## Relationship to other projects

**TimeEduSuite (C++/Qt: TimeEditor, TimeVerify, TimeView, TimePyBling) is a
separate, ongoing production track.** This project is a fresh, model-first
attack on the same problem with different tools (Python + OR-Tools CP-SAT) and
deliberately does not reference the suite's code or schemas. The only import is
the *concept* of `ClashDetector` as an independent verifier sharing no code
with the solver. Do not pull suite context into this project.

## Current state (2026-07)

* **Coding front: Phase 2** (precolour). Phase 0/1 done and validated in Excel
  (`Phase01_2026.xlsx`) across Gr10–12 for both years.
* **Phases 3–5 have been explored analytically in chat** to validate soundness
  — CP-SAT timings, model shape, repair strategy. See docs/explorations/.
  **Nothing beyond Phase 2 exists as code.** Do not treat exploration results
  as implemented behaviour.
* Teacher qualification files (`TT<year>.xlsx`) are being rebuilt/verified;
  same-surname teachers have been split (see corrections §7–8 below).

## Provenance of every fact below

Two tiers. Do not conflate them.

* **Solid** — derived from `Students2025.xlsx` / `Students.xlsx` (raw student
rosters). Student baskets, enrolments, subject-grade existence, basket-size
bounds. These are ground truth.
* **Provisional** — derived from `Teachers2025.xlsx`, which records *2025 actual
assignments*, not qualifications. Everything about teacher pools, section
counts and the precolouring anchor is provisional and **will change** when the
file is rebuilt in the new qualification format. Do not build on it.

## The timetable shape

* 8 columns `A`–`H`, 7 periods each = **56 cells**, plus `P1`–`P4` (4 extra
fields in the source; treated as out-of-timetable).
* A column is a school-wide time slot. Each grade allocates its own 8 columns
independently; **the only thing linking grades is teacher exclusivity** — and
this must remain a real constraint in Phase 3, not a design convention.
* `getM(subject, grade)` gives periods per cycle. Most senior subjects are
**M=7 — one class fills an entire column.** This is the key simplification:
for senior subjects, assigning a column *is* the complete scheduling decision.
Sub-column subjects: `LO`=2, `PE`=2, `RD`/`RDI`=1, options and `TE`/`EM`/`EMS`=4.
Junior overrides at grades 8–9: `GE`/`HI`/`SC`/`LS`/`LO`=3, `DR`/`ED`/`EM`=4.
* **`MA` = 10 in both 2025 and 2026.** The stale `m` field in the JSON read 7 —
a confirmed trap. Do not revert.
* Compulsory block = 3 columns: `EN` fills one (pinned to column A); the
**band** MA(10)+PE(2)+LO(2) = 14 cells across two columns (B–C), with ML(7)
running parallel — ML learners get 3 free slots spread over the band. Band
width formula: `ceil(ΣM_band / 7)`.
* 8 columns = 1 EN + 2 band + 5 choice — **zero slack**.
* `_CAP` = 25 (`Constants.h`). ED in Grade 12 sits exactly at cap (25/25) —
keep an assertion on it.

## Corrections to earlier beliefs — read before trusting old notes

1. **Pool size caps *simultaneous* sections, not total sections.** A teacher can
cover several sections of the same subject in *different* columns. Confirmed:
`CAREW` was the only BS_12 teacher yet ran 3 BS_12 classes. The constraint
`Σ_c x[subject,column] ≤ pool` is **wrong**; any result from it is void.
2. **`MA` = 10** (see shape section). `ML` = 7.
3. **Teacher "pool" numbers in the original planning table were whole-school**,
not per-grade — roughly 3× the real per-grade figure.
4. **PLAN.md §5 as originally written was structurally infeasible**: it did
basket SDR over *subjects*. The correct model assigns *students to sections*
and requires each student's chosen sections to occupy distinct columns.
PLAN.md has been corrected; if you see the subject-level formulation anywhere,
it is stale.
5. **`Phase01_2025.xlsx` silently returned zeros**: Grade stored as text in
Roster but integer in Config. "Plausible wrong answer, not a crash." Every
verdict needs type-coerced comparison and a non-zero-scope guard before it may
report anything.
6. **Five Grade 10 rows in the 2026 workbook share a duplicate student ID.**
7. **GOVENDER covers three distinct people; WYLIE covers two.** The rebuilt
teacher files split them (GOVENDER_K, GOVENDER_L, WYLIE_C, WYLIE_Z). Legacy
files contain phantom double-bookings until disambiguated.
8. **The 2026 teacher table in the original JSON is a stale copy of 2025's.**
Reconstruct from section keys, never from that table.
9. **Warm-starting from an existing timetable is rejected.** Year-to-year cell
placement Jaccard similarity is only ~0.19 despite structural stability, and a
warm start biases toward the teacher count we are trying to minimise.

## Established structure

* **The binding constraint is basket-level SDR**, not pairwise subject conflict.
Two subjects clash only if some *actual basket* contains both.
* **SDR soundness boundary:** subject-level all-different is sound only for
singleton-section subjects (floor = 1). Multi-section subjects contribute to
Hall counting only.
* **Two independent lower bounds on column count**: max clique in the
co-occurrence graph, and **max basket size** (a basket of size *k* is a
*k*-clique, so always a valid bound, computable in Excel).
* **Oversized baskets are exceptions, not grid constraints.** Quarantine and
handle manually.
* **Plain feasibility search over-spreads subjects.** Spread must be *costed*
in the objective (minimise teacher lesson count), not merely bounded.
* **Grades cannot be solved independently.** 39 of 46 teachers work across
more than one senior grade. (Provisional — from assignment data.)
* **Heuristic placements must be `AddHint` only**, never hard constraints.
* **Anchor-teacher ranking is expected to be weak at Grade 12** — broad
qualification pools defeat singleton-pool forcing. Expected behaviour, not a
bug.

## Subject-grade existence (solid, stable across 2025 and 2026)

* **Senior only (10–12)**: AC, BS, CA/CAT, DA, DR, ED, FR, IT, ML, MU, VA
* **Junior only (8–9)**: EMS, OA, ODA/DA, ODR/OD, OE/ED, OF/FR, OM/MU, TE, RD/RDI
* **All grades (8–12)**: AF, EN, GE, HI, LO, LS, MA, PE, SC/NS(juniors), ZU

Derive this table from the roster — never hand-maintain it.

## Subject code drift (real, must be handled)

`CAT`→`CA`, `OD`→`ODR`, `RDI`→`RD` between 2025 and 2026. `getM` falls back to
`SUBJECT_M.value(subjectCode, 7)`, so an unknown code **silently returns 7**. A
conversion table plus hard validation is mandatory — see PLAN.md.

## Qualification file convention (`TT<year>.xlsx`)

Qualifications read dynamically from the `sua`–`sue` columns. `LIB`, `ST`,
`LAB` map explicitly to null. Bare subject code = grades 8–12. Token expansion
with **union across repeated tokens for the same subject**:

```
"SC"    -> {8,9,10,11,12}      "SC_S"  -> {10,11,12}
"SC_J"  -> {8,9}               "SC_11" -> {11}

qualified(t, subj, gr) <=> gr in UNION(tokenGrades(tok) for tok of subj)
                                 INTERSECT gradesWhereSubjectExists(subj)
```

Suffixes only matter for the 10 all-grade subjects; the rest are grade-locked
by the existence table.

**Semantic change:** in the old file, repeated tokens meant *number of classes
taught*; in the new file a token is a *capability*. Correct for a constructive
solver, but it removes the only independent cross-check on section counts —
keep one legacy-format year as a validation fixture.

## Exception students (Grade 12, 2025)

Student ids **7 and 44 removed from the roster; id 69's sixth subject moved
out-of-timetable.** All three **must be reinstated at Phase 5 output** or they
silently receive no timetable. The selection rule is still "noticed by eye" —
it must become explicit and testable.

## Regression fixtures (assert these — but see verification note)

Choice subjects only, excluding EN/LO/PE/MA/ML. Grade 12 excludes the three
manual-exception students.

|Grade|Students|Distinct baskets|Max basket|Size distribution|
|-|-|-|-|-|
|10|89|65|5|4:20, 5:69|
|11|77|59|5|3:1, 4:45, 5:31|
|12|97|72|5|4:80, 5:17|

> **VERIFY:** the Grade 12 row is known to be **off by one** (flagged in chat,
> never corrected here). Re-derive from the roster before asserting on it.

Grade 12 max basket is **5 clean, 6 with exceptions included** — test both.

## Open questions

* True minimum teacher count; when is the max-of-bounds tight? Candidate
bounds: concurrency, pooled load, Hall-type covering, colouring, basket size,
per-teacher column demand.
* Is the marginal-impact greedy for leftover teachers provably near-optimal?
* Phase 3 ↔ Phase 4 coupling: fold teacher variables into Phase 3, or iterate?
Current lean (from exploration): keep sequential, use the **repair model**
reframing — see docs/explorations/repair-model.md.
* The exception-selection rule must become explicit and testable.
