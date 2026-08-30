from tests.fixtures import SAMPLE_TABLE, SAMPLE_TEXT
from hmu_transcript.parse import parse_transcript


def _by_name(courses):
    return {c.course: c for c in courses}


def test_parse_sample_text_keeps_thesis_and_skips_headers():
    courses = parse_transcript(SAMPLE_TEXT)
    names = [c.course for c in courses]

    assert "人体解剖学" in names
    assert "毕业设计" in names
    assert "中国近现代史纲要" in names
    assert "健康评估" in names
    assert "军事训练" in names
    assert "平均成绩" not in names
    assert "测试学生" not in names
    assert "护理实习生临床适应研究" not in names


def test_parse_score_and_credit_point_same_line():
    anatomy = _by_name(parse_transcript(SAMPLE_TEXT))["人体解剖学"]
    assert anatomy.category == "必修"
    assert anatomy.credit == 3.5
    assert anatomy.score100 == 87.0
    assert anatomy.gpa_cn == 3.5
    assert anatomy.year == "2019-2020"
    assert anatomy.semester == "1"


def test_parse_letter_grade_and_gpa_line():
    physio = _by_name(parse_transcript(SAMPLE_TEXT))["生理学"]
    assert physio.score100 == 85.0
    assert physio.gpa_cn == 3.7
    assert physio.year == "2019-2020"
    assert physio.semester == "2"


def test_parse_excellent_without_gpa():
    ethics = _by_name(parse_transcript(SAMPLE_TEXT))["医学伦理学"]
    assert ethics.category == "选修"
    assert ethics.score100 == 95.0
    assert ethics.uk_class == "First"


def test_course_name_containing_zhong_is_not_a_grade():
    history = _by_name(parse_transcript(SAMPLE_TEXT))["中国近现代史纲要"]
    assert history.score100 == 78.0
    assert history.gpa_cn == 2.8


def test_single_line_record():
    assess = _by_name(parse_transcript(SAMPLE_TEXT))["健康评估"]
    assert assess.credit == 3.0
    assert assess.score100 == 92.0
    assert assess.gpa_cn == 4.0
    assert assess.year == "2020-2021"
    assert assess.semester == "1"
    assert assess.au7 == 7.0


def test_pass_fail_excluded_from_gpa_flag():
    drill = _by_name(parse_transcript(SAMPLE_TEXT))["军事训练"]
    assert drill.counts_toward_gpa is False
    assert "不计入学分加权" in drill.notes


def test_parse_table_rows():
    courses = parse_transcript("", tables=[SAMPLE_TABLE])
    names = _by_name(courses)
    assert names["病理学"].score100 == 81.0
    assert names["病理学"].gpa_cn == 3.1
    assert names["护理学导论"].score100 == 85.0
    assert names["护理学导论"].category == "选修"


def test_year_with_suffix_and_trailing_semester():
    text = "外科护理学\n必修\n4.0\n83.0\n2021-2022学年\n2\n"
    course = _by_name(parse_transcript(text))["外科护理学"]
    assert course.score100 == 83.0
    assert course.year == "2021-2022"
    assert course.semester == "2"
    assert course.gpa_cn is None


def test_dedupe_table_and_text():
    text = "病理学\n必修\n4.0\n81.0\n3.10\n2020-2021\n2\n"
    courses = parse_transcript(text, tables=[SAMPLE_TABLE])
    pathology = [c for c in courses if c.course == "病理学"]
    assert len(pathology) == 1
