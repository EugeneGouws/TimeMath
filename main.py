"""End-to-end run, phases 0-5.

Phases 0-3 are per grade (grade-at-a-time mode: baskets never cross grades).
Phases 4 and 5 run ONCE across all grades, because columns are school-wide
time slots and teacher exclusivity is the only thing coupling the grades.

The whole run is parameterised by `run(...)` so the same pipeline can be
pointed at a different year, or at a synthetic fixture, without editing this
file. `main()` is the default 2026 run.
"""
import os
import sys
import roster as r
import section as sec_mod
import constants as c
import tt_loader as tt
import phase3
import phase3b
import phase4
import phase34
import phase5
import export_v3

ROSTER_FILE = "Phase01_2026.xlsx"
TEACHER_FILE = "data/2026/Teachers2026.xlsx"
GRADES = [10, 11, 12]
OUT_DIR = "out"


def run_grade(students, grade, offset, run_3b=True, time_limit=30.0):
    """Phases 1-3 for one grade. Returns ((Section, column) list, sections, bodies)."""
    print(f"\n=== grade {grade} ===")
    gr_students = [s for s in students if s.grade == grade]
    print(f"[phase0] {len(gr_students)} students in grade {grade}")
    if not gr_students:
        # A verdict computed over an empty scope is the canonical plausible
        # wrong answer (CLAUDE.md, Known traps) -- refuse to emit one. Seen for
        # real on grade 9: MA(10)+LO(3)+PE(2) = 15 periods against a 14-cell
        # band, so quarantine takes the whole grade.
        print(f"[phase0] grade {grade} has ZERO students in scope -- refusing "
              f"to emit a verdict (all quarantined, or none in the roster)")
        return None, None, None

    # ---- Phase 1: bounds -------------------------------------------------
    if c.is_junior(grade):
        # Juniors are a different mechanism (constants.JUNIOR_GRADES): no band,
        # no universal block, and the register class is the section for
        # everything but FAL and the O-subjects. Basket SDR does not apply --
        # it assumes one column per subject, and a junior legitimately packs
        # GE(3) + TE(4) into one column.
        sections = sec_mod.build_sections(students, grade)
        reg = sec_mod.reg_groups(students, grade)
        loads = [sum(c.getM(sub, grade) for sub in s.subjects) for s in gr_students]
        print(f"[phase1] junior grade: {len(reg)} register classes "
              f"{sorted((k, len(v)) for k, v in reg.items())}")
        print(f"[phase1] period load per student: min {min(loads)}, max {max(loads)} "
              f"of 56 cells")
        print(f"[phase2] materialised {len(sections)} sections "
              f"({sum(1 for x in sections if x.students is None)} awaiting a roll)")
        sec_mod.pin_universal(sections, offset)
        used_sections, columns, opened = phase3.solve_feasibility(
            gr_students, grade, sections, time_limit=time_limit)
        if used_sections is None:
            print(f"[phase3] grade {grade}: INFEASIBLE even with optional extras")
            return None, None, None
        print(f"[phase3] feasible column assignment ({opened} extra section(s) "
              f"beyond floor)")
        for sec, col in zip(used_sections, columns):
            sec.column = col
        return list(zip(used_sections, columns)), sections, None

    baskets = r.baskets(students, grade)
    max_basket = max(len(k) for k in baskets)
    choice_cols = 8 - 1 - 2          # EN takes 1 column, the band takes 2
    print(f"[phase1] {len(baskets)} distinct baskets, max size {max_basket}, "
          f"{choice_cols} choice columns free")
    if max_basket > choice_cols:
        print(f"[phase1] WARNING max basket ({max_basket}) exceeds choice columns "
              f"({choice_cols}) -- oversized-basket exception needed, not handled here")
    else:
        print("[phase1] not yet proven infeasible on the basket-size bound")

    # ---- Phase 2: precolour + basket SDR screen --------------------------
    sections = sec_mod.build_sections(students, grade)
    print(f"[phase2] materialised {len(sections)} sections")
    en_col, band_cols = sec_mod.universal_layout(offset)
    print(f"[phase2] universal block: EN -> {chr(ord('A') + en_col)}, band -> "
          f"{''.join(chr(ord('A') + cl) for cl in band_cols)}")
    sec_mod.pin_universal(sections, offset)
    violations = sec_mod.check_baskets(students, grade, sections)
    if violations:
        print(f"[phase2] {len(violations)} basket(s) have NO valid column SDR -- infeasible")
        for subjects, ids in violations:
            print(f"  basket {sorted(subjects)} (students {sorted(ids)}) has no valid column SDR")
        return None, None, None
    print(f"[phase2] all {len(baskets)} baskets pass the SDR pre-filter "
          f"(necessary, not sufficient)")

    # ---- Phase 3: columns + student->section partition -------------------
    used_sections, columns, opened = phase3.solve_feasibility(
        gr_students, grade, sections, time_limit=time_limit, band_cols=band_cols)
    if used_sections is None:
        print(f"[phase3] grade {grade}: INFEASIBLE even with optional extras")
        return None, None, None
    print(f"[phase3] feasible column assignment ({opened} extra section(s) beyond floor)")
    for sec, col in zip(used_sections, columns):
        sec.column = col

    bodies = None
    if run_3b:
        bodies, _ = phase3b.solve_min_bodies(gr_students, grade, used_sections,
                                             band_cols=band_cols)
        if bodies is not None:
            print(f"[phase3b] minimum abstract teacher-body demand: {bodies}")

    return list(zip(used_sections, columns)), sections, bodies


