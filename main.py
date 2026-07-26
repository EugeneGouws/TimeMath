import roster as r
from constants import getM
import section as s

senior_students = r.parse_student("Phase01_2026.xlsx")
exist = r.existence(senior_students)

enrol12 = r.enrol(senior_students, 12)
floor12 = r.floors(senior_students, 12)
baskets12 = r.baskets(senior_students, 12)

sections12 = s.build_sections(senior_students, 12)
s.pin_universal(sections12)
for t in sections12:
    print(t)