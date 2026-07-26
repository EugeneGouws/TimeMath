from dataclasses import dataclass
from openpyxl import load_workbook
import constants as c
import math

@dataclass(frozen=True)
class Student:
    id: int
    grade: int
    subjects: frozenset[str]

@dataclass(frozen = True)
class Section:
    subject: str
    gr: int


# functions------------------------------------
def parse_student(path: str) -> list[Student]:
    wb = load_workbook(path, data_only=True)
    ws = wb["Roster"]

    students: list[Student] = []
    header_row = ws[1]
    headers = []
    for cell in header_row:
        headers.append(cell.value)

    id_col = headers.index("Id")
    gr_col = headers.index("Grade")

    s_cols = []
    for i in range(len(headers)):
        if headers[i] is not None and headers[i].startswith("S"):
            s_cols.append(i)

    for row in ws.iter_rows(min_row=2):
        if row[id_col].value is None:
            continue
        s_id = int(row[id_col].value)
        s_gr = int(row[gr_col].value)
        s_subjects = []

        for i in s_cols:
            sub = row[i].value
            if sub is None:
                continue
            code = sub.strip().upper()
            if code in s_subjects:
                raise ValueError(f"student {s_id}: duplicate subject {code}")
            s_subjects.append(code)

        student = Student(id=s_id, grade=s_gr, subjects=frozenset(s_subjects))
        students.append(student)

    return students

#------------------------------------------------------------
def existence(students: list[Student]) -> dict[str, frozenset[int]]:
    table = {}
    for student in students:
        for s in student.subjects:
            if s not in table:
                table[s] = set()
            table[s].add(student.grade)

    result = {}
    for s in table:
        result[s] = frozenset(table[s])
    return result

#---------------------------------------------------------------
def enrol(students: list[Student], gr: int) -> dict[str, frozenset[int]]:
    table = {}
    for student in students:
        if student.grade != gr:
            continue
        for s in student.subjects:
            if s not in table:
                table[s] = set()
            table[s].add(student.id)

    result = {}
    for s in table:
        result[s] = frozenset(table[s])
    return result

#-----------------------------------------------------------
def floors(students: list[Student], gr: int, cap: int = c.CLASS_CAP) -> dict[str, int]:
    e = enrol(students, gr)

    result = {}
    for s in e:
        result[s] = math.ceil(len(e[s]) / cap)
    return result

#----------------------------------------------------------
def baskets(students: list[Student], gr: int) -> dict[frozenset[str], frozenset[int]]:
    table = {}
    for student in students:
        if student.grade != gr:
            continue
        key = student.subjects - c.UNIVERSAL
        if key not in table:
            table[key] = set()
        table[key].add(student.id)

    result = {}
    for s in table:
        result[s] = frozenset(table[s])
    return result


