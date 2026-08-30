from hmu_transcript.models import Course
from hmu_transcript.scales import (
    apply_scales,
    interpret_point_column,
    parse_grade_word,
    score_from_cn_gpa,
    to_au_7,
    to_canada_4,
    to_nz_7,
    to_nz_9,
    to_uk_class,
    weighted_avg,
)


def test_grade_words_prefer_long_match():
    word, score = parse_grade_word("良好 3.70")
    assert word == "良好"
    assert score == 85.0


def test_short_grade_does_not_match_inside_course_like_text():
    word, score = parse_grade_word("中国近现代史纲要")
    assert word is None
    assert score is None


def test_short_grade_exact():
    word, score = parse_grade_word("优")
    assert word == "优"
    assert score == 95.0


def test_score_from_cn_gpa_four_point():
    assert score_from_cn_gpa(4.0) == 90.0
    assert score_from_cn_gpa(3.0) == 80.0
    assert score_from_cn_gpa(1.0) == 60.0


def test_interpret_point_column_distinguishes_gpa_and_credit_point():
    gpa, credit_point = interpret_point_column(3.5, 3.5)
    assert gpa == 3.5
    assert credit_point == 12.25

    gpa, credit_point = interpret_point_column(12.25, 3.5)
    assert gpa == 3.5
    assert credit_point == 12.25


def test_au_nz_boundaries_differ():
    assert to_au_7(84) == 6.0
    assert to_nz_7(84) == 6.0
    assert to_au_7(74) == 5.0
    assert to_nz_7(74) == 4.0
    assert to_nz_9(90) == 9.0
    assert to_nz_9(89) == 8.0
    assert to_au_7(49.9) == 0.0
    assert to_nz_7(50) == 2.0


def test_canada_and_uk_class():
    assert to_canada_4(90) == 4.0
    assert to_canada_4(80) == 3.7
    assert to_canada_4(49) == 0.0
    assert to_uk_class(85) == "First"
    assert to_uk_class(75) == "2:1"
    assert to_uk_class(65) == "2:2"
    assert to_uk_class(60) == "Third"
    assert to_uk_class(59) == "Fail"


def test_apply_scales_infers_score_from_gpa():
    course = Course(course="测试", credit=2.0, gpa_cn=3.0)
    apply_scales(course)
    assert course.score100 == 80.0
    assert course.au7 == 6.0
    assert "回推" in course.notes


def test_weighted_avg_skips_missing():
    rows = [
        Course(course="a", credit=2, score100=80),
        Course(course="b", credit=None, score100=100),
        Course(course="c", credit=2, score100=None),
        Course(course="d", credit=2, score100=100),
    ]
    assert weighted_avg(rows, "score100") == 90.0
