# PLAN.md — Implementation Plan

Read **PRODUCT.md** for the goal and **CLAUDE.md** for established facts and
corrections. This file is the build order.

Prime directive: **each phase either produces a strictly smaller problem for the
next, or fails with a specific, named, actionable reason.** A phase that returns
"infeasible" without naming the culprit has not done its job.

\---

## 0\. Inputs (the contract with a school)

|File|Contents|
|-|-|
|`Students.xlsx`|One row per student: `Id, Lastname, Firstname, Grade, Reg, Gender, House, S1..Sn`|
|`Teachers.xlsx`|One row per teacher: `Id, Lastname, MaxLoad (blank=default), S1..Sn` qualification tokens|
|`Subjects.xlsx`|Canonical code, M per grade, alias list|
|`Shape`|Columns, periods per column, cap — `Constants.h` defaults, overridable|

Rules:

* **Caps and school-wide defaults live in `Constants.h`** (`CLASS\\\\\\\\\\\\\\\_CAP`, `MAX\\\\\\\\\\\\\\\_LOAD`).
* **Per-teacher and per-school data lives in the xlsx**, never in a header. A
per-school header fork breaks the "new school sends me data" goal.
* The **conversion table is data**, not code.

\---

## 1\. Object model

The entity missing from the previous codebase is `Section`. `Lesson` was a single
cell, so a 7-period class was 7 unrelated objects with no identity — nothing for
a solver to assign.

```cpp
struct Section {                    // THE decision-carrying entity
    QString subCode;                // canonical
    int     gr   = 0;
    int     idx  = 0;               // 0..n-1 parallel groups
    int     m    = 0;               // periods per cycle, from getM
    std::bitset<MAX\\\\\\\\\\\\\\\_STUDENTS> S;    // enrolled students
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

\---

## 2\. Phase 0 — Normalise

1. Parse rosters and teacher file.
2. **Apply the conversion table once, at parse.** Nothing downstream may see an
alias. Validate the table itself first:

   * **functional** — no code maps to two targets
   * **idempotent** — every canonical code maps to itself
   * **closed** — every target exists in the M table and the existence table
3. **Hard validation, fail loudly**: every code appearing in any input must
resolve to a canonical code present in the M table. Report the offending code
and where it appeared. Never default silently. (This alone would have caught
all three known renames.)
4. **Derive the subject-grade existence table from the roster.** Do not
hand-maintain.
5. Expand qualification tokens (union semantics, intersected with existence).
6. Derive baskets: distinct choice-subject sets with frequency counts.
7. Split subjects into **universal** (taken by \~all students) and **choice**.
8. **Quarantine exceptions** by an explicit, testable rule — incomplete records
and oversized baskets — *before* modelling. Letting one student into the model
makes the whole grade pay for them.

Output: baskets, sections-to-be, qualification map, existence table, exception list.

\---

## 3\. Phase 1 — Bounds (fail fast)

Compute all, take the max. This is where "infeasible" becomes actionable.

|Bound|Computation|Failure message|
|-|-|-|
|Basket size|max basket size|"Student X takes N subjects; block has C columns"|
|Clique|max clique in co-occurrence graph|"AC/CAT/HI/GE mutually conflict; needs 4 columns"|
|Load|`ceil(students\\\\\\\\\\\\\\\_j / cap)` per subject|"Subject j needs k sections"|
|Teacher column demand|per teacher, count of M=7 classes|"Teacher T needs k distinct columns"|
|Hall / covering|for every subject set S: `Σ sections(S) ≤|teachers qualified for S|

Max basket size is a valid clique, so it is a sound lower bound even when full
clique-finding is skipped.

Already implemented and validated in Excel (`Phase01\\\\\\\\\\\\\\\_Screen.xlsx`) for Phases 0–1.
Port it; the workbook is the spec and the fixture.

\---

## 4\. Phase 2 — Precolour

**The trap:** a pin is a commitment, and an unsound one surfaces 200 decisions
later as an infeasibility unrelated to the real constraints, with no way to walk
it back. This is the most likely mechanism by which a previous attempt died
slowly rather than cleanly.

Phase 2 produces **three kinds of output, only two of which may become hard
constraints**:

1. **Symmetry breaks — sound.** Pinning the most column-demanding teacher's
sections to columns A, B, C… loses nothing, because at that moment no other
section is placed and all columns are interchangeable. Highest-value thing
Phase 2 does: CP-SAT is excellent at search and bad at symmetry, so without
this it re-discovers 8! relabellings of the same timetable.
2. **Domain reductions — sound.** "AC\_12 cannot be in column D", derived by
propagation. Never removes a real solution.
3. **Heuristic placements — NOT sound.** These must become CP-SAT **hints**
(`AddHint`), never constraints.

