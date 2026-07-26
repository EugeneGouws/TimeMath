# CLAUDE.md — Timetable Solver (model-first project)

## Mode of work

Model-first. Five prior attempts failed by building before the structure was
understood, so the rule is: **nothing goes into code until it has been checked
against real data and is small enough to verify by hand.**

Companion docs: **PRODUCT.md** (what done looks like) and **PLAN.md** (how to
build it). This file is the record of what is *established* and what is *open*.

## Provenance of every fact below

Three tiers. Do not conflate them.

* **Solid** — derived from raw student rosters (`Students<year>.xlsx`, or the
  `Roster` sheet of `Phase01_<year>.xlsx`). Student baskets, enrolments,
  subject-grade existence, basket-size bounds, section floors. Ground truth.
* **Solid (new)** — derived from `TT<year>.xlsx`, the rebuilt teacher file in
  qualification format, generated from the accdb source. Qualification pools
  are now capability statements and can be built on.
* **Provisional** — anything still traceable to `Teachers2025.xlsx` (2025
  *actual assignments*, not qualifications). **The `Pool size` and `2025 actual
  sections` columns in both `Phase01_*.xlsx` workbooks are still pre-filled from
  this file** and have not been regenerated from `TT<year>.xlsx`. Section counts
  and the precolouring anchor derived from them remain provisional.

## The timetable shape

* 8 columns `A`–`H`, 7 periods each = **56 cells**, plus `P1`–`P4` (4 extra
  fields in the source; treated as out-of-timetable, and the escape hatch for
  oversized baskets).
* A column is a school-wide time slot. Each grade allocates its own 8 columns
  independently; **the only thing linking grades is teacher exclusivity.**
* `getM(subject, grade)` gives periods per cycle. Most senior subjects are
  **M=7 — one class fills an entire column.** For those, assigning a column *is*
  the complete scheduling decision.
  Sub-column subjects: `LO`=2, `PE`=2, `RD`/`RDI`=1, options and `TE`/`EM`/`EMS`=4.
  Junior overrides at grades 8–9: `GE`/`HI`/`SC`/`LS`/`LO`=3, `DR`/`ED`/`EM`=4.
* **`MA_S` = 10 in every year checked (2025 and 2026). `ML` = 7.**
* Compulsory block = **3 columns**:
  * `EN` (7) fills one column alone.
  * `MA`(10) + `PE`(2) + `LO`(2) = **14 = two columns**, packed as one composite
    band. `ML`(7) runs parallel inside the band, filling one of its two columns;
    ML students therefore carry 3 slack cells.
  * **`PE` and `LO` are not confined to one column of the band.** Verified on
    2026 Gr11: an MA student reads `A = MA×6 + PE×1`, `G = MA×4 + LO×2 + PE×1`.
    The band is a 2-column, 14-cell packing region, not two separately placed
    columns. Derive band width as `ceil(sum(M_band) / periods_per_column)` so the
    shape is a parameter, not a fork.
* Leaves **5 columns for choice subjects.**
* `_CAP` = 25 (`Constants.h`).

## Corrections to earlier beliefs — read before trusting old notes

1. **Pool size caps *simultaneous* sections, not total sections.** A teacher can
   cover several sections of the same subject in *different* columns, because
   columns are time slots. Confirmed: `CAREW` was the only BS_12 teacher yet ran
   3 BS_12 classes. The CP-SAT constraint `Σ_c x[subject,column] ≤ pool` used
   earlier in this project is **wrong** and any result from it is void.
2. **`MA_S` = 10, in both 2025 and 2026** — not 7, and not year-varying. It is
   deliberately mixed with `PE` and `LO` to pack 14 lessons over 2 columns. This
   is the source of most senior-grade difficulty, and of the only Section that
   spans more than one column.
3. **The `m` field in the timetable JSON is stale** (~86 sections per file) and
   has now caused a wrong conclusion twice. It reported MA=7 for 2025 while the
   *placements* in the same file showed 10 cells. **Never read M from the JSON
   `m` field.** Authoritative M comes from `getM` / the M table, and can be
   independently recovered by counting cells per section in `student_slots`.
   Any earlier claim sourced from `m` — including "EN junior went 7→8 in 2026" —
   is retracted pending re-derivation from placements.
