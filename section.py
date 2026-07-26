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
    en_mask = 1<<0              #EN in column 0
    band_mask = (1<<1) | (1<<2) #Band in col 1 or 2
    choice_mask = 0xFF & ~(en_mask | band_mask) #Choice un all other cols.

    for sec in sections:
        if sec.subject == "EN":
            sec.dom = en_mask
        elif sec.subject in c.BAND:
            sec.dom = band_mask
        else :
            sec.dom = choice_mask
