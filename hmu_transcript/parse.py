from __future__ import annotations

import re

from .models import Course
from .scales import (
    PASS_FAIL_WORDS,
    apply_scales,
    interpret_point_column,
    parse_grade_word,
)

CATEGORIES = {
    "必修",
    "选修",
    "任选",
    "限选",
    "实践",
    "通识",
    "公选",
    "专业必修",
    "专业选修",
    "公共必修",
    "公共选修",
    "集中实践",
    "实验",
    "其他",
}

CATEGORY_RE = re.compile(
    r"^(?:专业|公共|通识|学科|综合)?(?:必修|选修|任选|限选|实践)|通识|公选|实验|集中实践|其他$"
)

CATEGORY_TOKEN = (
    r"(?:专业|公共|通识|学科|综合)?(?:必修|选修|任选|限选|实践)|通识|公选|实验|集中实践|其他"
)

SINGLE_LINE_RE = re.compile(
    rf"^(?P<course>.+?)\s+(?P<category>{CATEGORY_TOKEN})\s+"
    rf"(?P<credit>\d+(?:\.\d+)?)\s+(?P<rest>.+)$"
)

YEAR_RE = re.compile(r"^20\d{2}\s*[-–—~/]\s*20\d{2}(?:学年)?$")
SEMESTER_RE = re.compile(r"^(?:[123]|第[一二三123]学期|春|秋|夏)$")
NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")
LEADING_INDEX_RE = re.compile(r"^\d+[\.、\)]\s*")

EXACT_HEADERS = {
    "院(系)",
    "院（系）",
    "培养层次",
    "学制",
    "入学时间",
    "学号",
    "专业",
    "行政班级",
    "毕业时间",
    "姓名",
    "性别",
    "课程/环节",
    "课程",
    "环节",
    "类别",
    "学分",
    "成绩",
    "绩点",
    "学年",
    "学期",
    "平均成绩",
    "身份证号",
}

CONTAINS_NOISE = (
    "学生成绩档案表",
    "打印日期",
    "成绩审查",
    "获得等级考试证书",
    "教务处盖章",
    "毕业论文题目",
    "毕业设计题目",
    "--------------------------------",
)

HEADER_ALIASES = {
    "course": ("课程/环节", "课程名称", "课程", "环节"),
    "category": ("课程类别", "类别", "性质"),
    "credit": ("学分",),
    "score": ("考核成绩", "成绩"),
    "gpa": ("学分绩点", "绩点"),
    "year": ("学年",),
    "semester": ("学期",),
}


def parse_transcript(text: str, tables: list[list[list[str | None]]] | None = None) -> list[Course]:
    rows: list[Course] = []
    if tables:
        rows.extend(_parse_tables(tables))
    rows.extend(_parse_text(text or ""))
    rows = _dedupe(rows)
    for row in rows:
        apply_scales(row)
    return rows


def is_category(value: str) -> bool:
    text = value.strip()
    return text in CATEGORIES or CATEGORY_RE.fullmatch(text) is not None


def is_year(value: str) -> bool:
    return YEAR_RE.fullmatch(value.strip()) is not None


def is_semester(value: str) -> bool:
    return SEMESTER_RE.fullmatch(value.strip()) is not None


def is_number_line(value: str) -> bool:
    return NUMBER_RE.fullmatch(value.strip()) is not None


def is_noise(value: str) -> bool:
    text = value.strip()
    if not text or text in EXACT_HEADERS:
        return True
    if any(token in text for token in CONTAINS_NOISE):
        return True
    if re.fullmatch(r"[-—_=]{5,}", text):
        return True
    return False


def parse_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return None


def _parse_text(text: str) -> list[Course]:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]
    rows: list[Course] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _skip_standalone(line):
            i += 1
            continue

        single = _parse_single_line(line)
        if single:
            rows.append(single)
            i += 1
            continue

        block, consumed = _parse_block(lines, i)
        if block and consumed:
            rows.append(block)
            i += consumed
            continue

        i += 1
    return rows