4. **Teacher "pool" numbers in the original planning table were whole-school**,
   not per-grade — roughly 3× the real per-grade figure. Column assignments
   solved against them were solved against fictitious headroom.

## Established structure

* **The binding constraint is basket-level SDR** (System of Distinct
  Representatives), not pairwise subject conflict. Two subjects clash only if
  some *actual basket* contains both. A basket of *k* subjects needs *k* distinct
  columns; by Hall's theorem this is satisfiable iff every sub-collection of *j*
  subjects has ≥ *j* columns available between them.
* **Subject-level all-different is sound only for singleton-section subjects.**
  If a subject has ≥2 sections they may legitimately occupy different columns
  with students distributed between them. Forcing subject-level distinctness on
  a multi-section subject *removes real solutions* — an unsound pin, exactly the
  PLAN.md §4 trap. Therefore, per basket:
  * subjects with **floor = 1** → genuine pairwise all-different → sound domain
    reduction;
  * subjects with **floor ≥ 2** → contribute to the Hall *counting* check only,
    never to pairwise elimination.
  Implement as one bipartite matching (subjects → columns) per basket. Success
  means feasible-so-far; failure yields the Hall violator, which **is** the
  actionable reason required by PLAN.md §2.4 and PRODUCT.md.
* **The universal block is forced by the column budget, not conventional.**
  Max basket 5 needs 5 choice columns; `EN` is universal so needs a column
  disjoint from all of them; the band needs 2. 5 + 1 + 2 = 8 exactly — **zero
  slack**. `EN` therefore cannot split and the band cannot spill. Only *which*
  columns is free, and that is pure symmetry. Pinning it is sound.
* **Two independent lower bounds on column count**: max clique in the
  co-occurrence graph, and **max basket size** (a basket of size *k* is itself a
  *k*-clique, so it is always a valid clique bound and is computable in Excel).
  A single 6-subject basket forced 6 columns regardless of clique structure or
  staffing — confirmed by CP-SAT with pool caps removed entirely.
* **Oversized baskets are exceptions, not grid constraints.** One student should
  never size the whole grade's grid; quarantine and handle manually.
* **Plain feasibility search over-spreads subjects.** Given no cost on spread,
  the solver fragmented a 15-student subject across 3 columns. Spread must be
  *costed* in the objective, not merely bounded. Cost should focus on minimising
  the number of lessons teachers teach.
* **Grades cannot be solved independently.** 39 of 46 teachers work across more
  than one senior grade, and the tightest-loaded ones are exactly the
  single-teacher subjects. (Provisional — from assignment data.)

## Grade-at-a-time scoping (current working mode)

Solving one grade at a time, starting with **Grade 12**. What this does and does
not cost:

* **Sound per grade, no loss:** section materialisation at floor, universal-block
  placement, basket SDR propagation, all Phase 1 bounds, named failure. Baskets
  never cross grades.
* **Breaks per grade:** teacher exclusivity only — and that is already the part
  gated on qualification data.
* **Warning:** "grade-aware conventions so pinned subjects don't clash by design"
  is a *heuristic placement*. It may be a CP-SAT **hint** and a symmetry-breaking
  order, never a hard constraint. Cross-grade teacher exclusivity must be a real
  constraint in Phase 3.
* **Symmetry is spent once.** Placing the universal block (2.1) consumes the free
  relabelling; the anchor-teacher pin (2.2) is then free only on the *residual*
  columns. Pin the anchor's choice sections into the residual; never touch its
  compulsory-block sections.

## Subject-grade existence (solid, stable across 2025 and 2026)

* **Senior only (10–12)**: AC, BS, CA/CAT, DA, DR, ED, FR, IT, ML, MU, VA
* **Junior only (8–9)**: EMS, OA, ODA/DA, ODR/OD, OE/ED, OF/FR, OM/MU, TE, RD/RDI
* **All grades (8–12)**: AF, EN, GE, HI, LO, LS, MA, PE, SC/NS (for juniors), ZU

