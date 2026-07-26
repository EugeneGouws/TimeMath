import roster as r

senior_students = r.parse_student("Phase01_2026.xlsx")
exist = r.existence(senior_students)

#Check exist
for subj in sorted(exist):
    print(subj, sorted(exist[subj]))