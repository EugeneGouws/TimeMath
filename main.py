import roster as r
from constants import getM
import section as s

senior_students = r.parse_student("Phase01_2026.xlsx")

sections = s.build_sections(senior_students, 10)
s.pin_universal(sections)
viol = s.check_baskets(senior_students,10,sections)

for v in viol:
    print(v)