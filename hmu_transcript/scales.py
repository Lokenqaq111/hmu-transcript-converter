"""留学常用分制参考换算。

这些映射是常见申请参考表，不是目标院校的官方评估。
同一所大学也可能按院系/WES/NARIC 使用不同规则。
"""

from __future__ import annotations

from .models import Course, WeightedSummary

# 五级制 / 等级制 → 百分制中位参考
GRADE_WORDS: list[tuple[str, float]] = [
    ("不及格", 50.0),
    ("不通过", 0.0),
    ("优秀", 95.0),
    ("良好", 85.0),
    ("中等", 75.0),
    ("及格", 60.0),
    ("合格", 65.0),
]

SHORT_GRADE_WORDS = {
    "优": 95.0,
    "良": 85.0,
    "中": 75.0,
    "及": 60.0,
}

PASS_FAIL_WORDS = {"通过", "不通过"}


def parse_grade_word(text: str) -> tuple[str | None, float | None]:
    """从成绩文本里识别等级词。短词（优/良/中/及）只在整段就是该字时生效，避免误伤课程名。"""
    raw = (text or "").strip()
    if not raw:
        return None, None
    for word, value in GRADE_WORDS:
        if word in raw:
            return word, value
    if raw in SHORT_GRADE_WORDS:
        return raw, SHORT_GRADE_WORDS[raw]
    return None, None


def clamp_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def score_from_cn_gpa(gpa: float) -> float | None:
    """用国内绩点粗略回推百分制。

    多数高校 4 分制接近：绩点 ≈ max(0, (百分制 - 50) / 10)。
    90–100 常都记 4.0，因此回推值只是中位参考。
    """
    if gpa < 0:
        return None
    if gpa <= 4.3:
        return clamp_score(gpa * 10.0 + 50.0)
    if gpa <= 5.0:
        return clamp_score(gpa / 5.0 * 100.0)
    return None


def interpret_point_column(num: float, credit: float | None) -> tuple[float | None, float | None]:
    """区分「绩点」和「学分绩点」。

    绩点通常 ≤ 5；学分绩点 = 学分 × 绩点，往往明显更大。
    返回 (gpa_cn, credit_point)。
    """
    if num <= 5.0:
        credit_point = num * credit if credit else None
        return num, credit_point
    if credit and credit > 0:
        gpa = num / credit
        if 0 <= gpa <= 5.0:
            return gpa, num
    return None, num


def to_nz_7(score100: float) -> float:
    """新西兰 7 分制参考（按百分制区间，细于澳制 HD/D/C/P）。"""
    s = score100
    if s >= 85:
        return 7.0
    if s >= 80:
        return 6.0
    if s >= 75:
        return 5.0
    if s >= 70:
        return 4.0
    if s >= 65:
        return 3.0
    if s >= 50:
        return 2.0
    return 0.0


def to_nz_9(score100: float) -> float:
    """新西兰 9 分制参考（接近奥克兰大学常见百分制区间）。"""
    s = score100
    if s >= 90:
        return 9.0
    if s >= 85:
        return 8.0
    if s >= 80:
        return 7.0
    if s >= 75:
        return 6.0
    if s >= 70:
        return 5.0
    if s >= 65:
        return 4.0
    if s >= 60:
        return 3.0
    if s >= 55:
        return 2.0
    if s >= 50:
        return 1.0
    return 0.0


def to_au_7(score100: float) -> float:
    """澳大利亚 7 分制常见对应：HD7 / D6 / C5 / P4 / F0。"""
    s = score100
    if s >= 85:
        return 7.0
    if s >= 75:
        return 6.0
    if s >= 65:
        return 5.0
    if s >= 50:
        return 4.0
    return 0.0


def to_canada_4(score100: float) -> float:
    """加拿大 4 分制常见细表（偏 Ontario 百分制区间）。"""
    s = score100
    if s >= 90:
        return 4.0
    if s >= 85:
        return 3.9
    if s >= 80:
        return 3.7
    if s >= 77:
        return 3.3
    if s >= 73:
        return 3.0
    if s >= 70:
        return 2.7
    if s >= 67:
        return 2.3
    if s >= 63:
        return 2.0
    if s >= 60:
        return 1.7
    if s >= 57:
        return 1.3
    if s >= 53:
        return 1.0
    if s >= 50:
        return 0.7
    return 0.0


def to_uk_class(score100: float) -> str:
    """用中国百分制估 UK 荣誉等级。国内 85+ 通常对标 First，不是把 70 当成一等。"""
    s = score100
    if s >= 85:
        return "First"
    if s >= 75:
        return "2:1"
    if s >= 65:
        return "2:2"
    if s >= 60:
        return "Third"
    return "Fail"


def apply_scales(course: Course) -> Course:
    if course.score100 is None and course.gpa_cn is not None:
        inferred = score_from_cn_gpa(course.gpa_cn)
        if inferred is not None:
            course.score100 = inferred
            _add_note(course, "百分制由绩点回推，仅供参考")

    score = course.score100
    if score is None:
        return course

    course.nz7 = to_nz_7(score)
    course.nz9 = to_nz_9(score)
    course.au7 = to_au_7(score)
    course.uk_pct = score
    course.uk_class = to_uk_class(score)
    course.ca4 = to_canada_4(score)
    return course


def weighted_avg(courses: list[Course], key: str) -> float | None:
    total_c = 0.0
    total_v = 0.0
    for row in courses:
        credit = row.credit
        value = getattr(row, key, None)
        if credit is None or credit <= 0 or value is None:
            continue
        if isinstance(value, str):
            continue
        total_c += credit
        total_v += credit * float(value)
    if total_c == 0:
        return None
    return total_v / total_c


def credit_total(courses: list[Course]) -> float:
    return sum(c.credit or 0.0 for c in courses if c.credit and c.credit > 0)


def build_summary(label: str, courses: list[Course]) -> WeightedSummary:
    score = weighted_avg(courses, "score100")
    return WeightedSummary(
        label=label,
        course_count=len(courses),
        credit_total=credit_total(courses),
        score100=score,
        nz7=weighted_avg(courses, "nz7"),
        nz9=weighted_avg(courses, "nz9"),
        au7=weighted_avg(courses, "au7"),
        ca4=weighted_avg(courses, "ca4"),
        uk_class=to_uk_class(score) if score is not None else "",
    )


def _add_note(course: Course, note: str) -> None:
    if note in course.notes:
        return
    course.notes = f"{course.notes}；{note}" if course.notes else note