def _skip_standalone(line: str) -> bool:
    return (
        is_noise(line)
        or is_number_line(line)
        or is_category(line)
        or is_year(line)
        or is_semester(line)
    )


def _parse_single_line(line: str) -> Course | None:
    match = SINGLE_LINE_RE.match(line)
    if not match:
        return None
    course = _clean_course_name(match.group("course"))
    if not course or is_noise(course) or is_category(course):
        return None
    credit = parse_float(match.group("credit"))
    rest_tokens = match.group("rest").split()
    score_tokens: list[str] = []
    for tok in rest_tokens:
        if is_year(tok) or is_semester(tok):
            break
        score_tokens.append(tok)
    return _course_from_parts(
        course=course,
        category=match.group("category").strip(),
        credit=credit,
        raw_score_text=" ".join(score_tokens) or match.group("rest").strip(),
        extra_tokens=rest_tokens,
    )


def _parse_block(lines: list[str], i: int) -> tuple[Course | None, int]:
    if i + 2 >= len(lines):
        return None, 0
    course = _clean_course_name(lines[i])
    if not course or is_noise(course) or is_category(course) or is_number_line(course):
        return None, 0
    if not is_category(lines[i + 1]) or not is_number_line(lines[i + 2]):
        return None, 0

    category = lines[i + 1]
    credit = parse_float(lines[i + 2])
    j = i + 3
    if j >= len(lines):
        return None, 0

    tokens: list[str] = []
    score_line = lines[j]
    tokens.extend(score_line.split())
    j += 1

    if j < len(lines) and _looks_like_point_value(lines[j]):
        tokens.append(lines[j])
        j += 1
    if j < len(lines) and is_year(lines[j]):
        tokens.append(lines[j])
        j += 1
    if j < len(lines) and is_semester(lines[j]):
        tokens.append(lines[j])
        j += 1

    course_obj = _course_from_parts(
        course=course,
        category=category,
        credit=credit,
        raw_score_text=score_line,
        extra_tokens=tokens,
    )
    return course_obj, j - i


def _course_from_parts(
    *,
    course: str,
    category: str,
    credit: float | None,
    raw_score_text: str,
    extra_tokens: list[str],
) -> Course:
    grade_word, grade_score = parse_grade_word(raw_score_text)
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", " ".join(extra_tokens))]
    year = next((normalize_year(tok) for tok in extra_tokens if is_year(tok)), "")
    semester = next((normalize_semester(tok) for tok in extra_tokens if is_semester(tok)), "")

    score: float | None = grade_score
    point_num: float | None = None

    leftover = [n for n in nums if not _is_year_number(n, extra_tokens) and not _is_semester_number(n, extra_tokens, year)]
    # 学年里的 2019/2020 也会被 findall 抓到，先去掉 1900+ 的整数
    leftover = [n for n in leftover if not (n >= 1900 and float(n).is_integer())]

    if grade_word:
        if leftover:
            point_num = leftover[0]
    elif leftover:
        first = leftover[0]
        if first <= 100:
            score = first
        if len(leftover) >= 2:
            second = leftover[1]
            # 没有学年时，尾部整数 1/2/3 更像学期，而不是绩点 1.0/2.0/3.0
            if second in {1.0, 2.0, 3.0} and float(second).is_integer() and not year and not semester:
                semester = str(int(second))
            else:
                point_num = second
        elif first > 100:
            point_num = first

    gpa_cn = None
    if point_num is not None:
        gpa_cn, _ = interpret_point_column(point_num, credit)

    notes = []
    if any(word in raw_score_text for word in PASS_FAIL_WORDS):
        notes.append("通过/不通过课程，不计入学分加权")
        if "不通过" in raw_score_text:
            score = 0.0

    row = Course(
        course=course,
        category=category,
        credit=credit,
        score_raw=raw_score_text.strip(),
        score100=score,
        gpa_cn=gpa_cn,
        year=year,
        semester=semester,
        notes="；".join(notes),
    )
    return row


