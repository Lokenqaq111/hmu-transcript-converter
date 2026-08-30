from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass
class Course:
    course: str
    category: str = ""
    credit: float | None = None
    score_raw: str = ""
    score100: float | None = None
    gpa_cn: float | None = None
    year: str = ""
    semester: str = ""
    nz7: float | None = None
    nz9: float | None = None
    au7: float | None = None
    uk_pct: float | None = None
    uk_class: str = ""
    ca4: float | None = None
    notes: str = ""

    @property
    def counts_toward_gpa(self) -> bool:
        return "不计入学分加权" not in self.notes


@dataclass
class ExtractedDocument:
    text: str
    tables: list[list[list[str | None]]] = field(default_factory=list)
    used_ocr: bool = False


@dataclass
class WeightedSummary:
    label: str
    course_count: int
    credit_total: float
    score100: float | None = None
    nz7: float | None = None
    nz9: float | None = None
    au7: float | None = None
    ca4: float | None = None
    uk_class: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConversionResult:
    source: str
    text: str
    courses: list[Course]
    used_ocr: bool = False
    warnings: list[str] = field(default_factory=list)

    def iter_gpa_courses(self, categories: Iterable[str] | None = None) -> list[Course]:
        rows = [c for c in self.courses if c.counts_toward_gpa]
        if categories is None:
            return rows
        wanted = set(categories)
        return [c for c in rows if c.category in wanted]