Derive this table from the roster (subject X exists in grade g iff some student
in grade g takes X) — never hand-maintain it.

## Subject code drift (real, must be handled)

`CAT`→`CA`, `OD`→`ODR`, `RDI`→`RD` between 2025 and 2026. `getM` currently ends
with `SUBJECT_M.value(subjectCode, 7)`, so an unknown code **silently returns 7**
and a renamed subject gets a plausible wrong M with no complaint. A conversion
table plus hard validation is mandatory — see PLAN.md.

**Note:** the `Phase01_2025` and `Phase01_2026` rosters carry **identical code
sets** (both use `CAT`), so the conversion table is currently untested against
them. The drift lives in the accdb/JSON sources, not in these workbooks.

## Teacher file format — `TT<year>.xlsx` (built, from accdb)

```
Teacherid | Teacher Code | sua | sub | suc | sud | sue |
TSurname | TTitle | TInitials | TClassroom | TTutorclass | TGradecoord | Thouse
```

* Qualifications live in `sua`–`sue`. **Read all `su*` columns dynamically**, do
  not hardcode a–e; assert no teacher fills every slot (a full row suggests the
  source truncated a further qualification).
* **A bare code means grades 8–12.** Confirmed convention. Consequence: pools are
  broad, so **singleton pools will be rare**, and both the Phase 2 anchor ranking
  (2.2) and teacher-exclusivity propagation (2.3) may produce little or nothing
  at single-grade scope. This is expected, not a bug. Over-broad qualifications
  do not fail loudly — they fail *flatteringly*, by making the minimum teacher
  count look better than it is.
* **`LIB`, `ST`, `LAB` are non-teaching codes.** Declare them in the conversion
  table as canonical codes mapping to null. Do **not** filter them silently — a
  skip reintroduces the exact silent-default bug that `SUBJECT_M.value(code, 7)`
  caused. Declared codes are ignored deliberately; unknown codes must still fail.

Token expansion, with **union across repeated tokens for the same subject**:

```
"SC"    -> {8,9,10,11,12}      "SC_S"  -> {10,11,12}
"SC_J"  -> {8,9}               "SC_11" -> {11}

qualified(t, subj, gr) <=> gr in UNION(tokenGrades(tok) for tok of subj)
                                 INTERSECT gradesWhereSubjectExists(subj)
```

Suffixes are only meaningful for the 10 all-grade subjects; the other 23 are
grade-locked by the existence table, so a bare code is unambiguous.

**Semantic change to be aware of:** in the old file, repeated tokens meant
*number of classes taught*. In the new file a token is a *capability* and says
nothing about count. This is correct for a constructive solver — section counts
come from Phase 1 — but it removes the only independent cross-check on section
counts. Keep one legacy-format year as a validation fixture.

## Exception rule (now explicit and testable — was an open question)

Two distinct rules, not one. Both were previously collapsed into "the ones we
noticed by eye".

| Rule | Test | Action | 2025 Gr12 |
|-|-|-|-|
| **Oversized basket** | `\|basket\| > free column count` | Quarantine, or move one subject out-of-timetable (`P1`–`P4`) | id 69 (BS DA DR GE SC ZU, 6) |
| **Incomplete record** | missing a universal subject, or basket below grade norm | Report loudly | id 7 (3 choice), id 44 (2 choice, **no EN at all**) |

**Only the oversized rule affects feasibility.** A 2- or 3-subject basket is a
subset constraint and constrains nothing; undersized students are a data-quality
signal, not a grid problem.

Applied for the current run: ids 7 and 44 removed from the roster; id 69's sixth
subject moved out-of-timetable, bringing its basket to 5.

**Consequence to track:** students removed from the model still need a timetable.
They must be reinstated at Phase 5 output or they silently receive nothing.

## Regression fixtures (solid — assert these)

Choice subjects only, excluding EN/LO/PE/MA/ML.

**2025** (`Phase01_2025.xlsx`, after removing ids 7 and 44):

