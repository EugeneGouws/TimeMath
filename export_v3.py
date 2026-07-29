"""Export a solved timetable as `timetable.json`, schema v3.0.

The v3.0 contract (top-level `version`, `timeslots`, `students`, `teachers`,
`lessons`, `enrolments`, `placements`, `student_slots`, `free_periods`) comes
from the TimeEduSuite converter, not from this project.

  NOTE: CLAUDE.md states this project deliberately does not reference the
  suite's code or schemas. Writing this file crosses that firewall knowingly,
  on request, so a solved timetable can be opened in Editor/TimeView. Nothing
  else in the pipeline imports it.

Two properties of the schema drive the code:

* `lessons` and `student_slots` are NORMATIVE; `enrolments` and `placements`
  are DERIVED and recomputed on every write. They are derived here too, from
  the same section list, so they cannot drift.
* Lesson labels are `CODE_SURNAME_GG[_N]` and must never contain a teacher id
  -- that breaks the converter's ST1/TT1 round-trip. `_N` is added only when
  one teacher runs two sections of the same subject and grade; the first keeps
  the bare label, the second becomes `_2`, per the converter's suffix
  recovery.

Because labels carry surnames, the output contains real names and MUST be
written under data/ (git-ignored), never into the repo.
"""
import json
import datetime

PERIODS = 7
COLUMNS = 8
OOT_SLOTS = ["P1", "P2", "P3", "P4"]


def all_timeslots():
    slots = [f"{chr(ord('A') + cl)}{p + 1}" for cl in range(COLUMNS) for p in range(PERIODS)]
    return slots + list(OOT_SLOTS)


def slot_name(cell):
    col, period = cell
    return f"{chr(ord('A') + col)}{period + 1}"


def _labels(placement, details):
    """Section -> label, applying CODE_SURNAME_GG[_N] and its suffix rule."""
    entries = []
    for _key, (sec, cells) in sorted(placement.items(), key=lambda kv: (
            kv[1][0].gr, kv[1][0].subject, kv[1][0].idx)):
        surname = (details.get(sec.teacherId, {}).get("TSurname") or
                   f"T{sec.teacherId}")
        surname = surname.upper().replace(" ", "_")
        entries.append((sec, cells, f"{sec.subject}_{surname}_{sec.gr:02d}"))

    counts = {}
    labelled = []
    for sec, cells, base in entries:
        counts[base] = counts.get(base, 0) + 1
        n = counts[base]
        labelled.append((sec, cells, base if n == 1 else f"{base}_{n}"))
    return labelled


def build(placement, students, details, quarantined,
          roster_file, teacher_file, version="3.0"):
    """Shapes match E:\\TimeEduSuite\\data\\2026\\2026_v3.json field for field.

    They do NOT match the wiki's json-timetable-schema summary, which states
    `lessons` carries `student_ids`/`timeslots` and `student_slots` maps
    label -> [slots]. The real file puts rolls in `enrolments`, slots in
    `placements`, and inverts `student_slots` to slot -> label. The file on
    disk wins; the wiki page is a paraphrase and is wrong on this point.

    Note ids and grades are STRINGS throughout, as in the real file.
    """
    labelled = _labels(placement, details)
    timeslots = all_timeslots()

    lessons, enrolments, placements = {}, {}, {}
    student_slots: dict[str, dict[str, str]] = {}
    teacher_used_slots: dict[str, set[str]] = {}

    for sec, cells, label in labelled:
        slots = [slot_name(cell) for cell in sorted(cells)]
        roll = [str(sid) for sid in sorted(sec.students or ())]
        tid = str(sec.teacherId)
        lessons[label] = {
            "name": sec.subject,
            # no subject display-name table in this project; the code is the
            # honest display name rather than an invented long form
            "display_name": sec.subject,
            "grade": str(sec.gr),
            "teacher": tid,
            "m": sec.m,
            "venues": {},
        }
        enrolments[label] = roll
        placements[label] = slots
        teacher_used_slots.setdefault(tid, set()).update(slots)
        for sid in roll:
            for slot in slots:
                student_slots.setdefault(sid, {})[slot] = label

    student_block = {}
    for s in list(students) + list(quarantined):
        student_block[str(s.id)] = {
            # This project's roster carries Id, Grade and subject codes only --
            # no names, classes, gender or house. Emitted empty rather than
            # invented; a consumer needing them must merge the source roster.
            "name": "",
            "grade": str(s.grade),
            "reg_class": "",
            "gender": "",
            "house": "",
        }

    teacher_block = {}
    for tid in sorted(teacher_used_slots, key=int):
        d = details.get(int(tid), {})
        surname = d.get("TSurname", "")
        initials = d.get("TInitials", "")
        teacher_block[tid] = {
            "surname": surname,
            "display_name": f"{d.get('TTitle', '')} {initials} {surname}".strip(),
            "venue": d.get("TClassroom", ""),
        }

    timetabled = [s for s in timeslots if s not in OOT_SLOTS]
    free_students = {}
    for s in students:
        used = student_slots.get(str(s.id), {})
        free = {t: "STUDY" for t in timetabled if t not in used}
        if free:
            free_students[str(s.id)] = free
    for s in quarantined:
        # quarantined students hold no lesson at all -- every slot is free,
        # which is the honest representation of "still needs placing by hand"
        free_students[str(s.id)] = {t: "STUDY" for t in timetabled}

    free_teachers = {}
    for tid in sorted(teacher_used_slots, key=int):
        free_teachers[tid] = {t: "FREE" for t in timetabled
                              if t not in teacher_used_slots[tid]}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "version": version,
        "generated_at": now,
        "source": {
            # the real file names an accdb here; this pipeline reads xlsx, so
            # the key is kept and the value says what was actually read
            "accdb": "",
            "roster": roster_file,
            "teachers": teacher_file,
            "read_at": now,
        },
        "timeslots": timeslots,
        "students": student_block,
        "teachers": teacher_block,
        "lessons": lessons,
        "enrolments": enrolments,
        "placements": placements,
        "student_slots": student_slots,
        "free_periods": {"students": free_students, "teachers": free_teachers},
    }


