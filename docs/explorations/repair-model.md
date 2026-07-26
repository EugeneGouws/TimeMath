# Repair model — what to do when infeasible

**Status: EXPLORED, NOT IMPLEMENTED.** Source: chat sessions.

## Question

PRODUCT.md demands a *specific, actionable reason* on failure. Can we go one
better and propose the cheapest fix?

## Approach

* Model qualification tokens (and candidate section splits) as **CP-SAT
assumption literals**; on infeasibility, extract
`sufficient_assumptions_for_infeasibility` to name the deficient set.
* **Minimum-cost repair** = fewest additional qualification tokens (or splits)
that make the instance feasible. This *is* the actionable failure message:
"infeasible unless someone picks up SC_11" beats "infeasible".
* **Gate with the split/clique pre-pass** — it is far cheaper than exhaustive
enumeration and prunes most candidates.

## Findings

* Exhaustive enumeration of all minimum-cost split sets completed in ~91 s —
the time cost sits in enumeration, not in feasibility finding. Hence: find
*one* min-cost repair fast; enumerate all only on request.
* Combined with the Phase 4 reframing, the pipeline becomes:
feasible? → done. Infeasible? → named culprit + cheapest repair.

## Open

* Cost function design: are all qualification tokens equally priced, or
weighted by scarcity/PD-effort?
* Interaction with the exception-quarantine rule: a repair should never be
proposed for a problem an exception student caused.
