"""Phase 3+4 joint -- columns and teachers decided together, all grades at once.

PLAN.md §6 "Known risk": Phases 3/3b/4 are sequential but coupled. A column
assignment that is cheap in section count can force more distinct teachers.
That risk is not theoretical -- solving the grades independently put DA, FR,
IT and MU (pool size 1 each) into the same column in more than one grade, and
Phase 4 then had no legal teacher at all.

This module is the mitigation: one CP-SAT model holding every grade's Phase 3
structure (columns, student->section partition, optional extra sections) PLUS
the real teacher assignment, so a column choice that starves a singleton pool
is simply never made.

  col[section]         -> from phase3.build_model, per grade
  b[section, column]   -> BoolVar channelling col[section] == column
  x[section, teacher]  -> ExactlyOne over the qualified pool
  cells[band section, column] -> IntVar, band periods split across its 2 columns

  for each teacher t, column c:   periods t teaches in c  <=  7

Objective is lexicographic in spirit, encoded as a weighted sum: teachers
first (PRODUCT.md "minimal teacher usage"), sections beyond the floor second
(PLAN.md §5).
"""
from ortools.sat.python import cp_model
import constants as c
import phase3

PERIODS_PER_COLUMN = 7
TEACHER_WEIGHT = 100
EXTRA_WEIGHT = 1


