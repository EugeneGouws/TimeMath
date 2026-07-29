"""Phase 5 -- expand placed, staffed sections into actual cells.

A cell is (column, period), 8 x 7 = 56. Phase 3 fixed columns, Phase 4 fixed
teachers under a period-COUNTING relaxation; this phase does the exact packing
and is where that relaxation is honoured or exposed.

The unit that gets a cell pattern is not the section but the GROUP:
(grade, subject, region). Parallel sections of one subject in one region meet
at the same times -- three MA classes in a grade are simultaneous, taught by
three teachers in three rooms. That is what lets the band tile exactly:

    band = 2 columns x 7 periods = 14 cells
    MA(10) + LO(2) + PE(2) = 14      <- MA students, no slack
    ML(7)  + LO(2) + PE(2) = 11      <- ML students, 3 free cells

If instead every section chose its own pattern, an LO section holding students
from two different MA sections would have to dodge the union of both MA
patterns, and the band would not pack at all.

  x[group, cell] -> BoolVar, sum over cells == m
  per student, per cell: at most one of the groups they belong to
  per teacher, per cell: at most one of the groups they teach

Teachers are global, so this runs once across all grades.
"""
from ortools.sat.python import cp_model
import constants as c

PERIODS = 7
COLUMNS = 8


def cell_name(col: int, period: int) -> str:
    return f"{chr(ord('A') + col)}{period + 1}"


def region(sec, col: int, layout) -> tuple[int, ...]:
    """The columns a section may draw its periods from. Band sections span
    their grade's two band columns; everything else sits in its own column."""
    if c.is_band(sec.subject, sec.gr):
        return tuple(layout[sec.gr][1])
    return (col,)


def group_key(sec, col: int, layout):
    """One key per SECTION: every section picks its own cell pattern.

    An earlier version merged non-band sections sharing (grade, subject,
    column) into one pattern, on the grounds that an m == 7 section fills its
    whole column so grouping changes nothing. That reasoning holds only at
    m == 7. At m < 7 -- every junior override (GE/HI/SC/LS/LO = 3), and LO/PE
    anywhere -- merging FORCES those sections simultaneous, which is the
    "parallel sections need not be simultaneous" error this project has
    already rejected twice. Worse, it disabled the very check that would have
    caught it: by_teacher and by_student hold a SET of keys, so two sections
    collapsing to one key contribute one term and AddAtMostOne becomes a no-op.
    Seen live on grade 9 -- one teacher, two GE_9 sections, same cell.
    """
    return (sec.gr, sec.subject, sec.idx, region(sec, col, layout))


def solve(assignment, layout, time_limit=120.0):
    """assignment: list of (Section, column, tid) from Phase 4.
       layout: grade -> (en_col, band_cols).
    Returns (placement, None) or (None, reasons)."""
    model = cp_model.CpModel()

    groups: dict[tuple, list] = {}
    for sec, col, tid in assignment:
        groups.setdefault(group_key(sec, col, layout), []).append((sec, tid))

    x = {}
    for key, members in groups.items():
        _gr, subject, reg = key[0], key[1], key[-1]
        m = members[0][0].m
        cells = [(cl, p) for cl in reg for p in range(PERIODS)]
        if m > len(cells):
            cols = "".join(chr(ord('A') + cl) for cl in reg)
            return None, [f"{subject}_{_gr} needs {m} periods but column(s) {cols} "
                          f"offer only {len(cells)}"]
        vs = []
        for cell in cells:
            v = model.NewBoolVar(f"x_{subject}{_gr}_{cell_name(*cell)}")
            x[(key, cell)] = v
            vs.append(v)
        model.Add(sum(vs) == m)

    all_cells = [(cl, p) for cl in range(COLUMNS) for p in range(PERIODS)]

    # --- no student in two places at once ---------------------------------
    by_student: dict[int, set] = {}
    for sec, col, _tid in assignment:
        if sec.students is None:
            return None, [f"{sec.subject}_{sec.gr}#{sec.idx} has no student roll -- "
                          f"phase 3 did not decide its partition"]
        key = group_key(sec, col, layout)
        for sid in sec.students:
            by_student.setdefault(sid, set()).add(key)

    for sid, keys in by_student.items():
        for cell in all_cells:
            terms = [x[(k, cell)] for k in keys if (k, cell) in x]
            if len(terms) > 1:
                model.AddAtMostOne(terms)

    # --- no teacher in two places at once (global, across grades) ---------
    by_teacher: dict[int, set] = {}
    for sec, col, tid in assignment:
        by_teacher.setdefault(tid, set()).add(group_key(sec, col, layout))

    for tid, keys in by_teacher.items():
        for cell in all_cells:
            terms = [x[(k, cell)] for k in keys if (k, cell) in x]
            if len(terms) > 1:
                model.AddAtMostOne(terms)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    print(f"[phase5] status={solver.StatusName(status)} time={solver.WallTime():.2f}s")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, _named_reasons(assignment, layout, groups)

    pattern = {}
    for key in groups:
        pattern[key] = tuple(sorted(cell for (k, cell) in x
                                    if k == key and solver.Value(x[(k, cell)])))

    placement = {}
    for sec, col, _tid in assignment:
        placement[id(sec)] = (sec, pattern[group_key(sec, col, layout)])
    return placement, None


