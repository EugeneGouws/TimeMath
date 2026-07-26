# PLAN.md — Implementation Plan

Read **PRODUCT.md** for the goal and **CLAUDE.md** for established facts and
corrections. This file is the build order.

Prime directive: **each phase either produces a strictly smaller problem for the
next, or fails with a specific, named, actionable reason.** A phase that returns
"infeasible" without naming the culprit has not done its job.

Status key: [DONE] validated · [ACTIVE] current coding front ·
[EXPLORED] soundness-checked analytically in chat, not implemented —
see docs/explorations/.

---

## 0. Inputs (the contract with a school)

|File|Contents|
|-|-|
|`Students.xlsx`|One row per student: `Id, Lastname, Firstname, Grade, Reg, Gender, House, S1..Sn`|
|`TT<year>.xlsx`|One row per teacher: `Id, Lastname, MaxLoad (blank=default)`, qualification tokens in `sua`–`sue` columns|
|`Subjects.xlsx`|Canonical code, M per grade, alias list|
|`Shape`|Columns, periods per column, cap — `Constants.h` defaults, overridable|

Rules:

* **Caps and school-wide defaults live in `Constants.h`** (`CLASS_CAP`, `MAX_LOAD`).
* **Per-teacher and per-school data lives in the xlsx**, never in a header. A
per-school header fork breaks the "new school sends me data" goal.
* The **conversion table is data**, not code.
* **Known input traps** (details in CLAUDE.md): Grade-as-text type mismatch in
the 2025 workbook; duplicate Gr10 student IDs in 2026; same-surname teachers
split in rebuilt files; `LIB`/`ST`/`LAB` tokens map to null.

---

## 1. Object model

The entity missing from the previous codebase is `Section`. `Lesson` was a single
cell, so a 7-period class was 7 unrelated objects with no identity — nothing for
a solver to assign.

```cpp
struct Section {                    // THE decision-carrying entity
    QString subCode;                // canonical
    int     gr   = 0;
    int     idx  = 0;               // 0..n-1 parallel groups
    int     m    = 0;               // periods per cycle, from getM
    std::bitset<MAX_STUDENTS> S;    // enrolled students
    int     teacherId = 0;          // 0 = undecided (Phase 4)
    char    column    = 0;          // 0 = unplaced  (Phase 2/3)  <-- decision var
};

struct Basket {                     // Phase 0 output; what SDR constrains
    QStringList subjects;
    QList<int>  students;
    int size() const { return subjects.size(); }
};

struct Qualification {              // expanded from tokens
    QString subCode;
    QSet<int> grades;
};
```

Keep `Student`, `Teacher`, `TimeSlot` broadly as they are. Add `MaxLoad` to
`Teacher`.

**`Lesson` and `TimeSlot` become derived output**, generated only at the end by
expanding placed `Section`s across their column's periods. This inverts the old
flow, where `timeSlot` was inherited and everything was fitted to it.

**Keep `ClashDetector`.** It is the independent verifier and the most valuable
piece of the old codebase — see §8.

---

## 2. Phase 0 — Normalise [DONE — validated in Excel]

1. Parse rosters and teacher file.
2. **Apply the conversion table once, at parse.** Nothing downstream may see an
alias. Validate the table itself first:

   * **functional** — no code maps to two targets
   * **idempotent** — every canonical code maps to itself
   * **closed** — every target exists in the M table and the existence table
3. **Hard validation, fail loudly**: every code appearing in any input must
resolve to a canonical code present in the M table. Report the offending code
and where it appeared. Never default silently.
4. **Derive the subject-grade existence table from the roster.** Do not
hand-maintain.
5. Expand qualification tokens (union semantics, intersected with existence).
6. Derive baskets: distinct choice-subject sets with frequency counts.
7. Split subjects into **universal** (taken by ~all students) and **choice**.
8. **Quarantine exceptions** by an explicit, testable rule — incomplete records
and oversized baskets — *before* modelling.