|Grade|Students|Distinct baskets|Max basket|Size distribution|
|-|-|-|-|-|
|10|89|65|5|4:20, 5:69|
|11|77|59|5|3:1, 4:45, 5:31|
|12|98|—|5 (6 raw, before id 69's OOT move)|4:80, 5:17 + id 69|

Raw 2025 Gr12 before any exception handling: 100 students, 75 baskets, max 6,
distribution `{2:1, 3:1, 4:80, 5:17, 6:1}`. Test both — exception handling is
exactly what turns infeasible into feasible.

**Note (2026-07-26):** `Phase01_2025.xlsx` has since been edited in place to
remove ids 7 and 44 — the workbook itself now reflects the post-exception
state (Gr12 = 98), not the raw 100. `tests/test_roster.py::test_2025` asserts
98 directly against the live file. The "raw 100" figure above is now historical
only; if the raw file is needed again (e.g. to test the exception-handling
code path itself once written), restore from git history rather than
re-deriving by hand.

**2026** (`Phase01_2026.xlsx`): Gr10 = 99, Gr11 = 90, Gr12 = 81 students.

**Grade 12 2026 section floors at cap 25** (choice block, 22 sections):

| Floor | Subjects |
|-|-|
| 1 (singleton — SDR applies soundly) | AC 19, CAT 21, DA 9, DR 19, **ED 25**, FR 5, GE 15, HI 13, IT 13, MU 3, VA 8, ZU 19 |
| ≥2 (Hall counting only) | AF 58→3, BS 34→2, LS 53→3, SC 42→2 |

Universal: EN 81→4, LO 80→4, PE 80→4, MA 54→3, ML 28→2.

**`ED` sits at exactly cap** (25 of 25). One additional enrolment splits it and
moves it out of the singleton set, weakening the SDR propagator. Assert on this.

## Known traps in the tooling

* **`Phase01_2025.xlsx` silently returns zeros.** `Roster!B` stores Grade as
  *text* (`'12'`); `Config!B2` stores it as the *number* `12`. Excel treats these
  as unequal, so `In scope` is 0 for every row, every subject reports "not
  offered this grade", and `Bounds` reports **"Not yet proven infeasible —
  proceed to Phase 2"** on an empty set. `Phase01_2026.xlsx` stores Grade as an
  integer and works.
  Fixes: type-coerce the comparison, **and** add a Bounds assertion that
  students-in-scope is non-zero before any verdict is emitted. A verdict computed
  over zero students must be an error, never a pass.
* This is the canonical instance of PLAN.md §8's "the dangerous failure is a
  plausible wrong answer, not a crash." Any future screen must refuse to return
  a verdict on an empty scope.

## Open questions

* What is the true minimum teacher count, and when is the max-of-bounds tight?
  Candidate bounds: concurrency, pooled load, Hall-type covering over
  qualification pools, colouring, **basket size**, and **per-teacher column
  demand** (an M=7 class consumes a whole column, so a teacher's count of M=7
  classes is a direct demand on distinct columns).
* Is the marginal-impact greedy for distributing leftover teachers provably
  near-optimal, or arbitrarily bad?
* Phase 3 and Phase 4 are sequential but coupled — a column assignment cheap in
  section count can force more distinct teachers than an alternative. Since
  minimal teacher usage is the product goal, this ordering optimises a proxy.
  Unresolved: fold teacher variables into Phase 3, or iterate 3↔4.
* **Student-to-section assignment is undecided at Phase 2.** For a subject with
  floor ≥ 2, which students land in which parallel section is itself a decision,
  and it interacts with basket SDR. Phase 2 handles this by relaxing to the Hall
  counting check; whether Phase 3 needs explicit student-section variables, or
  whether a post-hoc assignment always succeeds, is unresolved.
* Pool sizes in both Phase01 workbooks still come from `Teachers2025.xlsx`.
  Regenerate from `TT<year>.xlsx` before trusting any staffing verdict.

## Python implementation design (agreed 2026-07-25; `roster.py` now under way)

* Two loader modules: `roster.py` and `tt_loader.py` (`tt_loader.py` not yet
  started). The existence table is built in `roster.py` and passed into
  `tt_loader.py`, where it (a) clamps bare qualification tokens to grades
  where the subject actually exists and (b) makes unknown codes detectable
  (hard-fail).
* `roster.py` API: `parse_student(path) -> list[Student]` (note: singular
  `parse_student`, not `parse_students` as originally named) with
  `Student = @dataclass(frozen=True)(id: int, grade: int, subjects:
  frozenset[str])`, plus `existence`, `enrolment`, `floors(cap=25)`, `baskets`
  (choice-only, excludes EN/LO/PE/MA/ML).
* `Phase01_2026.xlsx` Roster sheet layout (Solid, observed): wide format,
  headers `Id | Grade | In scope | S1..S9`, one row per student, blank S-cells
  allowed. Parse rules agreed: **ignore the `In scope` column** (recompute
  scope from Grade — it is the formula that silently zeroed in 2025); read
  `S*` columns dynamically; coerce Grade with `int()` and let it raise;
  normalise codes (`strip().upper()`); duplicate subject in a row → raise.
  Also: skip rows where `Id` is blank (trailing padding rows in the sheet's
  used range) — hit this as a real bug parsing `Phase01_2025.xlsx`.
* Validation fixtures for first run: Gr12 2026 = 81 students, ED enrolment
  = 25 exactly.
* `constants.py` added, holds `CLASS_CAP = 25` (the doc's `_CAP`).
* End-to-end pipeline (phases 0–5, where sections/partition/teachers live) is
  now written out in **PRODUCT.md**.

## Current state

Phase 0 and Phase 1 are done and validated in Excel across Gr10–12 for both
years (2025 workbook pending the grade-type fix above). `TT<year>.xlsx` is built
in qualification format. The exception rule is explicit. Phase 2 is designed and
**unblocked** at single-grade scope; starting with Grade 12.

Python work in progress (PyCharm, Python 3.11, venv; user writes all code —
guided-coding mode). Done and verified against fixtures:
* `roster.py`: `Student` dataclass, `parse_student(path)`, `existence(students)`.
* `tests/test_roster.py`: fixture tests for `parse_student` on both
  `Phase01_2026.xlsx` (99/90/81) and `Phase01_2025.xlsx` (89/77/98).

Next concrete steps, in order:
1. **Consolidate `solver-docs/` into `docs/`** — user has been brainstorming
   in a separate `solver-docs/` folder; fold it into `docs/` so `docs/` becomes
   the single LLM-readable wiki of record for all attempts and ideas on this
   project (not just the current approach). Do this before adding more new
   docs elsewhere.
2. **Git remote/sharing setup** — get this repo onto a shared source (e.g.
   GitHub) so this CLI session ("gremlin"), and the user's claude.ai Projects
   session ("claude"), both read from the same repo/docs instead of drifting.
   Prompt the user for their preferred remote/hosting choice; do not assume
   GitHub vs another host.
3. Finish `roster.py`: `floors(students, grade, cap=CLASS_CAP)` — signature
   and imports (`math`, `constants as C`) are in place, body not yet written.
4. `enrolment` and `baskets` in `roster.py` (agreed API, not started).
5. `sections.py` (Section materialisation, 2.0) — needs `floors` + an M-value
   table/function (`getM`), neither written yet.
6. `tt_loader.py` (teacher qualifications) — needs `existence` from step above;
   no code yet.

Remaining Phase 2 dependency: regenerate workbook pool sizes from `TT<year>.xlsx`
before the anchor ranking (2.2) means anything.

## Working mode

Guided coding: the user writes all project code; Claude coaches (see
`.claude/skills/guided-coding`). `tests/` is reserved for real tests only —
Claude does not drop debug/check scripts there. For quick debug output, Claude
gives print-line snippets inline for the user to paste into the module they're
working on. Claude should prompt the user when a point in the work looks like
a good place to add a real test to `tests/`, rather than writing one
unprompted. Token economy rules in `docs/TOKENS.md` are standing policy:
surgical reads, no subagents or heavy skills unless asked, `/handoff` at task
boundaries before `/clear` or model switches.