def _named_reasons(assignment, layout, groups):
    """Counting certificates: someone handed more periods in one region than
    the region physically holds."""
    reasons = []

    teacher_load: dict[tuple, int] = {}
    student_load: dict[tuple, int] = {}
    same_group: dict[tuple, int] = {}
    for sec, col, tid in assignment:
        reg = region(sec, col, layout)
        key = group_key(sec, col, layout)
        teacher_load[(tid, reg)] = teacher_load.get((tid, reg), 0) + sec.m
        same_group[(tid, key)] = same_group.get((tid, key), 0) + 1
        for sid in (sec.students or ()):
            student_load[(sid, reg)] = student_load.get((sid, reg), 0) + sec.m

    def cols_of(reg):
        return "".join(chr(ord('A') + cl) for cl in reg)

    for (tid, key), n in sorted(same_group.items()):
        if n > 1:
            reasons.append(f"teacher T{tid} holds {n} parallel sections of "
                           f"{key[1]}_{key[0]} in column(s) {cols_of(key[-1])} -- "
                           f"they meet at the same times, so they need "
                           f"{n} different teachers")
    for (tid, reg), load in sorted(teacher_load.items()):
        limit = PERIODS * len(reg)
        if load > limit:
            reasons.append(f"teacher T{tid}: {load} periods in column(s) "
                           f"{cols_of(reg)}, which hold only {limit}")
    for (sid, reg), load in sorted(student_load.items()):
        limit = PERIODS * len(reg)
        if load > limit:
            reasons.append(f"student {sid}: {load} periods in column(s) "
                           f"{cols_of(reg)}, which offer only {limit}")

    if not reasons:
        reasons = ["cells could not be packed, but no single overload found -- "
                   "the conflict is a combination of student and teacher cell "
                   "demands, not one saturated row"]
    return sorted(set(reasons))


def band_rigidity(assignment, pools):
    """Describe how tightly the band is coupled. NOT a proof of infeasibility.

    A student taking MA carries MA(10) + LO(2) + PE(2) = 14 periods against a
    14-cell band: zero slack, so their three sections must tile the band
    exactly. Fix one MA section's 10 cells and only 4 cells remain; every one
    of its students must find their LO and PE inside those 4.

    That is a strong coupling but it is NOT by itself a contradiction -- two
    LO sections under the same MA section can take disjoint halves of the 4
    free cells, so they do not even need different teachers. What it does mean
    is that LO and PE section MEMBERSHIP has to be chosen together with MA
    membership, and Phase 3 currently partitions each subject independently.
    That is the most likely cause of a Phase 5 packing failure, and the fix is
    to make the band a joint sub-problem, not to hire more LO teachers.

    Returns descriptive findings only. No claim of infeasibility is made here.
    """
    findings = []
    by_student_subject = {}
    for sec, _col, _tid in assignment:
        for sid in (sec.students or ()):
            by_student_subject[(sid, sec.subject)] = sec

    for sec, _col, _tid in assignment:
        if sec.subject != "MA":
            continue
        spread = {}
        for partner in ("LO", "PE"):
            partners = set()
            for sid in (sec.students or ()):
                other = by_student_subject.get((sid, partner))
                if other is not None:
                    partners.add(other.idx)
            spread[partner] = partners
        free = PERIODS * 2 - sec.m
        findings.append(
            f"grade {sec.gr} MA#{sec.idx}: its {len(sec.students or ())} students "
            f"are spread over {len(spread['LO'])} LO and {len(spread['PE'])} PE "
            f"sections, all of which must fit in the {free} band cells MA leaves "
            f"free (LO pool {len(pools.get(('LO', sec.gr), ()))}, "
            f"PE pool {len(pools.get(('PE', sec.gr), ()))})"
        )
    return findings