def check(doc) -> list[str]:
    """Verify the emitted document against the parts of the contract that can
    be checked without the suite: labels well-formed, derived blocks agreeing
    with the normative ones, no student or teacher in two places at once."""
    problems = []
    valid_slots = set(doc["timeslots"])

    for label, lesson in doc["lessons"].items():
        parts = label.split("_")
        if len(parts) < 3:
            problems.append(f"label {label!r} is not CODE_SURNAME_GG[_N]")
            continue
        # locate the GG segment: it is last, unless an _N split suffix follows.
        # GG is ZERO-PADDED (08, 09) while lesson["grade"] is the bare string
        # ("8"), so compare against the padded form -- otherwise every junior
        # lesson is reported malformed, which is what happened the first time
        # grades 8-9 were exported.
        gg = f"{int(lesson['grade']):02d}"
        gg_at = None
        if parts[-1] == gg:
            gg_at = len(parts) - 1
        elif len(parts) >= 4 and parts[-2] == gg:
            gg_at = len(parts) - 2
        if gg_at is None:
            problems.append(f"label {label!r} does not end in grade {gg}")
            continue
        # the surname sits between the code and the grade, and must not be the
        # teacher id -- that is what breaks the ST1/TT1 round-trip. (The grade
        # segment may coincidentally equal an id; only the surname is checked.)
        surname = "_".join(parts[1:gg_at])
        if not surname:
            problems.append(f"label {label!r} has no surname segment")
        elif surname == lesson["teacher"]:
            problems.append(f"label {label!r} embeds the teacher id as its surname")

        slots = doc["placements"].get(label, [])
        if len(slots) != lesson["m"]:
            problems.append(f"{label}: {len(slots)} slots placed but m={lesson['m']}")
        for slot in slots:
            if slot not in valid_slots:
                problems.append(f"{label}: unknown timeslot {slot}")
        if label not in doc["enrolments"]:
            problems.append(f"{label}: no enrolment entry")

    seen_student = {}
    seen_teacher = {}
    for label, lesson in doc["lessons"].items():
        for slot in doc["placements"].get(label, []):
            key = (lesson["teacher"], slot)
            if key in seen_teacher:
                problems.append(f"teacher {lesson['teacher']} double-booked at "
                                f"{slot}: {seen_teacher[key]} and {label}")
            seen_teacher[key] = label
            for sid in doc["enrolments"].get(label, []):
                skey = (sid, slot)
                if skey in seen_student:
                    problems.append(f"student {sid} double-booked at {slot}: "
                                    f"{seen_student[skey]} and {label}")
                seen_student[skey] = label

    # student_slots is the inverted view; it must agree with enrolments +
    # placements exactly, or the normative and derived blocks have drifted
    for sid, by_slot in doc["student_slots"].items():
        for slot, label in by_slot.items():
            if slot not in doc["placements"].get(label, []):
                problems.append(f"student_slots[{sid}][{slot}]={label} but that "
                                f"label is not placed there")
            if sid not in doc["enrolments"].get(label, []):
                problems.append(f"student_slots[{sid}][{slot}]={label} but {sid} "
                                f"is not on its roll")

    return problems


def write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=False)
