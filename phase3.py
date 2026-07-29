"""Phase 3 — CP-SAT column + student-section assignment. Rapid prototype.

Model (per docs/explorations/phase3-feasibility.md finding, teacher-free):
  col[section]            -> IntVar, domain = Phase 2's pinned bitmask
  y[student, section]     -> BoolVar, only for subjects with floor >= 2
                              (floor == 1 sections have a fixed student set,
                              no split decision needed)
  student_col[student, subject] -> the column that subject occupies for that
                              student; equals col[section] directly when
                              floor == 1, channelled through y when floor >= 2
  per-student AllDifferent over student_col[student, *] for every subject in
  that student's basket + universal block.

Escape valve (PLAN.md §5 Phase 3: "Sections beyond the floor are optional
variables... minimise sections beyond the load floor"): one optional extra
section per non-universal subject, `opened[i]` BoolVar, objective minimises
sum(opened). Found necessary empirically -- floor-only section counts proved
globally infeasible for Gr12 2026 even after the band simplification (see
git history / session notes): per-basket SDR is a necessary, not sufficient,
check, and doesn't see students competing for the same limited columns
across DIFFERENT baskets.
"""
from ortools.sat.python import cp_model
from dataclasses import replace
import roster as r
import constants as c


def _column_domain(mask: int) -> list[int]:
    return [col for col in range(8) if mask & (1 << col)]


def add_optional_extras(sections):
    """Append one optional extra section per non-universal subject, same
    column domain as its siblings. Returns a NEW list (sections + extras)
    and the set of indices into that list which are extras.
    """
    extended = list(sections)
    extra_indices = set()

    by_subject: dict[str, list] = {}
    for sec in sections:
        by_subject.setdefault(sec.subject, []).append(sec)

    for subject, secs in by_subject.items():
        if subject in c.UNIVERSAL:
            continue  # EN/band domains are singletons -- an extra can't help
        sibling = secs[0]
        if c.is_junior(sibling.gr) and subject not in c.JUNIOR_CHOICE:
            # A junior register-class section's roll is the register class.
            # An "extra" section would have no one to put in it, and would
            # invite phase 3 to redistribute a register class it must not touch.
            continue
        extra = replace(sibling, idx=len(secs), students=None)
        extra_indices.add(len(extended))
        extended.append(extra)

    return extended, extra_indices


