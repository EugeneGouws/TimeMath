from dataclasses import dataclass
import math
import roster as r
from constants import getM
import constants as c

@dataclass
class Section:
    subject: str
    gr: int
    idx: int
    m: int
    students: frozenset[int] | None
    dom: int = 0xFF     #bitmask for domain for 8 columns
    column: int | None = None      #decided in phase 3
    teacherId: int | None = None   #decided in phase 4
    link: str | None = None        #sections sharing a link share one teacher

#---------------------------------------------------------------
def band_groups(students: list[r.Student], gr: int, cap: int = c.CLASS_CAP) -> list[frozenset[int]]:
    """Split a grade's students into band cohorts of at most `cap`.

    The band is 2 columns x 7 periods = 14 cells, and an MA student fills all
    14 of them: MA(10) + LO(2) + PE(2). Zero slack means those three sections
    must tile the band exactly -- so once MA's 10 cells are fixed, that
    student's LO and PE must live in the 4 cells left over. Choosing LO and PE
    membership independently of MA membership (which is what a plain
    ceil(n/cap) floor per subject does) produces requirements that cannot be
    packed, and that is what blocked Phase 5.

    Fix: make the cohort the unit. Students are grouped by their primary band
    subject (MA or ML), chunked to the cap; every band section then draws its
    roll from one cohort, so a cohort's band sections can tile the band
    together. ML cohorts carry 11 of 14 periods and keep 3 cells of slack.
    """
    by_primary: dict[str, list[int]] = {}
    for s in students:
        if s.grade != gr:
            continue
        if "MA" in s.subjects:
            primary = "MA"
        elif "ML" in s.subjects:
            primary = "ML"
        elif s.subjects & c.BAND:
            primary = "LO/PE only"      # no maths at all -- rare, keep separate
        else:
            continue                     # takes nothing in the band
        by_primary.setdefault(primary, []).append(s.id)

    groups = []
    for primary in sorted(by_primary):
        ids = sorted(by_primary[primary])
        # even chunks, so no cohort is left tiny
        n_groups = max(1, math.ceil(len(ids) / cap))
        size = math.ceil(len(ids) / n_groups)
        for start in range(0, len(ids), size):
            groups.append(frozenset(ids[start:start + size]))
    return groups


def reg_groups(students: list[r.Student], gr: int) -> dict[str, frozenset[int]]:
    """Register classes for one junior grade: reg label -> student ids.

    Students with no register class are put in a synthetic one of their own so
    they are never silently dropped -- roster.quarantine has already reported
    them.
    """
    groups: dict[str, set[int]] = {}
    for s in students:
        if s.grade != gr:
            continue
        label = s.reg if s.reg else f"NOREG_{s.id}"
        groups.setdefault(label, set()).add(s.id)
    return {label: frozenset(ids) for label, ids in groups.items()}


def build_junior_sections(students: list[r.Student], gr: int) -> list[Section]:
    """Junior grades: the register class IS the section.

    Everything except FAL (AF/ZU) and the O-subjects is taught to the whole
    register class, so those sections have a fixed roll and there is no
    student-to-section decision left for Phase 3 -- the same shape as band
    cohorts, and the reason the junior problem is far smaller than the senior
    one despite juniors carrying more subjects.

    FAL and the O-subjects regroup across register classes, so they get floor
    sections with students=None and Phase 3 partitions them.
    """
    groups = reg_groups(students, gr)
    subjects_of = {s.id: s.subjects for s in students if s.grade == gr}
    result = []

    per_subject_idx = {}
    for label in sorted(groups):
        for subject in sorted({sub for sid in groups[label] for sub in subjects_of[sid]}):
            if subject in c.JUNIOR_CHOICE:
                continue
            members = frozenset(sid for sid in groups[label] if subject in subjects_of[sid])
            if not members:
                continue
            m = getM(subject, gr)
            # A section cannot exceed one column: junior EN is m=8 against 7
            # periods, so it is split into linked pieces (7 + 1) that live in
            # different columns and share one teacher. Everything downstream
            # then keeps the invariant "one section fits one column", which is
            # what the whole column model rests on.
            pieces = []
            left = m
            while left > 0:
                pieces.append(min(7, left))
                left -= min(7, left)
            link = f"{subject}_{gr}_{label}" if len(pieces) > 1 else None
            for piece in pieces:
                idx = per_subject_idx.get(subject, 0)
                per_subject_idx[subject] = idx + 1
                result.append(Section(subject=subject, gr=gr, idx=idx,
                                      m=piece, students=members, link=link))

    floor_table = r.floors(students, gr)
    enrol_table = r.enrol(students, gr)
    for subject in sorted(c.JUNIOR_CHOICE):
        if subject not in floor_table:
            continue
        floor = floor_table[subject]
        roll = enrol_table[subject] if floor == 1 else None
        for idx in range(floor):
            result.append(Section(subject=subject, gr=gr, idx=idx,
                                  m=getM(subject, gr), students=roll))
    return result


