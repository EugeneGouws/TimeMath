# CLAUDE.md — Minimal-Teacher Timetabling (brainstorm project)

## Mode of work
**No building in this project. Brainstorming only.**
No production code, no apps, no pipelines. Small throwaway scripts are permitted
only to check arithmetic on toy examples or to pull facts out of the data files.
Every result must first be small enough to verify by hand.

## Outcome (what "done" looks like)
1. A **structure** (model + algorithm sketch) for timetabling a given set of
   learners with the **fewest possible teachers**, where:
   - Teachers exist in **pools**: each teacher belongs to the pool of all
     subjects they could possibly offer (qualification sets, not 1:1 subject
     assignment).
   - After the minimum is staffed, **leftover teachers are distributed one at
     a time**, each placed where an extra class has the greatest marginal
     impact (smaller classes, split of an overfull subject, new elective, …).
2. A **separate proof** of the lower bound: an argument for why the minimum
   teacher count cannot be smaller, not just an algorithm that happens to
   find a number.
3. A characterisation of **what conditions move that lower bound**
   (cap, max load, subject breadth, basket diversity, pool overlap,
   periods-per-cycle M, week length).

## Method
Start with **one grade, a handful of students, 2–4 subjects**, small enough to
do the maths by hand. Then scale up stepwise (more subjects → free baskets →
multiple grades → real data), and at every step record how the problem size
and the bound computations **grow (O-notation)**.

## Established facts about the data (verified, 2025+2026 JSON)
- The JSON contract's `subjects`/`lessons` keys are **(subject, teacher,
  grade) aggregates**, not classes. One key can bundle several parallel
  class groups. `student_slots` is ground truth; reconstruct **true groups**
  (students sharing an identical cell-set) from it.
- True groups: 2026 = 303, 2025 = 330. Median size 20. Classes essentially
  never exceed cap 25 except PE (40–45, mass-supervision exempt).
- The `m` field in the JSON is stale in ~86 sections/file. Authoritative M
  values live in `lessoninfo.cpp` (`timeedu::getM`), including grade-8/9
  overrides (GE/HI/SC/LS/LO=3, DR/ED/EM=4 at grades 8–9) and MA=10,
  LO(senior)=2, PE=2, RD/RDI=1, TE=4, option subjects=4, default 7.
- Bounds ladder measured on 2026 (466 students, cap 25, 56 cells):
  concurrency floor ≈ 19–20 teachers on duty at peak; pooled load bound
  ≈ 26 at load 41; **subject-silo bound ≈ 48 at load 41 vs ~55 actual**.
  Teacher count is driven mainly by subject fragmentation / qualification
  structure, not by conflict-graph colouring; concurrency is already
  near-optimal (mean 21.6 busy vs floor ~19).
- Free choice overhead: ~1.36× more groups than the cap-25 minimum but only
  ~1.18× more teacher-cells (extra groups are small-M electives).

## Open questions being circled
- Exact lower bound = ? Some max over {concurrency, pooled load, a covering
  bound over qualification pools (Hall-type condition), a colouring bound}.
  When is that max **tight**, i.e. achievable?
- Is the marginal-impact greedy for leftover teachers provably near-optimal
  (submodularity?) or can it be arbitrarily bad?
- How does basket diversity (25 baskets/100 students at Gr8 vs 54/66 at
  Gr10) enter the bound — or does it only affect feasibility, not count?
