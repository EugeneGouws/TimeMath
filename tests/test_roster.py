import roster as r


def count_by_grade(students):
    counts = {}
    for s in students:
        counts[s.grade] = counts.get(s.grade, 0) + 1
    return counts


def test_2026():
    students = r.parse_student("Phase01_2026.xlsx")
    counts = count_by_grade(students)

    assert counts[10] == 99, f"Gr10 expected 99, got {counts[10]}"
    assert counts[11] == 90, f"Gr11 expected 90, got {counts[11]}"
    assert counts[12] == 81, f"Gr12 expected 81, got {counts[12]}"

    print("2026 OK:", counts)


def test_2025():
    students = r.parse_student("Phase01_2025.xlsx")
    counts = count_by_grade(students)

    # raw counts, before exception handling (ids 7/44 not yet removed)
    assert counts[10] == 89, f"Gr10 expected 89, got {counts[10]}"
    assert counts[11] == 77, f"Gr11 expected 77, got {counts[11]}"
    assert counts[12] == 98, f"Gr12 expected 98 (raw), got {counts[12]}"

    print("2025 OK:", counts)


if __name__ == "__main__":
    test_2026()
    test_2025()