def write_outputs(placement, teachers_used, teacher_code, grades, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    secs = [placement[key] for key in placement]

    # --- grid per grade ---------------------------------------------------
    path = os.path.join(out_dir, "grid_by_grade.txt")
    with open(path, "w", encoding="utf-8") as f:
        for grade in grades:
            f.write(f"=== grade {grade} ===\n")
            rows = []
            for sec, cells in secs:
                if sec.gr != grade:
                    continue
                rows.append((sorted(cells), sec))
            rows.sort(key=lambda t: (t[0][0], t[1].subject))
            for cells, sec in rows:
                names = " ".join(phase5.cell_name(*cell) for cell in cells)
                f.write(f"{sec.subject}{sec.idx:<2} m={sec.m:<2} "
                        f"n={len(sec.students):<3} T{sec.teacherId}"
                        f"({teacher_code.get(sec.teacherId, '?')})  {names}\n")
            f.write("\n")
    print(f"[out] {path}")

    # --- per teacher ------------------------------------------------------
    path = os.path.join(out_dir, "grid_by_teacher.txt")
    by_teacher = {}
    for sec, cells in secs:
        by_teacher.setdefault(sec.teacherId, []).append((sec, cells))
    with open(path, "w", encoding="utf-8") as f:
        for tid in sorted(by_teacher):
            load = sum(s.m for s, _ in by_teacher[tid])
            f.write(f"=== T{tid} ({teacher_code.get(tid, '?')}) "
                    f"{len(by_teacher[tid])} sections, {load} periods ===\n")
            for sec, cells in sorted(by_teacher[tid], key=lambda t: sorted(t[1])[0]):
                names = " ".join(phase5.cell_name(*cell) for cell in sorted(cells))
                f.write(f"  {sec.subject}_{sec.gr}#{sec.idx}  {names}\n")
    print(f"[out] {path}")

    # --- per student ------------------------------------------------------
    path = os.path.join(out_dir, "grid_by_student.txt")
    by_student = {}
    for sec, cells in secs:
        for sid in sec.students:
            for cell in cells:
                by_student.setdefault(sid, {})[cell] = sec
    with open(path, "w", encoding="utf-8") as f:
        for sid in sorted(by_student):
            f.write(f"=== student {sid} ===\n")
            for col in range(phase5.COLUMNS):
                row = []
                for p in range(phase5.PERIODS):
                    sec = by_student[sid].get((col, p))
                    row.append(f"{sec.subject}{sec.idx}" if sec else "--")
                f.write(f"  {chr(ord('A') + col)}: " + " ".join(f"{v:>5}" for v in row) + "\n")
    print(f"[out] {path}")


def write_sections(assignment, teacher_code, grades, out_dir):
    """Phase 4 output: every section with its column, teacher and roll."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "sections.txt")
    with open(path, "w", encoding="utf-8") as f:
        for grade in grades:
            f.write(f"=== grade {grade} ===\n")
            rows = [(col, sec, tid) for sec, col, tid in assignment if sec.gr == grade]
            rows.sort(key=lambda t: (t[0], t[1].subject, t[1].idx))
            for col, sec, tid in rows:
                n = len(sec.students) if sec.students is not None else 0
                f.write(f"  {chr(ord('A') + col)}  {sec.subject}{sec.idx:<2} "
                        f"m={sec.m:<2} n={n:<3} T{tid}({teacher_code.get(tid, '?')})\n")
            f.write("\n")
    print(f"[out] {path}")


def write_exceptions(quarantined, report, out_dir):
    """Quarantined students still need a timetable -- PLAN.md §7 says reinstate
    them here, or they silently get nothing. They cannot be placed
    automatically (that is why they were quarantined), so they are written out
    as an explicit manual worklist rather than dropped in silence."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "exceptions.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== data-quality report ===\n")
        for line in report:
            f.write(line + "\n")
        f.write(f"\n=== {len(quarantined)} student(s) needing manual placement ===\n")
        for s in quarantined:
            f.write(f"student {s.id} grade {s.grade}: {sorted(s.subjects)}\n")
    print(f"[out] {path}")


def verify(placement, teacher_code):
    """Independent check, sharing no variables with the solver models
    (PLAN.md §8 -- the dangerous failure is a plausible wrong answer)."""
    secs = [placement[key] for key in placement]
    problems = []

    student_cells = {}
    teacher_cells = {}
    for sec, cells in secs:
        if len(cells) != sec.m:
            problems.append(f"{sec.subject}_{sec.gr}#{sec.idx}: {len(cells)} cells, m={sec.m}")
        if len(sec.students) > c.CLASS_CAP:
            problems.append(f"{sec.subject}_{sec.gr}#{sec.idx}: {len(sec.students)} students "
                            f"over cap {c.CLASS_CAP}")
        for cell in cells:
            for sid in sec.students:
                if (sid, cell) in student_cells:
                    problems.append(f"student {sid} double-booked at "
                                    f"{phase5.cell_name(*cell)}: "
                                    f"{student_cells[(sid, cell)]} and {sec.subject}")
                student_cells[(sid, cell)] = sec.subject
            key = (sec.teacherId, cell)
            if key in teacher_cells:
                problems.append(f"teacher T{sec.teacherId} double-booked at "
                                f"{phase5.cell_name(*cell)}: "
                                f"{teacher_cells[key]} and {sec.subject}_{sec.gr}")
            teacher_cells[key] = f"{sec.subject}_{sec.gr}"
    return problems


def run(roster_file=ROSTER_FILE, teacher_file=TEACHER_FILE, grades=GRADES,
        out_dir=OUT_DIR, run_3b=True, export=True, write_files=True,
        phase3_time=30.0, phase34_time=300.0, phase5_time=120.0):
    """One full pipeline run. Returns a result dict; never raises on an
    infeasible instance -- infeasibility is an answer, and `stage` says where
    it stopped so a test can assert on it.
    """
    result = {
        "roster": roster_file, "teachers": teacher_file, "grades": list(grades),
        "stage": "phase0", "ok": False,
        "students_modelled": 0, "quarantined": 0, "renumbered": 0,
        "sections": 0, "extras": 0, "teachers_used": 0,
        "per_grade": {}, "verify_problems": [], "reasons": [],
    }

    c.validate_conversion()
    print(f"=== end-to-end run: {roster_file} + {teacher_file}, grades {list(grades)} ===")

    students = r.parse_student(roster_file)
    print(f"[phase0] parsed {len(students)} students total")
    students, dup_report = r.resolve_duplicate_ids(students)
    for line in dup_report:
        print(f"[phase0] DATA PROBLEM: {line}")
    result["renumbered"] = len(dup_report)

    students, quarantined, exc_report = r.quarantine(students)
    for line in exc_report:
        print(f"[phase0] EXCEPTION: {line}")
    print(f"[phase0] {len(students)} students modelled, {len(quarantined)} quarantined")
    result["students_modelled"] = len(students)
    result["quarantined"] = len(quarantined)
    existence = r.existence(students)

    teachers = tt.parse_teachers(teacher_file)
    teacher_code = {t.tid: t.code for t in teachers}
    pools = tt.pools(teachers, existence)
    print(f"[phase0] parsed {len(teachers)} teachers, "
          f"{len(pools)} (subject, grade) pools")
    result["pools"] = len(pools)

    # A subject nobody is qualified for is a Phase 0 failure, not a solver
    # mystery -- say so before spending 300s finding out.
    missing_pool = []
    for grade in grades:
        for subject in r.floors(students, grade):
            if not pools.get((subject, grade)):
                missing_pool.append(f"no qualified teacher for {subject} grade {grade}")
    if missing_pool:
        for line in missing_pool:
            print(f"[phase0] PROBLEM: {line}")
        result["reasons"] = missing_pool
        return result

    # Rotate the universal block by grade -- see section.universal_layout for
    # why a shared column A is infeasible once real teachers are involved.
    layout = {}
    placed = []
    sections_by_grade = {}
    for n, grade in enumerate(grades):
        if not any(s.grade == grade for s in students):
            reason = (f"grade {grade} has zero students in scope -- all quarantined, "
                      f"or none in the roster")
            print(f"[phase0] PROBLEM: {reason}")
            result["reasons"] = [reason]
            return result
        offset = (3 * n) % 8
        layout[grade] = sec_mod.universal_layout(offset)
        got, floor_sections, bodies = run_grade(students, grade, offset,
                                                run_3b=run_3b,
                                                time_limit=phase3_time)
        sections_by_grade[grade] = floor_sections
        if got is None:
            print(f"\n=== stopped: grade {grade} did not reach a column assignment ===")
            result["stage"] = "phase3"
            result["reasons"] = [f"grade {grade} has no column assignment"]
            return result
        placed.extend(got)
        result["per_grade"][grade] = {
            "students": sum(1 for s in students if s.grade == grade),
            "sections": len(got),
            "bodies": bodies,
        }

    # ---- Phase 4: real teachers, all grades at once ----------------------
    # The joint model is primary. Phases 3 and 4 are coupled (PLAN.md §6), and
    # it shows: keeping Phase 3's columns and only choosing teachers needs 31
    # teachers on 2026 where deciding both together needs 24 -- and it
    # sometimes has no solution at all, because nothing stopped Phase 3 giving
    # two grades the same column for a subject with one qualified teacher.
    print(f"\n=== phase 3+4 joint: {len(placed)} sections, columns and teachers "
          f"decided together ===")
    result["stage"] = "phase34"
    assignment, info, opened = phase34.solve(
        students, grades, sections_by_grade, layout, pools, time_limit=phase34_time)
    if assignment is None:
        print("[phase34] no joint solution. Reasons:")
        for reason in info:
            print(f"  - {reason}")
        print("\n=== falling back to phase 4 on phase 3's fixed columns ===")
        assignment, info = phase4.solve(placed, pools, layout)
        if assignment is None:
            print("[phase4] INFEASIBLE. Named reasons:")
            for reason in info:
                print(f"  - {reason}")
            result["reasons"] = list(info)
            return result
        opened = 0
    teachers_used = info
    result["sections"] = len(assignment)
    result["extras"] = opened
    result["teachers_used"] = len(teachers_used)

    # Phase 4's answer is a deliverable in its own right (every section has a
    # column and a teacher), so write it out before attempting cells.
    if write_files:
        write_sections(assignment, teacher_code, grades, out_dir)
        write_exceptions(quarantined, exc_report, out_dir)

    # ---- Phase 5: cells --------------------------------------------------
    print(f"\n=== phase 5: expanding {len(assignment)} sections into cells ===")
    result["stage"] = "phase5"
    placement, reasons = phase5.solve(assignment, layout, time_limit=phase5_time)
    if placement is None:
        print("[phase5] could not pack cells into the 8x7 grid. Named reasons:")
        for reason in reasons:
            print(f"  - {reason}")
        print("[phase5] band coupling (descriptive, not a proof of infeasibility):")
        for finding in phase5.band_rigidity(assignment, pools):
            print(f"  . {finding}")
        print("[phase5] phases 0-4 output is still written to out/ "
              "(sections, columns and teachers); only period-level cells are missing")
        result["reasons"] = list(reasons)
        return result

    problems = verify(placement, teacher_code)
    result["verify_problems"] = problems
    if problems:
        print(f"[verify] {len(problems)} PROBLEM(S) -- timetable is NOT valid:")
        for p in problems[:20]:
            print(f"  - {p}")
        return result
    print("[verify] independent check passed: no double-booked student or "
          "teacher, every section has exactly m cells, no section over cap")

    if write_files:
        write_outputs(placement, teachers_used, teacher_code, grades, out_dir)
        write_exceptions(quarantined, exc_report, out_dir)

    result["stage"] = "done"
    result["ok"] = True

    # ---- v3.0 timetable.json --------------------------------------------
    # Lesson labels carry teacher surnames, so this file holds real names and
    # is written under data/ (git-ignored), never into the repo.
    if export:
        details = tt.parse_teacher_details(teacher_file)
        doc = export_v3.build(placement, students, details, quarantined,
                              roster_file, teacher_file)
        problems = export_v3.check(doc)
        if problems:
            print(f"[export] {len(problems)} PROBLEM(S) -- v3 JSON not written:")
            for p in problems[:20]:
                print(f"  - {p}")
            result["export_problems"] = problems
        else:
            # Derived from the ROSTER's directory, not the teacher file's: a
            # 2025 roster run against the 2026 teacher file would otherwise
            # write into data/2026/ and clobber the 2026 timetable.
            json_path = os.path.join(os.path.dirname(roster_file), "timetable.json")
            export_v3.write(json_path, doc)
            print(f"[export] v3.0 timetable.json written to {json_path} "
                  f"({len(doc['lessons'])} lessons, {len(doc['student_slots'])} students "
                  f"with slots, {len(doc['teachers'])} teachers)")
            result["export_problems"] = []
            result["lessons"] = len(doc["lessons"])
    if quarantined:
        print(f"[export] WARNING {len(quarantined)} quarantined student(s) appear in "
              f"'students' with no lesson at all -- every slot free. They still "
              f"need placing by hand (see {out_dir}/exceptions.txt)")
    print(f"\n=== done: {len(teachers_used)} teachers, {len(assignment)} sections, "
          f"grades {list(grades)} ===")
    return result


def main(argv=None):
    """CLI: main.py [roster.xlsx] [teachers.xlsx] [grade,grade,...]"""
    argv = list(sys.argv[1:] if argv is None else argv)
    roster_file = argv[0] if len(argv) > 0 else ROSTER_FILE
    teacher_file = argv[1] if len(argv) > 1 else TEACHER_FILE
    grades = [int(g) for g in argv[2].split(",")] if len(argv) > 2 else GRADES
    return run(roster_file, teacher_file, grades)


if __name__ == "__main__":
    main()