**Every verdict requires a non-zero-scope guard** (e.g. student count > 0
before reporting "feasible") — the 2025 silent-zeros bug is the cautionary
tale (CLAUDE.md correction 5).

Output: baskets, sections-to-be, qualification map, existence table, exception list.

---

## 3. Phase 1 — Bounds (fail fast) [DONE — validated in Excel]

Compute all, take the max. This is where "infeasible" becomes actionable.

|Bound|Computation|Failure message|
|-|-|-|
|Basket size|max basket size|"Student X takes N subjects; block has C columns"|
|Clique|max clique in co-occurrence graph|"AC/CAT/HI/GE mutually conflict; needs 4 columns"|
|Load|`ceil(students_j / cap)` per subject|"Subject j needs k sections"|
|Teacher column demand|per teacher, count of M=7 classes|"Teacher T needs k distinct columns"|
|Hall / covering|for every subject set S: `Σ sections(S) ≤ |teachers qualified for S|`|names the deficient set|

Max basket size is a valid clique, so it is a sound lower bound even when full
clique-finding is skipped.

Implemented and validated in Excel (`Phase01_2026.xlsx`) — the workbook is the
spec and the fixture. (`Phase01_2025.xlsx` carries the type-mismatch trap.)

---

## 4. Phase 2 — Precolour [ACTIVE]

**The trap:** a pin is a commitment, and an unsound one surfaces 200 decisions
later as an infeasibility unrelated to the real constraints, with no way to walk
it back.

Phase 2 produces **three kinds of output, only two of which may become hard
constraints**:

1. **Symmetry breaks — sound.** Pinning the most column-demanding teacher's
sections to columns A, B, C… loses nothing at the moment no other section is
placed. CP-SAT is excellent at search and bad at symmetry; without this it
re-discovers 8! relabellings of the same timetable.
2. **Domain reductions — sound.** "AC_12 cannot be in column D", derived by
propagation. Never removes a real solution.
3. **Heuristic placements — NOT sound.** These must become CP-SAT **hints**
(`AddHint`), never constraints.

> **Phase 2 shrinks domains and kills symmetry. It does not guess a partial
> solution.**

### Steps

* **2.0 Materialise sections** at the Phase 1 floor, with 8-bit column-domain
bitmasks. Only floor sections may be pinned — beyond-floor is Phase 3.
* **2.1 Place the universal block** per grade: EN → column A; the
MA+ML+PE+LO band → columns B–C via `ceil(ΣM_band / 7)` (see CLAUDE.md shape
section for the band structure).
* **2.2 Pin the anchor teacher.** Rank teachers by column demand (count of M=7
sections, forced only where the qualification pool is a singleton). Pin the
largest — the free symmetry break. Subsequent teachers become domain
reductions, not pins. **Expect the ranking to be weak at Grade 12** (broad
pools) — that is expected behaviour, not failure.
* **2.3 Propagate to fixpoint.** Alternate teacher exclusivity and basket SDR
until nothing changes — but **respect the SDR soundness boundary**
(CLAUDE.md): subject-level all-different only for floor=1 subjects;
multi-section subjects enter Hall counting only. A domain collapsing to one
value is a *derived* pin — sound. Do not build a bespoke forward-checking
tracker beyond this fixpoint — that re-implements CP-SAT's propagation; use
assumption literals at Phase 3 instead.
* **2.4 Fail with a name** (Hall certificate) if any domain empties: "ZU_11
has no legal column: ZUMA is committed in all 8."

Output: fixed columns for the anchor, reduced domains, hints, and free section
counts as Phase 3 variables.

**Note:** the 2025 anchor (ZUMA, 6 of 8 columns) is provisional — it comes from
assignment data. Recompute from the real qualification file; expect it to move.

---

## 5. Phase 3 — Column + student assignment (CP-SAT) [EXPLORED]

> **Correction (supersedes the original §5):** basket SDR over *subjects* is
> structurally infeasible once a subject runs multiple sections — the model
> must assign **students to sections**, not subjects to columns.

