# Phase 4 — cost of minimising distinct teachers

**Status: EXPLORED, NOT IMPLEMENTED.** Source: chat sessions with throwaway
CP-SAT scripts.

## Question

The product goal is minimal teacher usage. What does *proving* minimality
cost, and is it worth paying?

## Findings

* Teacher-minimisation took **up to 38 s to prove optimality even on small
instances**. Feasibility is cheap; the optimality proof is not, and it will
get worse at full scale.
* This motivated the **product-goal reframing** (now in PLAN.md §6): find a
feasible assignment with available teachers, or compute a minimum-cost repair
for infeasible instances — skipping the optimality proof in the common
feasible case.
* Phase 3↔4 coupling confirmed as a real risk: a section-cheap column
assignment can force more distinct teachers. Unresolved whether to fold
teacher variables into Phase 3 or iterate with feedback; the repair reframing
reduces the pressure but does not remove the question.

## Open

* Is the marginal-impact greedy for distributing leftover teachers provably
near-optimal (submodularity?) or can it be arbitrarily bad?
