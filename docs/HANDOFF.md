Handoff: Phase 2 — Precolour (Grade 12, 2026, per-grade isolation)

Mode: Model is settled; implementation is now in scope. Build in Python. Phase 0/1 (Excel, Phase01_2026.xlsx) is validated and exports JSON as Phase 2's input. Phase 2 writes domain results back to xlsx for visual check.

Scope decision: One grade at a time, starting with Grade 12, 2026 roster. Cross-grade teacher exclusivity is deliberately deferred to Phase 3 as a real constraint — do not bake grade-separation conventions into Phase 2 as if sound; they're heuristics and belong in AddHint, not constraints.

Terminology locked:

Column = A–H (was "Block")
Timeslot = 1 of the 56 places in the grid. 
Lesson = individual scheduled cell (subject, 1 teacher, one student bitset)
Section = the decision-carrying entity: subCode, grade, idx, student set, m-value. A Section generates lessons, isn't a collection of them.
For m>7 (MA 2026, m=10): Section placement is a column-set, not a single column — MA spans 2 columns combined with PE/LO into a 14-cell band.

Data inputs settled:

TT2025.xlsx (per year) is the teacher qualification file, derived from accdb, columns sua–sue hold qualification tokens (read dynamically, don't hardcode a–e; a fully-filled row signals truncated source data — assert against it).
LIB, ST, LAB are non-teaching codes → declare as canonical codes mapping to null in the conversion table (not silently skipped — same silent-default bug class as SUBJECT_M.value(code,7)).
Bare qualification code = grades 8–12.
Grade 12 2026 roster cleaned: ids 7 and 44 removed (incomplete records — id 44 had no EN at all), id 69's 6th subject moved out-of-timetable (OOT) so its basket is 5, not 6.

Exception rule — now explicit, two distinct rules:

Rule	Test	Action
Oversized basket	|basket| > free column count	Quarantine or push a subject to OOT (P1–P4)
Incomplete record	missing a universal subject / basket below norm	Report loudly, keep in model

Only the oversized rule is feasibility-relevant. Removed/OOT'd students must be reinstated at Phase 5 output or they silently get no timetable — track this.

Grade 12 2026 section floors at cap 25 (choice block, 22 sections):

Singleton (SDR elimination sound): AC 19, CAT 21, DA 9, DR 19, ED 25, FR 5, GE 15, HI 13, IT 13, MU 3, VA 8, ZU 19
Multi-section (Hall counting only, no elimination): AF 58→3, BS 34→2, LS 53→3, SC 42→2
Universal: EN 81→4, LO 80→4, PE 80→4, MA 54→3, ML 28→2
Watch: ED sits exactly at cap (25/25) — one more enrolment splits it out of the singleton set and weakens the propagator. Assert on this.

Phase 2 steps agreed:

2.0 Materialise sections at Phase 1 floor, domains as 8-bit integers (bitmask over columns).
2.1 Universal block placement, derived by formula not hardcoded: band width = ceil(ΣM_band / 7). Pin EN→A; pin MA+ML+PE+LO band → B (or B,C per the width formula). Year is a parameter, not a code fork.
2.2 Anchor teacher: rank by column demand (count of forced M=7 sections where qualification pool is a singleton). Pin the largest as the free symmetry break. Expected weak/near-empty at Grade 12 since bare-code qualifications (8–12) make pools broad — this is expected, not a bug; broad quals fail flatteringly by making the teacher-minimum look artificially achievable.
2.3 Propagate to fixpoint, alternating: teacher exclusivity (pairwise column-distinct per teacher) and basket SDR. Critical: SDR propagator must split singleton-section subjects (pairwise elimination sound) from multi-section subjects (Hall counting check only — subject-level all-different on a multi-section subject removes valid solutions).
2.4 Fail with a named culprit via bipartite matching / Hall's theorem certificate on any domain collapse to empty (e.g., "ZU_11 has no legal column: ZUMA committed in all 8").

Only symmetry breaks and domain reductions may become hard constraints; heuristic placements must be AddHint only, never constraints (CP-SAT is good at search, bad at symmetry — that's what 2.2 buys).

Known tooling trap: Phase01_2025.xlsx has a text/number type mismatch on Grade ('12' text vs 12 number) causing silent zero-scope bugs — Phase01_2026.xlsx is clean and integer-typed; use 2026 as the working file.

Not yet done / immediate next actions for Claude Code:

Write JSON export from Phase01_2026.xlsx Phase 0/1 output.
Implement Section materialisation (2.0) against Grade 12 2026.
Implement the band-width formula and universal block pin (2.1).
Implement anchor ranking (2.2) — expect it to do little at Grade 12; don't treat that as a bug.
Implement split SDR/exclusivity propagator (2.3) with Hall-based failure naming (2.4).
Write xlsx export of resulting domains for visual verification.