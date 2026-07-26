# Consolidation note — for Eugene + Gremlin (delete after merging)

Drafted 2026-07-26 by chat-Claude from: the synced project docs, chat-side
memory, and the phone brainstorm sessions. **Diff against the repo before
committing** — these drafts were written from synced copies, not repo state.

## What to do

1. Drop this folder's contents into the solver repo root: `CLAUDE.md`,
   `PLAN.md`, `docs/explorations/*`, `docs/archive/BRAINSTORM.md`.
   `PRODUCT.md` is unchanged — keep the repo's copy.
2. Delete the old chat-project copies; set the claude.ai project to sync from
   the repo so chat and Gremlin read the same files.
3. Working agreement from here: **a fact is not established until committed to
   CLAUDE.md.** Chat memory is scratch. Exploration results go to
   docs/explorations/ with an EXPLORED flag, and get promoted only when
   implemented and tested.

## What changed vs the old docs

* **CLAUDE.md**: added current-state section (coding = Phase 2; phases 3–5
  explored only); added corrections 4–9 (Phase 3 model fix, 2025 silent-zeros
  bug, dup Gr10 IDs, GOVENDER/WYLIE splits, stale 2026 teacher table,
  warm-start rejection); added SDR soundness boundary, band structure with
  `ceil(ΣM/7)`, ED_12 at-cap assertion, TT<year>.xlsx conventions, exception
  reinstatement rule, sibling-project firewall paragraph, VERIFY flag on the
  Gr12 fixture row.
* **PLAN.md**: §5 rewritten to student-to-section formulation (old subject-SDR
  version was structurally infeasible); §6 reframed to
  feasible-or-min-cost-repair; §8 gained non-zero-scope guards and the at-cap
  assertion; build order gained status tags; teacher file renamed
  `TT<year>.xlsx`.
* **BRAINSTORM.md**: moved to docs/archive/ with a superseded banner (its
  "no building" rule contradicted PRODUCT.md).
* **New**: docs/explorations/ (bounds ladder, Phase 3 feasibility, Phase 4
  cost, repair model, warm-start rejection).

## Open items needing your verification (not resolvable from chat)

1. **Gr12 fixture off-by-one** — re-derive students/baskets from the roster;
   the table row is flagged VERIFY until then.
2. **Teacher file rebuild status** — CLAUDE.md says "in progress"; correct if
   done. Nine real mismatches from the dedup session (ALDRIDGE GE_08, ALDWORTH
   LIB_12, ALLY EMS_09, BARNES OM/MU, BHUNGANE SC_08, ELLIS LS_09, LAMB
   DA/ODA, VAN DEN BERG ODR/DR/OD, VISSER LS_12/LS_09) still need resolution.
3. **Anchor teacher** — recompute ranking from the rebuilt qualification file.
4. **253 vs 190 section count** discrepancy (bounds-ladder.md) — unreconciled.