def _is_year_number(num: float, tokens: list[str]) -> bool:
    if not (num >= 1900 and float(num).is_integer()):
        return False
    return any(is_year(tok) and f"{int(num)}" in tok for tok in tokens)


def _is_semester_number(num: float, tokens: list[str], year: str) -> bool:
    if num not in {1.0, 2.0, 3.0} or not float(num).is_integer():
        return False
    if not year:
        return False
    return any(is_semester(tok) and tok.strip() in {"1", "2", "3"} for tok in tokens)


def _looks_like_point_value(value: str) -> bool:
    if not is_number_line(value):
        return False
    number = float(value)
    if number > 5:
        return True
    if "." in value:
        return True
    return number >= 4


def _clean_course_name(name: str) -> str:
    text = LEADING_INDEX_RE.sub("", re.sub(r"\s+", " ", name).strip())
    if "。" in text or len(text) > 60:
        return ""
    return text


def normalize_year(value: str) -> str:
    text = re.sub(r"\s+", "", value.strip())
    text = text.replace("—", "-").replace("–", "-").replace("~", "-").replace("/", "-")
    return re.sub(r"学年$", "", text)


def normalize_semester(value: str) -> str:
    text = value.strip()
    mapping = {
        "第一学期": "1",
        "第二学期": "2",
        "第三学期": "3",
        "第1学期": "1",
        "第2学期": "2",
        "第3学期": "3",
        "春": "1",
        "秋": "2",
        "夏": "3",
    }
    return mapping.get(text, text)


def _parse_tables(tables: list[list[list[str | None]]]) -> list[Course]:
    rows: list[Course] = []
    for table in tables:
        header_idx, mapping = _find_header(table)
        if mapping is not None and header_idx is not None:
            for raw in table[header_idx + 1 :]:
                course = _course_from_table_row(raw, mapping)
                if course:
                    rows.append(course)
            continue
        for raw in table:
            cells = [_cell_text(c) for c in raw if _cell_text(c)]
            if not cells:
                continue
            joined = " ".join(cells)
            single = _parse_single_line(joined)
            if single:
                rows.append(single)
    return rows


def _find_header(table: list[list[str | None]]) -> tuple[int | None, dict[str, int] | None]:
    for idx, raw in enumerate(table[:8]):
        cells = [_norm_header(_cell_text(c)) for c in raw]
        mapping: dict[str, int] = {}
        for field, aliases in HEADER_ALIASES.items():
            for col, cell in enumerate(cells):
                if any(_norm_header(alias) == cell for alias in aliases):
                    mapping[field] = col
                    break
        if "course" in mapping and ("credit" in mapping or "score" in mapping):
            return idx, mapping
    return None, None


def _course_from_table_row(raw: list[str | None], mapping: dict[str, int]) -> Course | None:
    def col(key: str) -> str:
        idx = mapping.get(key)
        if idx is None or idx >= len(raw):
            return ""
        return _cell_text(raw[idx])

    course = _clean_course_name(col("course"))
    if not course or is_noise(course) or is_number_line(course):
        return None

    category = col("category")
    credit = parse_float(col("credit"))
    score_text = col("score") or col("gpa")
    tokens = [part for part in (score_text, col("gpa"), col("year"), col("semester")) if part]
    if category and not is_category(category):
        # 有些表把类别写成「专业必修课」等，尽量保留原文
        pass

    return _course_from_parts(
        course=course,
        category=category,
        credit=credit,
        raw_score_text=score_text,
        extra_tokens=tokens,
    )


def _cell_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _dedupe(courses: list[Course]) -> list[Course]:
    seen: set[tuple] = set()
    out: list[Course] = []
    for row in courses:
        key = (
            row.course,
            row.category,
            row.credit,
            row.year,
            row.semester,
            round(row.score100, 2) if row.score100 is not None else None,
            row.score_raw,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out
