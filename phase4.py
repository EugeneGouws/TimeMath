"""Phase 4 -- match the real teacher pool to the placed sections.

Runs ONCE for all grades together: columns are school-wide time slots, so
teacher exclusivity is the only thing that couples grades (CLAUDE.md, "Grades
cannot be solved independently"). Phase 3 has already fixed each section's
column per grade; this phase decides *who teaches it*.

Variables
  x[section, teacher] -> BoolVar, ExactlyOne per section over its qualified pool
  used[tid]           -> BoolVar, 1 if that teacher gets any section
  cells[section, col] -> IntVar, how many of the section's m periods fall in
                         that column. Constant m for a section pinned to one
                         column; a real variable only for band sections, which
                         span the band's two columns (MA has m=10 and cannot
                         fit in a 7-period column at all).

Exclusivity: PERIOD counting, not section counting.
      for each teacher t and column c:  sum of periods t teaches in c  <=  7
  For M=7 sections this collapses to "one section per teacher per column". It
  is deliberately weaker than AddAllDifferent-per-column, because two M=4
  option sections -- or an LO(2) and a PE(2) -- genuinely can be taught by one
  teacher inside one column. *Which* periods is Phase 5's job; this phase is a
  sound relaxation of it, so a Phase 4 pass is necessary but not sufficient
  and Phase 5 is the backstop.

Objective: fewest distinct teachers used (PRODUCT.md "minimal teacher usage").

Failure is named, not bare: we report the (subject, grade) or column whose
period demand outruns what its qualified teachers can physically supply.
"""
from ortools.sat.python import cp_model
import constants as c

PERIODS_PER_COLUMN = 7


def _regions(placed, layout):
    """section index -> tuple of columns it draws periods from."""
    regions = []
    for sec, col in placed:
        if sec.subject in c.BAND:
            regions.append(tuple(layout[sec.gr][1]))
        else:
            regions.append((col,))
    return regions


def _named_reasons(placed, regions, pools):
    """Counting certificates, computed without the solver.

    A group of sections sharing a region needs teacher-periods; the qualified
    teachers can supply at most 7 periods per column of that region each.
    """
    reasons = []

    # 1. one subject-grade whose sections crowd a single region
    groups = {}
    for i, (sec, _col) in enumerate(placed):
        groups.setdefault((sec.subject, sec.gr, regions[i]), []).append(sec)
    for (subject, gr, region), secs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        pool = pools.get((subject, gr), frozenset())
        demand = sum(s.m for s in secs)
        supply = len(pool) * PERIODS_PER_COLUMN * len(region)
        if demand > supply:
            cols = "".join(chr(ord('A') + cl) for cl in region)
            reasons.append(
                f"{subject}_{gr}: {len(secs)} sections need {demand} periods in "
                f"column(s) {cols}, but its {len(pool)} qualified teacher(s) can "
                f"supply only {supply} there"
            )

    # 2. a whole region demanding more than every teacher qualified for
    #    anything in it can supply
    by_region = {}
    for i, (sec, _col) in enumerate(placed):
        by_region.setdefault(regions[i], []).append(sec)
    for region, secs in sorted(by_region.items()):
        demand = sum(s.m for s in secs)
        supply_pool = set()
        for sec in secs:
            supply_pool |= pools.get((sec.subject, sec.gr), frozenset())
        supply = len(supply_pool) * PERIODS_PER_COLUMN * len(region)
        if demand > supply:
            cols = "".join(chr(ord('A') + cl) for cl in region)
            reasons.append(
                f"column(s) {cols}: {demand} simultaneous periods demanded but "
                f"only {len(supply_pool)} teacher(s) qualified for anything there "
                f"({supply} periods of supply)"
            )
    return reasons