> \\\\\\\\\\\\\\\*\\\\\\\\\\\\\\\*Phase 2 shrinks domains and kills symmetry. It does not guess a partial
> solution.\\\\\\\\\\\\\\\*\\\\\\\\\\\\\\\*

### Steps

* **2.0 Materialise sections** at the Phase 1 floor. Only floor sections may be
pinned — anything beyond the floor is a Phase 3 decision.
* **2.1 Place the universal block** per grade: EN one column; MA+ML parallel and PE+LO sharing two more (this will need to be resolved later).
* **2.2 Pin the anchor teacher.** Rank teachers by column demand (count of M=7
sections, forced only where the qualification pool is a singleton). Pin the
largest — this is the free symmetry break. Every *subsequent* teacher is not
free, because the symmetry is spent; those become domain reductions.
* **2.3 Propagate to fixpoint.** Alternate teacher exclusivity (a teacher's
sections are pairwise column-distinct) and basket SDR (subjects co-occurring in
a basket are column-distinct) until nothing changes. A domain collapsing to one
value is a *derived* pin — sound.
* **2.4 Fail with a name** if any domain empties: "ZU\_11 has no legal column:
ZUMA is committed in all 8."

Output: fixed columns for the anchor, reduced domains for everything else, hints,
and free section counts as Phase 3 variables.

**Note:** the 2025 anchor (ZUMA, 6 of 8 columns) is provisional — it comes from
assignment data, not qualifications. **Recompute the ranking from the real
qualification file; expect the anchor to move.**

\---

## 5\. Phase 3 — Column assignment (CP-SAT)

* `x\\\\\\\\\\\\\\\[section, column] ∈ {0,1}`, exactly one column per section.
* Basket SDR: for each basket, chosen columns all-different.
* Teacher exclusivity within a column.
* Sections beyond the floor are optional variables.
* **Objective: minimise sections beyond the load floor**, plus a heavily weighted
OOT escape. Do not optimise for bare feasibility — it over-spreads subjects.

\---

## 6\. Phase 4 — Teacher assignment

Bipartite matching per column, sections → qualified teachers, respecting
`MaxLoad`. **Minimise distinct teachers used** — this is where the product goal
is actually optimised — then distribute leftover teachers by marginal impact.

**Known risk:** Phases 3 and 4 are sequential but coupled. A column assignment
cheap in section count can force more distinct teachers. Two ways out: fold
teacher variables into Phase 3 (one bigger solve), or iterate 3↔4 with feedback.
Decide deliberately; do not let the ordering happen by default.

\---

## 7\. Phase 5 — Cell expansion

Expand each placed section across its column's periods. For M=7 seniors this is
trivial — the column *is* the schedule. Real work only for sub-column subjects
(LO=2, PE=2, RD=1, options=4) packing into shared columns.

\---

## 8\. Verification and tests

**The dangerous failure is a plausible wrong answer**, not a crash — a timetable
returned "feasible" that double-books a teacher. Golden tests do not catch it.

**Independent verifier, non-negotiable:** every complete timetable goes through
`ClashDetector`, which must share no code with the solver. Run it in tests *and*
in production. If solver and verifier disagree, you learn immediately.

|Layer|Catches|
|-|-|
|Verifier on every output|Invalid-but-plausible timetables|
|Exhaustive tiny instances (3 subjects, 5 students, 2 columns)|Model errors — brute-force the optimum and compare. Real data exercises only one shape|
|**Infeasibility tests**|That failures name the *right culprit*. Feed a 6-subject basket into a 5-column block; assert it names that student|
|Regression on 2025 + 2026|Drift during refactoring|

The infeasibility layer is usually skipped and is exactly what PRODUCT.md's
definition of done turns on — "a specific, actionable reason" is a testable claim.

Regression fixtures are in CLAUDE.md.

\---

## 9\. Build order

1. Phase 0 parse + conversion + hard validation + existence table  → test
2. Phase 0 baskets + exception quarantine                          → test vs fixtures
3. Phase 1 bounds                                                  → test vs workbook
4. `ClashDetector` verifier against a known-good timetable         → test
5. Phase 2 precolour (symmetry break + propagation)                → test
6. Phase 3 CP-SAT column assignment                                → test
7. Phase 4 teacher matching                                        → test
8. Phase 5 cell expansion                                          → test
9. End-to-end on 2025 and 2026

**Blocked until inputs land:** teacher files rebuilt in the qualification token
format, the subject conversion list, and the explicit exception-selection rule.
Steps 1–4 can be built against current data; step 5 onward needs the rebuild.

