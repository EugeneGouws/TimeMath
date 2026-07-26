CLASS_CAP = 25
UNIVERSAL = frozenset({"EN", "LO", "PE", "MA", "ML"})
BAND = frozenset({"MA", "PE", "LO", "ML"})

SUBJECT_M_GRADE = {
      ("GE", 8): 3, ("GE", 9): 3,
      ("HI", 8): 3, ("HI", 9): 3,
      ("SC", 8): 3, ("SC", 9): 3,
      ("LS", 8): 3, ("LS", 9): 3,
      ("LO", 8): 3, ("LO", 9): 3,
      ("DR", 8): 4, ("DR", 9): 4,
      ("ED", 8): 4, ("ED", 9): 4,
      ("EM", 8): 4, ("EM", 9): 4,
}
SUBJECT_M = {
      "AC": 7, "AF": 7, "BS": 7, "CAT": 7, "DA": 7,
      "DR": 7, "ED": 7, "EM": 4, "EMS": 4, "EN": 7, "FR": 7,
      "GE": 7, "HI": 7, "IT": 7, "LO": 2, "LS": 7, "MA": 10,
      "ML": 7, "MU": 7, "OA": 4, "OD": 4, "ODR": 4, "ODA": 4,
      "OE": 4, "OF": 4, "OM": 4, "PE": 2, "RD": 1, "RDI": 1,
      "SC": 7, "TE": 4, "VA": 7, "ZU": 7,
}

def getM(subject: str, grade: int) -> int:
    if (subject, grade) in SUBJECT_M_GRADE:
        return SUBJECT_M_GRADE[(subject, grade)]
    if subject in SUBJECT_M:
        return SUBJECT_M[subject]
    raise ValueError(f"unknown subject code {subject}")