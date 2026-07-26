# Bounds ladder — minimum teacher count

**Status: EXPLORED, NOT IMPLEMENTED.** Source: phone/chat brainstorm sessions
("Timetable Math" project), verified against 2025+2026 JSON with throwaway
scripts (`ttbounds.py`).

## Question

Given N students with free subject choice, how few teachers can staff the
year — and which structural property drives the number?

## Measured ladder (2026: 466 students, cap 25, 56 cells)

|Bound|Value|Meaning|
|-|-|-|
|Concurrency floor|≈ 19–20|Teachers on duty at peak, from true-group reconstruction|
|Pooled load bound|≈ 26 (at load 41)|Total teaching cells / max load, pooling all qualifications|
|Subject-silo bound|≈ 48 (at load 41)|Same, but each teacher locked to one subject|
|Actual|~55|Current staffing|

## Findings

* **Teacher count is driven by subject fragmentation / qualification
structure, not by conflict-graph colouring.** Concurrency is already
near-optimal (mean 21.6 busy vs floor ~19); the 26→48 gap is entirely
qualification silos.
* Free choice overhead: ~1.36× more groups than the cap-25 minimum but only
~1.18× more teacher-cells — extra groups are small-M electives.
* True groups (students sharing identical cell-sets): 2026 = 303, 2025 = 330,
median size 20. The JSON `subjects`/`lessons` keys are (subject, teacher,
grade) *aggregates*, not classes; `student_slots` is ground truth.
* Crude load anchor (481 students, 2026 rollover data): 253 min sections at
cap 25 vs **190 sections actually run** — real classes exceed cap or sections
are shared in ways the naive count misses. **Unreconciled; resolve before
trusting any bound built on 253.**

## Open

* When is max-of-bounds tight (achievable)?
* Where basket diversity enters: feasibility only, or the count itself?
* Absolute best/worst offering structures (streams vs free choice) — the
original phone question, still open.