def solve(placed, pools, layout, time_limit=120.0, enforce_parallel=False):
    """placed: list of (Section, column) across ALL grades.
       pools:  (subject, grade) -> frozenset of teacher ids.
       layout: grade -> (en_col, band_cols), from section.universal_layout.

    Returns (assignment, teachers_used) with assignment a list of
    (Section, column, tid), or (None, reasons) on infeasibility.
    """
    empty = []
    for sec, _col in placed:
        if not pools.get((sec.subject, sec.gr)):
            empty.append(f"{sec.subject}_{sec.gr}: no qualified teacher at all")
    if empty:
        return None, sorted(set(empty))

    regions = _regions(placed, layout)
    model = cp_model.CpModel()

    all_tids = sorted({tid for sec, _ in placed for tid in pools[(sec.subject, sec.gr)]})
    used = {tid: model.NewBoolVar(f"used_{tid}") for tid in all_tids}

    x = {}
    for i, (sec, _col) in enumerate(placed):
        choices = []
        for tid in sorted(pools[(sec.subject, sec.gr)]):
            v = model.NewBoolVar(f"x_{i}_{tid}")
            x[(i, tid)] = v
            choices.append(v)
            model.AddImplication(v, used[tid])
        model.AddExactlyOne(choices)

    # how many periods of section i land in each column of its region
    cells = {}
    for i, (sec, _col) in enumerate(placed):
        region = regions[i]
        if len(region) == 1:
            cells[(i, region[0])] = sec.m       # plain int, no decision
            if sec.m > PERIODS_PER_COLUMN:
                return None, [f"{sec.subject}_{sec.gr}#{sec.idx} has m={sec.m} but sits "
                              f"in a single {PERIODS_PER_COLUMN}-period column"]
        else:
            parts = []
            for cl in region:
                v = model.NewIntVar(0, PERIODS_PER_COLUMN, f"cells_{i}_{cl}")
                cells[(i, cl)] = v
                parts.append(v)
            model.Add(sum(parts) == sec.m)

    # --- period-counting exclusivity per (teacher, column) ----------------
    load = {}
    for i, (sec, _col) in enumerate(placed):
        for tid in pools[(sec.subject, sec.gr)]:
            for cl in regions[i]:
                cell = cells[(i, cl)]
                if isinstance(cell, int):
                    term = cell * x[(i, tid)]
                else:
                    # term = cell if teacher tid takes section i, else 0
                    term = model.NewIntVar(0, PERIODS_PER_COLUMN, f"load_{i}_{tid}_{cl}")
                    model.Add(term <= PERIODS_PER_COLUMN * x[(i, tid)])
                    model.Add(term <= cell)
                    model.Add(term >= cell - PERIODS_PER_COLUMN * (1 - x[(i, tid)]))
                load.setdefault((tid, cl), []).append(term)

    for (tid, cl), terms in load.items():
        if len(terms) > 1:
            model.Add(sum(terms) <= PERIODS_PER_COLUMN)

    # Optional (see phase34.solve for why it is off by default): parallel
    # sections of one subject in one region need distinct teachers only if
    # they are assumed to meet at the same times. LO runs 4 sections per grade
    # against 3 qualified teachers, so that assumption is infeasible here.
    if enforce_parallel:
        parallel = {}
        for i, (sec, _col) in enumerate(placed):
            for tid in pools[(sec.subject, sec.gr)]:
                parallel.setdefault((tid, sec.gr, sec.subject, regions[i]), []).append(x[(i, tid)])
        for key, terms in parallel.items():
            if len(terms) > 1:
                model.AddAtMostOne(terms)

    model.Minimize(sum(used.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    print(f"[phase4] status={solver.StatusName(status)} time={solver.WallTime():.2f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        reasons = _named_reasons(placed, regions, pools)
        if not reasons:
            reasons = ["infeasible, but no single counting certificate found -- the "
                       "clash is structural (a combination of columns), not one "
                       "saturated subject or column"]
        return None, reasons

    assignment = []
    for i, (sec, col) in enumerate(placed):
        tid = next(t for t in sorted(pools[(sec.subject, sec.gr)]) if solver.Value(x[(i, t)]))
        sec.teacherId = tid
        assignment.append((sec, col, tid))

    teachers_used = sorted(tid for tid in all_tids if solver.Value(used[tid]))
    print(f"[phase4] {len(teachers_used)} distinct teachers used of "
          f"{len(all_tids)} in the qualified pool "
          f"({'proven optimal' if status == cp_model.OPTIMAL else 'feasible, not proven minimal'})")
    return assignment, teachers_used