def build_junior_model(students, gr, sections, extra_indices, model):
    """Junior column model: a per-student PACKING, not an all-different.

    Senior choice subjects are all m=7, so "two of my subjects may not share a
    column" and "my periods in a column may not exceed 7" say the same thing.
    Juniors break that: GE(3) and TE(4) share a column happily, and a Gr9
    student carries 55 of the 56 cells, so forbidding sharing is instantly
    infeasible. The constraint is therefore

        for each student s, column c:  sum of m over s's sections in c  <=  7

    Most junior sections have a fixed roll (the register class), so their only
    variable is the column. Only FAL and the O-subjects carry y vars.
    """
    enrol_table = r.enrol(students, gr)

    col_vars = []
    for sec in sections:
        dom = _column_domain(sec.dom)
        assert dom, f"{sec} has empty column domain going into phase 3"
        col_vars.append(model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(dom), f"col_{sec.subject}{sec.idx}_{gr}"))

    # b[i][cl] channels col_vars[i] == cl, so period loads can be summed
    b = []
    for i, sec in enumerate(sections):
        row = {}
        for cl in _column_domain(sec.dom):
            bv = model.NewBoolVar(f"jb_{gr}_{i}_{cl}")
            model.Add(col_vars[i] == cl).OnlyEnforceIf(bv)
            model.Add(col_vars[i] != cl).OnlyEnforceIf(bv.Not())
            row[cl] = bv
        b.append(row)

    by_subject: dict[str, list[int]] = {}
    for i, sec in enumerate(sections):
        by_subject.setdefault(sec.subject, []).append(i)

    y_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    opened_vars: dict[int, cp_model.IntVar] = {}
    fixed_for: dict[int, list[int]] = {}     # student -> section indices, roll fixed

    # A subject is y-decided if ANY of its sections still needs a roll -- which
    # includes a floor-1 subject that picked up an optional extra. Its fixed
    # sibling must then NOT also be counted as fixed, or the student's periods
    # are counted twice (ZU 7 + 7 = 14 against a 7-period column) and the grade
    # is infeasible for a reason that does not exist.
    y_subjects = {sec.subject for sec in sections if sec.students is None}

    for i, sec in enumerate(sections):
        if sec.students is None or sec.subject in y_subjects:
            continue
        for sid in sec.students:
            fixed_for.setdefault(sid, []).append(i)

    for subject, idxs in by_subject.items():
        free = [i for i in idxs if sections[i].students is None]
        if not free:
            continue                      # register-class sections: roll fixed
        eligible = enrol_table[subject]
        for sid in eligible:
            choices = []
            for i in idxs:
                y = model.NewBoolVar(f"jy_{gr}_{sid}_{subject}_{sections[i].idx}")
                y_vars[(sid, i)] = y
                choices.append(y)
            model.AddExactlyOne(choices)
        for i in idxs:
            model.Add(sum(y_vars[(sid, i)] for sid in eligible) <= c.CLASS_CAP)
            if i in extra_indices:
                opened = model.NewBoolVar(f"jopened_{gr}_{subject}{sections[i].idx}")
                for sid in eligible:
                    model.Add(y_vars[(sid, i)] <= opened)
                opened_vars[i] = opened

    # --- the packing constraint -------------------------------------------
    # Written to keep the model SMALL. The naive form (one z = y AND b var per
    # student x section x column) built ~12 600 booleans per grade and the
    # whole-school joint model then timed out at UNKNOWN after 600 s. Two
    # reductions, both exact -- no solutions are lost:
    #
    #   1. Every student in a register class carries the SAME fixed sections,
    #      so their period load per column is one shared quantity. It is
    #      computed once per (register class, column) instead of once per
    #      student.
    #   2. A student takes exactly one section per choice subject, so the
    #      column that subject occupies for them is a single variable. One
    #      indicator per (student, subject, column) replaces one per section.
    reg_of = {}
    for student in students:
        if student.grade == gr:
            reg_of[student.id] = student.reg or f"NOREG_{student.id}"

    # fixed sections grouped by the register class they belong to
    sections_of_reg: dict[str, list[int]] = {}
    for i, sec in enumerate(sections):
        if sec.students is None or sec.subject in y_subjects:
            continue
        any_sid = next(iter(sec.students))
        sections_of_reg.setdefault(reg_of[any_sid], []).append(i)

    reg_load = {}
    for reg, idxs in sections_of_reg.items():
        for cl in range(8):
            terms = [sections[i].m * b[i][cl] for i in idxs if cl in b[i]]
            if not terms:
                continue
            load = model.NewIntVar(0, 7, f"jload_{gr}_{reg}_{cl}")
            model.Add(load == sum(terms))
            reg_load[(reg, cl)] = load

    # one column variable per (student, choice subject), channelled through y
    student_col: dict[tuple[int, str], cp_model.IntVar] = {}
    for subject, idxs in by_subject.items():
        if subject not in y_subjects:
            continue
        cols_union = sorted({cl for i in idxs for cl in b[i]})
        for sid in enrol_table[subject]:
            sc = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(cols_union), f"jsc_{gr}_{sid}_{subject}")
            student_col[(sid, subject)] = sc
            for i in idxs:
                model.Add(sc == col_vars[i]).OnlyEnforceIf(y_vars[(sid, i)])

    for student in students:
        if student.grade != gr:
            continue
        sid = student.id
        reg = reg_of[sid]
        choice = [sub for sub in student.subjects if (sid, sub) in student_col]
        w = {}
        for sub in choice:
            for cl in range(8):
                wv = model.NewBoolVar(f"jw_{gr}_{sid}_{sub}_{cl}")
                model.Add(student_col[(sid, sub)] == cl).OnlyEnforceIf(wv)
                model.Add(student_col[(sid, sub)] != cl).OnlyEnforceIf(wv.Not())
                w[(sub, cl)] = wv
        for cl in range(8):
            terms = []
            if (reg, cl) in reg_load:
                terms.append(reg_load[(reg, cl)])
            for sub in choice:
                terms.append(c.getM(sub, gr) * w[(sub, cl)])
            if terms:
                model.Add(sum(terms) <= 7)

    return model, col_vars, y_vars, {}, opened_vars