def solve(students, grades, sections_by_grade, layout, pools,
          time_limit=300.0, teacher_weight=TEACHER_WEIGHT, enforce_parallel=False,
          two_stage=True, stage1_limit=180.0):
    """sections_by_grade: grade -> list[Section] at the Phase 1 floor.
    Returns (assignment, teachers_used, opened_total) with assignment a list of
    (Section, column, tid), or (None, reasons, None).
    """
    model = cp_model.CpModel()

    entries = []        # (Section, col_var, region_cols or None-if-free, grade)
    opened_all = []
    y_all = {}

    for grade in grades:
        band_cols = layout[grade][1]
        extended, extra_indices = phase3.add_optional_extras(sections_by_grade[grade])
        model, col_vars, y_vars, _sc, opened_vars = phase3.build_model(
            students, grade, extended, extra_indices, band_cols, model=model
        )
        opened_all.extend(opened_vars.values())
        for i, sec in enumerate(extended):
            in_model = opened_vars.get(i)   # None => a floor section, always on
            entries.append({
                "sec": sec,
                "col": col_vars[i],
                "band": tuple(band_cols) if c.is_band(sec.subject, sec.gr) else None,
                "opened": in_model,
            })
        for (sid, i), v in y_vars.items():
            y_all[(grade, sid, i)] = v

    # --- teacher assignment -----------------------------------------------
    missing = sorted({f"{e['sec'].subject}_{e['sec'].gr}: no qualified teacher at all"
                      for e in entries if not pools.get((e["sec"].subject, e["sec"].gr))})
    if missing:
        return None, missing, None

    all_tids = sorted({tid for e in entries
                       for tid in pools[(e["sec"].subject, e["sec"].gr)]})
    used = {tid: model.NewBoolVar(f"used_{tid}") for tid in all_tids}

    load = {}     # (tid, column) -> list of period-count terms
    one_per_col = {}  # junior only, see below

    for i, e in enumerate(entries):
        sec = e["sec"]
        pool = sorted(pools[(sec.subject, sec.gr)])
        opened = e["opened"]

        x = {}
        for tid in pool:
            v = model.NewBoolVar(f"x_{i}_{tid}")
            x[tid] = v
            model.AddImplication(v, used[tid])
        e["x"] = x

        # an unopened optional section needs no teacher
        if opened is None:
            model.AddExactlyOne(x.values())
        else:
            model.Add(sum(x.values()) == 1).OnlyEnforceIf(opened)
            model.Add(sum(x.values()) == 0).OnlyEnforceIf(opened.Not())

        if e["band"] is not None:
            # band section: its m periods split across the band's 2 columns
            cells = {}
            for cl in e["band"]:
                cells[cl] = model.NewIntVar(0, PERIODS_PER_COLUMN, f"cells_{i}_{cl}")
            if opened is None:
                model.Add(sum(cells.values()) == sec.m)
            else:
                model.Add(sum(cells.values()) == sec.m).OnlyEnforceIf(opened)
                model.Add(sum(cells.values()) == 0).OnlyEnforceIf(opened.Not())
            e["cells"] = cells

            for cl in e["band"]:
                for tid in pool:
                    term = model.NewIntVar(0, PERIODS_PER_COLUMN, f"ld_{i}_{tid}_{cl}")
                    model.Add(term <= PERIODS_PER_COLUMN * x[tid])
                    model.Add(term <= cells[cl])
                    model.Add(term >= cells[cl] - PERIODS_PER_COLUMN * (1 - x[tid]))
                    load.setdefault((tid, cl), []).append(term)
        else:
            # ordinary section: whole m lands in whichever column col takes
            cand = phase3._column_domain(sec.dom)
            b = {}
            for cl in cand:
                bv = model.NewBoolVar(f"b_{i}_{cl}")
                model.Add(e["col"] == cl).OnlyEnforceIf(bv)
                model.Add(e["col"] != cl).OnlyEnforceIf(bv.Not())
                b[cl] = bv
            e["b"] = b

            for cl in cand:
                for tid in pool:
                    a = model.NewBoolVar(f"a_{i}_{tid}_{cl}")
                    model.Add(a <= x[tid])
                    model.Add(a <= b[cl])
                    model.Add(a >= x[tid] + b[cl] - 1)
                    load.setdefault((tid, cl), []).append(sec.m * a)
                    if c.is_junior(sec.gr):
                        one_per_col.setdefault((tid, cl), []).append(a)

    # Linked sections (a junior EN split into 7 + 1 because m=8 exceeds a
    # column) are one class and must be taught by one teacher.
    linked = {}
    for e in entries:
        if e["sec"].link:
            linked.setdefault(e["sec"].link, []).append(e)
    for link, group in linked.items():
        first = group[0]
        for other in group[1:]:
            for tid in first["x"]:
                if tid in other["x"]:
                    model.Add(first["x"][tid] == other["x"][tid])

    for (tid, cl), terms in load.items():
        if len(terms) > 1:
            model.Add(sum(terms) <= PERIODS_PER_COLUMN)

    # Juniors only: at most ONE section per teacher per column.
    #
    # Period counting (sum m <= 7) is the right relaxation for deciding
    # columns, but it is NOT sufficient at cell level, and juniors are where
    # that bites: with m=3/m=4 subjects a teacher can hold two sections in one
    # column, and then their cell patterns must dodge each other AND every
    # student's other sections. Measured on grade 9 2026: the student arm alone
    # packs (OPTIMAL), the teacher arm alone packs (OPTIMAL), both together are
    # INFEASIBLE. Senior grades never hit it -- their choice subjects are m=7,
    # so one section already fills a teacher's column.
    #
    # This is a RESTRICTION, not a relaxation: it can only cost teachers or
    # make the model infeasible, never produce a clash. The band is deliberately
    # exempt (a band teacher's MA/LO/PE legitimately share the band's columns).
    for (tid, cl), terms in one_per_col.items():
        if len(terms) > 1:
            model.AddAtMostOne(terms)

    # Optional: force parallel sections of one subject in one region onto
    # distinct teachers. Sound ONLY under the simplifying assumption that such
    # sections meet at the same times. That assumption is provably too strong
    # here: LO runs 4 sections per grade against a pool of 3 qualified
    # teachers, so requiring it makes the instance infeasible. Off by default;
    # the band's real rigidity is diagnosed in phase5 instead.
    if enforce_parallel:
        parallel = {}
        for i, e in enumerate(entries):
            sec = e["sec"]
            for tid, xv in e["x"].items():
                if e["band"] is not None:
                    parallel.setdefault((tid, sec.gr, sec.subject, e["band"]), []).append(xv)
                else:
                    for cl, bv in e["b"].items():
                        a = model.NewBoolVar(f"par_{i}_{tid}_{cl}")
                        model.Add(a <= xv)
                        model.Add(a <= bv)
                        model.Add(a >= xv + bv - 1)
                        parallel.setdefault((tid, sec.gr, sec.subject, (cl,)), []).append(a)

        for key, terms in parallel.items():
            if len(terms) > 1:
                model.AddAtMostOne(terms)

    # --- two-stage solve ---------------------------------------------------
    # Stage 1 finds ANY legal timetable, with no objective. Stage 2 minimises
    # teachers starting from it as a hint.
    #
    # Why: on the 2025 whole school, minimising from a cold start returned
    # UNKNOWN after 900 s -- not infeasible, just no solution found at all --
    # while the same model with the objective removed solved to OPTIMAL in
    # 120 s. Feasibility is easy here; it is the headcount objective that
    # makes the search hard, and CP-SAT needs an incumbent to work down from.
    hint_vars = []
    if two_stage:
        stage1 = cp_model.CpSolver()
        stage1.parameters.max_time_in_seconds = min(stage1_limit, time_limit / 2)
        stage1.parameters.num_workers = 8
        st1 = stage1.Solve(model)
        print(f"[phase34] stage 1 (feasibility only): "
              f"status={stage1.StatusName(st1)} time={stage1.WallTime():.2f}s")
        if st1 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for e in entries:
                hint_vars.append((e["col"], stage1.Value(e["col"])))
                if e["opened"] is not None:
                    hint_vars.append((e["opened"], stage1.Value(e["opened"])))
                for v in e["x"].values():
                    hint_vars.append((v, stage1.Value(v)))
            time_limit = max(30.0, time_limit - stage1.WallTime())
        else:
            # No feasible timetable at all -- stage 2 will not find one either,
            # so say so now rather than burning the rest of the budget.
            return None, _named_reasons(entries, pools), None

    objective = teacher_weight * sum(used.values())
    if opened_all:
        objective = objective + EXTRA_WEIGHT * sum(opened_all)
    model.Minimize(objective)
    for var, value in hint_vars:
        model.AddHint(var, value)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    print(f"[phase34] status={solver.StatusName(status)} time={solver.WallTime():.2f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, _named_reasons(entries, pools), None

    # --- read back ---------------------------------------------------------
    _apply_rolls(entries, y_all, solver)

    assignment = []
    opened_total = 0
    for i, e in enumerate(entries):
        sec = e["sec"]
        if e["opened"] is not None:
            if not solver.Value(e["opened"]):
                continue
            opened_total += 1
        col = solver.Value(e["col"])
        tid = next(t for t, v in e["x"].items() if solver.Value(v))
        sec.column = col
        sec.teacherId = tid
        assignment.append((sec, col, tid))

    teachers_used = sorted(tid for tid in all_tids if solver.Value(used[tid]))
    print(f"[phase34] {len(teachers_used)} distinct teachers used of "
          f"{len(all_tids)} qualified; {opened_total} section(s) beyond floor "
          f"({'proven optimal' if status == cp_model.OPTIMAL else 'feasible, not proven minimal'})")
    return assignment, teachers_used, opened_total


def _apply_rolls(entries, y_all, solver):
    """Write the y-var decisions back onto Section.students.

    y keys are (grade, student_id, grade_local_section_index); entries are in
    grade order, so the grade-local index maps to the entry that follows the
    first entry of that grade.
    """
    first_of_grade = {}
    for pos, e in enumerate(entries):
        first_of_grade.setdefault(e["sec"].gr, pos)

    touched = {}
    for (grade, sid, i), v in y_all.items():
        pos = first_of_grade[grade] + i
        touched.setdefault(pos, set())
        if solver.Value(v):
            touched[pos].add(sid)
    for pos, sids in touched.items():
        entries[pos]["sec"].students = frozenset(sids)


def _named_reasons(entries, pools):
    """Counting certificate: a subject whose total period demand across all
    grades cannot fit its qualified pool anywhere in the 8-column week."""
    reasons = []
    demand = {}
    for e in entries:
        sec = e["sec"]
        if e["opened"] is not None:
            continue                       # optional, not part of the floor demand
        demand[sec.subject] = demand.get(sec.subject, 0) + sec.m

    supply_pool = {}
    for e in entries:
        sec = e["sec"]
        supply_pool.setdefault(sec.subject, set())
        supply_pool[sec.subject] |= pools.get((sec.subject, sec.gr), frozenset())

    for subject, periods in sorted(demand.items()):
        capacity = len(supply_pool[subject]) * PERIODS_PER_COLUMN * 8
        if periods > capacity:
            reasons.append(
                f"{subject}: {periods} periods demanded across all grades, but its "
                f"{len(supply_pool[subject])} qualified teacher(s) have only "
                f"{capacity} periods in the week"
            )
    if not reasons:
        reasons = ["no legal column+teacher assignment exists, and no single "
                   "subject is over capacity -- the conflict is a combination "
                   "of columns (try relaxing the universal-block rotation)"]
    return reasons
