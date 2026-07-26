from dataclasses import dataclass
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

#---------------------------------------------------------------
def build_sections(students: list[r.Student], gr:int) -> list[Section]:
    print("building sections")
    floor_table = r.floors(students,gr)
    enrol_table = r.enrol(students,gr)

    result = []
    for subject, floor in floor_table.items():
        if floor == 1:
            s_students = enrol_table[subject]
        else:
            s_students = None #deffered to phase 3

        for idx in range(floor):
            result.append(Section(subject = subject, gr = gr, idx = idx, m = getM(subject,gr), students = s_students))

    return result

#-------------------------------------------------------------
def pin_universal(sections: list[Section]) -> None:
    print("pin universal")
    en_mask = 1<<0              #EN in column 0
    band_mask = (1<<1) | (1<<2) #Band in col 1 or 2
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
            print("col", col, "subject", subject)
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
    print("check_baskets")
    basket_table = r.baskets(students,gr)
    dom_by_sub = {sec.subject: sec.dom for sec in sections if sec.gr == gr}

    violations = []

    for subjects, student_ids in basket_table.items():
        print("checking ", subjects)
        if basket_sdr(subjects, dom_by_sub) is None:
            violations.append((subjects, student_ids))
        print("no violation")

    print("done checking baskets")
    return violations