def build_model(students, gr, sections, extra_indices: frozenset = frozenset(),
                band_cols=(1, 2), model=None):
    """Build the CP-SAT column + student-section model.

    Returns (model, col_vars, y_vars, student_col, opened_vars):
      col_vars    -> list[IntVar], aligned by index with `sections`
      y_vars      -> dict[(student_id, section_index)] -> BoolVar
      student_col -> dict[(student_id, subject)] -> IntVar
      opened_vars -> dict[section_index] -> BoolVar, 1 if that (extra)
                     section has any student in it. Only extras get one.
    """
    # `model` may be supplied so several grades share one model -- that is how
    # phase34 couples column choice with teacher supply across grades.
    if model is None:
        model = cp_model.CpModel()
    if c.is_junior(gr):
        return build_junior_model(students, gr, sections, extra_indices, model)
    enrol_table = r.enrol(students, gr)

    col_vars = []
    for i, sec in enumerate(sections):
        dom = _column_domain(sec.dom)
        assert dom, f"{sec} has empty column domain going into phase 3"
        col_vars.append(
            model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(dom), f"col_{sec.subject}{sec.idx}"
            )
        )

    by_subject: dict[str, list[int]] = {}
    for i, sec in enumerate(sections):
        by_subject.setdefault(sec.subject, []).append(i)

    y_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    student_col: dict[tuple[int, str], cp_model.IntVar] = {}
    opened_vars: dict[int, cp_model.IntVar] = {}

    for subject, idxs in by_subject.items():
        if subject in c.BAND:
            # Band sections carry a fixed cohort roll from Phase 2 (see
            # section.band_groups) -- there is no student-to-section decision
            # to make, and their columns are the band's, handled below.
            continue
        if len(idxs) == 1 and idxs[0] not in extra_indices:
            # floor == 1, no extra attached: student set fixed in Phase 2
            i = idxs[0]
            sec = sections[i]
            for sid in sec.students:
                student_col[(sid, subject)] = col_vars[i]
            continue

        # floor >= 2, or floor == 1 with an optional extra attached: which
        # section each student lands in is a real decision
        eligible = enrol_table[subject]
        cols_union = sorted({col for i in idxs for col in _column_domain(sections[i].dom)})
        for sid in eligible:
            sc = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(cols_union), f"sc_{sid}_{subject}"
            )
            student_col[(sid, subject)] = sc
            choices = []
            for i in idxs:
                y = model.NewBoolVar(f"y_{sid}_{subject}_{sections[i].idx}")
                y_vars[(sid, i)] = y
                choices.append(y)
                model.Add(sc == col_vars[i]).OnlyEnforceIf(y)
            model.AddExactlyOne(choices)

        for i in idxs:
            model.Add(sum(y_vars[(sid, i)] for sid in eligible) <= c.CLASS_CAP)
            if i in extra_indices:
                opened = model.NewBoolVar(f"opened_{sections[i].subject}{sections[i].idx}")
                for sid in eligible:
                    model.Add(y_vars[(sid, i)] <= opened)
                opened_vars[i] = opened

    # Band (MA/PE/LO/ML) is a real 2-column, 14-cell packing region (CLAUDE.md:
    # "an MA student reads A = MA*6 + PE*1, G = MA*4 + LO*2 + PE*1" -- subjects
    # interleave at the PERIOD level inside both band columns, not one-subject-
    # per-column). We don't model periods here, so a band subject's own
    # col_var is not individually meaningful -- what's real is that the band
    # AS A WHOLE consumes both pinned band columns for every band-taking
    # student. So contribute those 2 fixed columns ONCE per student (not once
    # per band subject -- MA/PE/LO all "sharing" the same 2 columns is by
    # design, not a collision).
    band_col_a = model.NewConstant(band_cols[0])
    band_col_b = model.NewConstant(band_cols[1])

    for student in students:
        if student.grade != gr:
            continue
        has_band = any(s in c.BAND for s in student.subjects)
        other_subjects = [s for s in student.subjects if s not in c.BAND]

        cols_for_student = []
        if has_band:
            cols_for_student.append(band_col_a)
            cols_for_student.append(band_col_b)
        for subj in other_subjects:
            if (student.id, subj) in student_col:
                cols_for_student.append(student_col[(student.id, subj)])

        if len(cols_for_student) > 1:
            model.AddAllDifferent(cols_for_student)

    return model, col_vars, y_vars, student_col, opened_vars


def solve_feasibility(students, gr, sections, time_limit=30.0, band_cols=(1, 2)):
    """Feasibility + minimise extra sections opened beyond the Phase 1 floor."""
    extended, extra_indices = add_optional_extras(sections)
    print(
        f"[phase3] grade {gr}: {len(sections)} floor sections + "
        f"{len(extra_indices)} optional extras available"
    )
    model, col_vars, y_vars, student_col, opened_vars = build_model(
        students, gr, extended, extra_indices, band_cols
    )
    if opened_vars:
        model.Minimize(sum(opened_vars.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    status = solver.Solve(model)
    print(f"[phase3] status={solver.StatusName(status)} time={solver.WallTime():.2f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, None, None

    opened_count = sum(solver.Value(v) for v in opened_vars.values())
    print(f"[phase3] {opened_count}/{len(extra_indices)} optional extra sections needed")

    # Materialise the student->section partition decided by the y vars, so
    # Phase 5 (and any verifier) has a concrete roll per section. Sections that
    # never got y vars (floor == 1, no extra attached) already carry their set.
    decided: dict[int, set[int]] = {i: set() for (_, i) in y_vars}
    for (sid, i), y in y_vars.items():
        if solver.Value(y):
            decided[i].add(sid)
    for i in decided:
        extended[i].students = frozenset(decided[i])

    columns = [solver.Value(v) for v in col_vars]
    used_sections = [
        sec for i, sec in enumerate(extended)
        if i not in extra_indices or solver.Value(opened_vars[i])
    ]
    used_columns = [
        col for i, col in enumerate(columns)
        if i not in extra_indices or solver.Value(opened_vars[i])
    ]
    return used_sections, used_columns, opened_count