def build_sections(students: list[r.Student], gr:int) -> list[Section]:
    if c.is_junior(gr):
        return build_junior_sections(students, gr)
    print("building sections")
    floor_table = r.floors(students,gr)
    enrol_table = r.enrol(students,gr)

    result = []

    # --- band subjects: one section per cohort, roll fixed here ------------
    groups = band_groups(students, gr)
    taken_by = {sid: s.subjects for s in students if s.grade == gr for sid in (s.id,)}
    per_subject_idx = {}
    for group in groups:
        for subject in sorted(c.BAND):
            members = frozenset(sid for sid in group if subject in taken_by[sid])
            if not members:
                continue
            idx = per_subject_idx.get(subject, 0)
            per_subject_idx[subject] = idx + 1
            result.append(Section(subject=subject, gr=gr, idx=idx,
                                  m=getM(subject, gr), students=members))

    # --- everything else: floor sections, split decided in phase 3 --------
    for subject, floor in floor_table.items():
        if subject in c.BAND:
            continue
        if floor == 1:
            s_students = enrol_table[subject]
        else:
            s_students = None #deffered to phase 3

        for idx in range(floor):
            result.append(Section(subject = subject, gr = gr, idx = idx, m = getM(subject,gr), students = s_students))

    return result

#-------------------------------------------------------------
def universal_layout(offset: int = 0) -> tuple[int, tuple[int, int]]:
    """(en_column, band_columns) for one grade.

    Placing the universal block is free symmetry WITHIN a grade -- but each
    grade picks its own 8 columns and the only thing linking grades is teacher
    exclusivity (CLAUDE.md, "The timetable shape"). Pinning EN to column A in
    every grade therefore stacks every grade's EN sections into one time slot:
    12 EN sections against 6 EN teachers, infeasible at Phase 4. Rotating the
    block by grade avoids that.

    This rotation is a HEURISTIC placement, not a sound domain reduction --
    per CLAUDE.md it may be revised (or become a Phase 3 decision variable) if
    Phase 4 fails; it must never be treated as a proof of anything.
    """
    en_col = offset % 8
    band_cols = ((offset + 1) % 8, (offset + 2) % 8)
    return en_col, band_cols


def pin_universal(sections: list[Section], offset: int = 0) -> None:
    if sections and c.is_junior(sections[0].gr):
        # Juniors have no universal block to pin. EN and MA are m=7 and do fill
        # a whole column each, but there is one EN section PER REGISTER CLASS
        # (5 of them in Gr9), so pinning EN to one column would demand 5
        # simultaneous EN teachers on top of the senior grades' EN. Different
        # register classes take EN in different columns; that freedom is the
        # whole point, so nothing is pinned and the packing constraint in
        # phase3 does the work.
        print("pin universal: skipped (junior grade -- no band, no block)")
        return
    print(f"pin universal (offset {offset})")
    en_col, band_cols = universal_layout(offset)
    en_mask = 1 << en_col
    band_mask = (1 << band_cols[0]) | (1 << band_cols[1])
    choice_mask = 0xFF & ~(en_mask | band_mask) #Choice un all other cols.

    for sec in sections:
        if sec.subject == "EN":
            sec.dom &= en_mask
        elif sec.subject in c.BAND:
            sec.dom &= band_mask
        else :
            sec.dom &= choice_mask
        assert sec.dom != 0, f"{sec} emptied by universal pin"

#-----------------------------------------------------------
def try_match(subject: str, dom_by_sub: dict[str,int], col_owner: dict[int,str], visited: set[int]) -> bool:
    #Check each column if subject can live there
    for col in range(8):
        if not (dom_by_sub[subject] & 1 << col):
            continue

        if col in visited:
            continue
        visited.add(col)

        #check if column is free. if it is, place it, else recursively "augment"
        if col not in col_owner or try_match(col_owner[col], dom_by_sub, col_owner, visited):
            col_owner[col] = subject
            return True

    return False

#-----------------------------------------------------------------
def basket_sdr(subjects: frozenset[str], dom_by_sub: dict[str,int]) -> dict[int,str] | None:
    col_owner = {}

    for sub in subjects:
        visited = set()
        if not try_match(sub, dom_by_sub, col_owner, visited):
            return None

    return col_owner

#-----------------------------------------------------------
def check_baskets(students: list[r.Student], gr: int, sections: list[Section]) -> list[str]:
    basket_table = r.baskets(students,gr)
    dom_by_sub = {sec.subject: sec.dom for sec in sections if sec.gr == gr}

    violations = []

    for subjects, student_ids in basket_table.items():
        if basket_sdr(subjects, dom_by_sub) is None:
            violations.append((subjects, student_ids))

    print("done checking baskets")
    return violations