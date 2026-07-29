"""Phase 3b — token-demand minimum: fewest interchangeable teacher "bodies"
that could cover the grid, teacher-free (abstract profiles, no real
qualification data). Solved jointly with column assignment: which columns
sections land in changes how many bodies collide in the same column.

Method: iterative deepening on k (per docs/PLAN.md §5a). Start at the cheap
bound ceil(sections/8) (a body can hold at most one section per column, 8
columns total), re-solve the joint model at increasing k until SAT.

Honest caveat (also in PLAN.md): this finds "k works", not "k-1 provably
doesn't" within the time budget — proving the lower bound tight is the same
expensive UNSAT proof that made Phase 4's optimality proof cost 38s. Treat
the returned k as a demonstrated-feasible minimum, not a proven one.
"""
import math
from ortools.sat.python import cp_model
import phase3


def _lower_bound_bodies(sections) -> int:
    return max(1, math.ceil(len(sections) / 8))


def solve_min_bodies(students, gr, sections, max_k=None, time_limit_per_k=15.0,
                     total_time_budget=120.0, band_cols=(1, 2)):
    """Returns (k, assignment) where assignment is a list of
    (section, column, body_id) tuples, or (None, None) if no k up to max_k
    was found within the total time budget.
    """
    import time

    n = len(sections)
    if max_k is None:
        max_k = n  # trivial upper bound: one body per section, no sharing

    k = _lower_bound_bodies(sections)
    print(f"[phase3b] {n} sections, cheap lower bound k={k} (ceil({n}/8))")

    start = time.monotonic()
    while k <= max_k:
        elapsed = time.monotonic() - start
        if elapsed > total_time_budget:
            print(f"[phase3b] total time budget ({total_time_budget}s) exceeded at k={k}, giving up")
            return None, None

        print(f"[phase3b] trying k={k} bodies ...")
        # band_cols MUST match the grade's rotated universal layout -- with the
        # default (1,2) against a rotated grade every k comes back INFEASIBLE,
        # because the band constants collide with that grade's choice columns.
        model, col_vars, y_vars, student_col, opened_vars = phase3.build_model(
            students, gr, sections, band_cols=band_cols)

        teacher_vars = [model.NewIntVar(0, k - 1, f"teacher_{i}") for i in range(n)]

        # symmetry break: body id t only used once body t-1 already appeared
        model.Add(teacher_vars[0] == 0)
        prev_max = teacher_vars[0]
        for i in range(1, n):
            model.Add(teacher_vars[i] <= prev_max + 1)
            new_max = model.NewIntVar(0, k - 1, f"running_max_{i}")
            model.AddMaxEquality(new_max, [prev_max, teacher_vars[i]])
            prev_max = new_max

        # two sections in the same column can't share a body
        for i in range(n):
            for j in range(i + 1, n):
                same_col = model.NewBoolVar(f"samecol_{i}_{j}")
                model.Add(col_vars[i] == col_vars[j]).OnlyEnforceIf(same_col)
                model.Add(col_vars[i] != col_vars[j]).OnlyEnforceIf(same_col.Not())
                model.Add(teacher_vars[i] != teacher_vars[j]).OnlyEnforceIf(same_col)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(time_limit_per_k, total_time_budget - elapsed)
        status = solver.Solve(model)
        print(f"[phase3b] k={k}: status={solver.StatusName(status)} time={solver.WallTime():.2f}s")

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignment = [
                (sections[i], solver.Value(col_vars[i]), solver.Value(teacher_vars[i]))
                for i in range(n)
            ]
            print(f"[phase3b] minimum feasible body count: k={k}")
            return k, assignment

        k += 1

    print(f"[phase3b] no feasible body count found up to max_k={max_k}")
    return None, None
