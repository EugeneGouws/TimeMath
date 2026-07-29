CLASS_CAP = 25
UNIVERSAL = frozenset({"EN", "LO", "PE", "MA", "ML"})
BAND = frozenset({"MA", "PE", "LO", "ML"})

# --- junior structure (grades 8-9) -------------------------------------------
# Juniors are a DIFFERENT MECHANISM, not a variant of the senior one:
#   * there is NO band. MA is 7 here, EN is 7, and each fills a whole column.
#   * every other subject is taught to the REGISTER CLASS, so the section roll
#     is the register class and there is no student-to-section decision.
#   * only FAL (AF/ZU) and the O-subjects regroup across register classes, so
#     they are the only junior subjects needing basket machinery.
# Consequence: the junior model is a per-student column PACKING (sum m <= 7 per
# column), not an all-different -- several m<7 subjects legitimately share a
# column. A typical Gr9 student carries 55 of the 56 cells, so the packing is
# tight: EN 7 + MA 7 + FAL 7 = 3 full columns, and 34 periods over the other 5.
JUNIOR_GRADES = frozenset({8, 9})
FAL = frozenset({"AF", "ZU"})
O_SUBJECTS = frozenset({"OA", "ODR", "ODA", "OE", "OF", "OM"})
JUNIOR_CHOICE = FAL | O_SUBJECTS

# A junior option is a distinct SUBJECT (different code, m=4) but not a
# distinct capability: whoever teaches the senior counterpart teaches it.
# Grounded in the school's own 2026 timetable, not assumed -- OE is taught by
# teachers 22 and 29, whose only qualification token is ED; OF by 19 (FR);
# ODA by 24 (DA); ODR by 30 and 43 (DR); OA by 56 (VA + OA). Without this the
# 2026 teacher file has an EMPTY pool for ODA, OE and OF and no junior grade
# can be staffed at all.
JUNIOR_OPTION_SOURCE = {
    "OA": "VA",     # art
    "ODA": "DA",    # dance
    "ODR": "DR",    # drama
    "OE": "ED",     # design
    "OF": "FR",     # french
    # NB: no OM entry. Music is the exception -- the O-music teacher (BARNES)
    # holds an explicit OM qualification token, so OM needs no inheritance and
    # must NOT pick up the senior MU pool.
}


def is_junior(grade: int) -> bool:
    return grade in JUNIOR_GRADES


def is_band(subject: str, grade: int) -> bool:
    """The band is a SENIOR structure. Juniors take MA, LO and PE too, but
    they are ordinary sub-column subjects there -- MA is 7, not 10, and there
    is no 14-cell region to tile. Anything asking "is this a band section?"
    must ask it per grade, or a junior LO gets spread across two columns that
    were never reserved for it."""
    return subject in BAND and not is_junior(grade)

SUBJECT_M_GRADE = {
      ("GE", 8): 3, ("GE", 9): 3,
      ("HI", 8): 3, ("HI", 9): 3,
      ("SC", 8): 3, ("SC", 9): 3,
      ("LS", 8): 3, ("LS", 9): 3,
      ("LO", 8): 3, ("LO", 9): 3,
      # MA is 10 in the SENIOR grades only. Juniors carry 7, so a junior band
      # is MA 7 + LO 3 + PE 2 = 12 of 14 cells and fits the 2-column band with
      # 2 cells of slack. Without this override getM returned the senior 10,
      # every junior tripped the oversized-band rule, and the whole grade was
      # quarantined.
      ("MA", 8): 7, ("MA", 9): 7,
      # EN is 8 in the junior grades, not 7. Derived by COUNTING CELLS in the
      # school's own 2026 timetable (never the JSON's stale `m` field), and it
      # is what makes the junior week add up EXACTLY:
      #   EN 8 + MA 7 + FAL 7 + GE 3 + HI 3 + SC 3 + LS 3 + LO 3 + PE 2
      #     + RD 1 + TE 4 + EMS 4 + two O-subjects 4+4  =  56 = ZERO SLACK.
      # With EN at 7 the total was 55 and the model had a free cell that does
      # not exist. Grades 8 and 9 carry the identical subject set and M values.
      ("EN", 8): 8, ("EN", 9): 8,
      ("DR", 8): 4, ("DR", 9): 4,
      ("ED", 8): 4, ("ED", 9): 4,
      ("EM", 8): 4, ("EM", 9): 4,
}
SUBJECT_M = {
      "AC": 7, "AF": 7, "BS": 7, "CAT": 7, "DA": 7,
      "DR": 7, "ED": 7, "EM": 4, "EMS": 4, "EN": 7, "FR": 7,
      "GE": 7, "HI": 7, "IT": 7, "LO": 2, "LS": 7, "MA": 10,
      # NB: RDI and OD are aliases (see ALIASES below), not canonical codes.
      "ML": 7, "MU": 7, "OA": 4, "ODR": 4, "ODA": 4,
      "OE": 4, "OF": 4, "OM": 4, "PE": 2, "RD": 1,
      "SC": 7, "TE": 4, "VA": 7, "ZU": 7,
}

# --- conversion table (DATA, not code -- PLAN.md §2.2) -----------------------
# Aliases: code seen in an input -> canonical code. Must be functional (no code
# maps to two targets), idempotent (canonical maps to itself) and closed (every
# target exists in SUBJECT_M). validate_conversion() asserts all three.
ALIASES = {
    "CA": "CAT",    # 2025->2026 drift, CLAUDE.md "Subject code drift"
    "OD": "ODR",
    "RDI": "RD",
    "NS": "SC",     # junior name for Science, CLAUDE.md existence table
}

# Codes that are DECLARED and deliberately ignored -- they are not subjects.
# Declared, not silently skipped: an unknown code must still hard-fail.
NON_TEACHING = frozenset({
    "LIB", "LIBRARY", "ST", "LAB",      # CLAUDE.md: non-teaching codes
    "BAT", "BATTING",                   # sports duty, seen in Teachers2026
    "FSM", "FSE", "FSS",                # support-slot codes, seen in Teachers2026
})


def canonical(code: str) -> str | None:
    """Canonicalise one input code. Returns None for a declared non-teaching
    code. Raises ValueError on anything unknown -- never defaults silently.
    """
    c = code.strip().upper()
    if c in NON_TEACHING:
        return None
    c = ALIASES.get(c, c)
    if c not in SUBJECT_M:
        raise ValueError(f"unknown subject code {code!r} (canonicalised {c!r})")
    return c


def validate_conversion() -> None:
    for src, dst in ALIASES.items():
        if dst in ALIASES:
            raise ValueError(f"alias {src}->{dst} is not idempotent: {dst} also aliased")
        if dst not in SUBJECT_M:
            raise ValueError(f"alias {src}->{dst} not closed: {dst} missing from SUBJECT_M")
        if src in NON_TEACHING:
            raise ValueError(f"{src} is both an alias and a non-teaching code")
    for code in SUBJECT_M:
        if code in ALIASES:
            raise ValueError(f"canonical code {code} is also an alias source")


def getM(subject: str, grade: int) -> int:
    if (subject, grade) in SUBJECT_M_GRADE:
        return SUBJECT_M_GRADE[(subject, grade)]
    if subject in SUBJECT_M:
        return SUBJECT_M[subject]
    raise ValueError(f"unknown subject code {subject}")