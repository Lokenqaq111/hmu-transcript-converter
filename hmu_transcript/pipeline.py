from __future__ import annotations

from pathlib import Path

from .extract import extract_pdf
from .models import ConversionResult
from .parse import is_category, parse_transcript


def convert_pdf(pdf_path: str | Path, *, ocr: bool = True) -> ConversionResult:
    path = Path(pdf_path).expanduser()
    extracted = extract_pdf(path, ocr=ocr)
    courses = parse_transcript(extracted.text, extracted.tables)
    warnings = _collect_warnings(courses, extracted.text)
    return ConversionResult(
        source=str(path),
        text=extracted.text,
        courses=courses,
        used_ocr=extracted.used_ocr,
        warnings=warnings,
    )


def _collect_warnings(courses, text: str) -> list[str]:
    warnings: list[str] = []
    if not courses:
        warnings.append("自动解析为 0 门课。请打开提取出的文本检查排版，或改用表格更清晰的电子版 PDF。")
        return warnings
    category_markers = sum(1 for line in text.splitlines() if is_category(line.strip()))
    if category_markers >= 6 and len(courses) < category_markers * 0.6:
        warnings.append(f"只解析到 {len(courses)} 门课，可能漏读。请对照 CSV 与原始成绩单。")
    missing_score = sum(1 for c in courses if c.score100 is None and "不计入学分加权" not in c.notes)
    if missing_score:
        warnings.append(f"有 {missing_score} 门课缺少可用百分制成绩，未计入加权。")
    return warnings