* `col[section] ∈ {A..H}` — one column per section (domain from Phase 2).
* `y[student, section] ∈ {0,1}` — student-to-section assignment, one section
per (student, chosen subject), `Σ students ≤ CAP` per section.
* Per-student all-different: the columns of a student's assigned sections are
pairwise distinct. (This replaces basket-level SDR as the hard constraint.)
* Teacher exclusivity within a column — **cross-grade, as a real constraint**.
* Sections beyond the floor are optional variables.
* **Objective: minimise sections beyond the load floor**, plus a heavily
weighted OOT escape. Do not optimise bare feasibility — it over-spreads.
* Exploration finding: feasibility solves in **< 1.2 s** for every grade-year
combination — Phase 3 is not the bottleneck.

---

## 6. Phase 4 — Teacher assignment [EXPLORED]

Bipartite matching per column, sections → qualified teachers, respecting
`MaxLoad`.

**Reframed product goal (from exploration):** find a feasible assignment with
the available teachers, **or** compute the minimum-cost repair — the fewest
additional qualification tokens that make the instance feasible. This removes
the expensive optimality proof in the common feasible case (proving minimality
took up to 38 s even on small instances).

Repair mechanics: CP-SAT assumption literals +
`sufficient_assumptions_for_infeasibility`; gate with the split/clique
pre-pass, which is far cheaper than exhaustive enumeration. See
docs/explorations/repair-model.md.

**Known risk:** Phases 3 and 4 are sequential but coupled. A column assignment
cheap in section count can force more distinct teachers. Decide deliberately:
fold teacher variables into Phase 3, or iterate 3↔4 with feedback.

**Do not warm-start from an existing timetable** — CLAUDE.md correction 9.

---

## 7. Phase 5 — Cell expansion [EXPLORED]

Expand each placed section across its column's periods. For M=7 seniors the
column *is* the schedule. Real work only for sub-column subjects (LO=2, PE=2,
RD=1, options=4) packing into shared columns; junior grades via König packing
in the band remainder.

**Reinstate the quarantined exception students here** (ids 7, 44, 69 in 2025)
— otherwise they silently receive no timetable.

---

## 8. Verification and tests

**The dangerous failure is a plausible wrong answer**, not a crash — a
timetable returned "feasible" that double-books a teacher, or a validator that
silently reports zeros (the 2025 workbook bug). Golden tests do not catch it.

**Independent verifier, non-negotiable:** every complete timetable goes through
`ClashDetector`, which must share no code with the solver. Run it in tests *and*
in production.

|Layer|Catches|
|-|-|
|Verifier on every output|Invalid-but-plausible timetables|
|Non-zero-scope guards on every verdict|Silent-zero "passes"|
|Exhaustive tiny instances (3 subjects, 5 students, 2 columns)|Model errors — brute-force the optimum and compare|
|**Infeasibility tests**|That failures name the *right culprit*|
|Regression on 2025 + 2026|Drift during refactoring|
|ED_12 at-cap assertion (25/25)|Cap handling regressions|

Regression fixtures are in CLAUDE.md — **note the Grade 12 row needs
re-derivation before use** (known off-by-one).

---

## 9. Build order

1. [DONE] Phase 0 parse + conversion + hard validation + existence table
2. [DONE] Phase 0 baskets + exception quarantine
3. [DONE] Phase 1 bounds (Excel-validated; Python port with tests pending)
4. `ClashDetector` verifier against a known-good timetable → test
5. [ACTIVE] Phase 2 precolour (symmetry break + propagation) → test
6. [EXPLORED] Phase 3 CP-SAT column + student assignment → test
7. [EXPLORED] Phase 4 teacher matching / repair model → test
8. [EXPLORED] Phase 5 cell expansion + exception reinstatement → test
9. End-to-end on 2025 and 2026

**Input dependencies:** teacher files in the qualification token format
(rebuild in progress — surname splits done), the subject conversion list, and
the explicit exception-selection rule.
