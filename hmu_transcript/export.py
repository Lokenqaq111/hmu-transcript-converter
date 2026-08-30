from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .models import ConversionResult, Course, WeightedSummary
from .scales import build_summary

CSV_COLUMNS = [
    ("course", "课程"),
    ("category", "类别"),
    ("credit", "学分"),
    ("year", "学年"),
    ("semester", "学期"),
    ("score_raw", "原始成绩"),
    ("score100", "百分制"),
    ("gpa_cn", "中国绩点"),
    ("nz7", "NZ_7"),
    ("nz9", "NZ_9"),
    ("au7", "AU_7"),
    ("uk_pct", "UK百分制"),
    ("uk_class", "UK等级"),
    ("ca4", "Canada_4"),
    ("notes", "备注"),
]


def format_number(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def summarize(result: ConversionResult) -> list[WeightedSummary]:
    all_rows = result.iter_gpa_courses()
    required = result.iter_gpa_courses({"必修", "专业必修", "公共必修"})
    summaries = [build_summary("全部课程（学分加权）", all_rows)]
    if required and len(required) != len(all_rows):
        summaries.append(build_summary("仅必修（学分加权）", required))
    return summaries


def write_csv(path: str | Path, result: ConversionResult) -> None:
    path = Path(path)
    summaries = summarize(result)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([label for _, label in CSV_COLUMNS])
        for row in result.courses:
            writer.writerow(_csv_row(row))
        if summaries:
            writer.writerow([])
            for item in summaries:
                writer.writerow(_summary_row(item))


def write_json(path: str | Path, result: ConversionResult) -> None:
    payload = {
        "source": result.source,
        "used_ocr": result.used_ocr,
        "warnings": result.warnings,
        "courses": [asdict(c) for c in result.courses],
        "summary": [item.as_dict() for item in summarize(result)],
    }
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_text(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def render_terminal(result: ConversionResult) -> str:
    lines = [
        "=== 海南医科大学成绩单转换 ===",
        f"文件: {result.source}",
        f"解析课程: {len(result.courses)} 门",
    ]
    if result.used_ocr:
        lines.append("文本提取: 已使用 OCR")
    for warning in result.warnings:
        lines.append(f"注意: {warning}")

    for item in summarize(result):
        lines.append("")
        lines.append(f"--- {item.label} ---")
        lines.append(f"计入课程 / 学分: {item.course_count} 门 / {format_number(item.credit_total, 2)}")
        lines.append(f"百分制(UK可参考): {format_number(item.score100)}")
        lines.append(f"NZ 7分制 GPA:      {format_number(item.nz7)}")
        lines.append(f"NZ 9分制 GPA:      {format_number(item.nz9)}")
        lines.append(f"AU 7分制 GPA:      {format_number(item.au7)}")
        lines.append(f"Canada 4分制 GPA:  {format_number(item.ca4)}")
        if item.uk_class:
            lines.append(f"UK 等级参考:       {item.uk_class}")
    return "\n".join(lines)


def _csv_row(row: Course) -> list[str]:
    values: list[str] = []
    for key, _ in CSV_COLUMNS:
        value = getattr(row, key)
        if isinstance(value, float):
            values.append(format_number(value, 3 if key in {"gpa_cn", "nz7", "nz9", "au7", "ca4", "score100", "uk_pct"} else 2))
        elif value is None:
            values.append("")
        else:
            values.append(str(value))
    return values


def _summary_row(item: WeightedSummary) -> list[str]:
    return [
        item.label,
        "",
        format_number(item.credit_total, 2),
        "",
        "",
        "",
        format_number(item.score100),
        "",
        format_number(item.nz7),
        format_number(item.nz9),
        format_number(item.au7),
        format_number(item.score100),
        item.uk_class,
        format_number(item.ca4),
        f"{item.course_count}门计入加权",
    ]
