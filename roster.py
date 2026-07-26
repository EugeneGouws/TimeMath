from dataclasses import dataclass
from openpyxl import load_workbook
import constants as C
import math

@dataclass(frozen=True)
class Student:
    id: int
    grade: int
    subjects: frozenset[str]


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

    #print("headers:", headers)
    #print("id_col:", id_col)
    #print("gr_col:", gr_col)
    #print("s_cols:", s_cols, "->", [headers[i] for i in s_cols])

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

    #print(students[:3])

    return students

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

def floors(students: list[Student], grade: int, cap: int = C.CLASS_CAP) -> dict[str, int]:
    
