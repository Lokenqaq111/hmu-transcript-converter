from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .models import ExtractedDocument

MIN_TEXT_CHARS = 200
TESSERACT_CANDIDATES = (
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/usr/bin/tesseract",
)


def ensure_pymupdf() -> None:
    try:
        import pymupdf  # noqa: F401
        return
    except ImportError:
        pass

    print("未检测到 PyMuPDF，正在安装…")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pymupdf"],
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "安装 PyMuPDF 失败。请手动执行: python3 -m pip install pymupdf"
        ) from exc

    try:
        import pymupdf  # noqa: F401
    except ImportError as exc:
        raise SystemExit("已尝试安装 PyMuPDF，但仍无法导入。") from exc


def extract_pdf(pdf_path: str | Path, *, ocr: bool = True) -> ExtractedDocument:
    ensure_pymupdf()
    import pymupdf

    path = Path(pdf_path)
    doc = pymupdf.open(path)
    try:
        if doc.needs_pass:
            raise SystemExit(f"PDF 已加密，请先解除密码: {path}")

        text_parts: list[str] = []
        tables: list[list[list[str | None]]] = []
        for page in doc:
            with contextlib.redirect_stdout(io.StringIO()):
                text_parts.append(page.get_text("text") or "")
                tables.extend(_extract_tables(page))

        text = "\n".join(text_parts)
        used_ocr = False
        if ocr and len(text.strip()) < MIN_TEXT_CHARS:
            ocr_text = try_ocr(doc)
            if ocr_text.strip():
                text = f"{text.rstrip()}\n{ocr_text}".strip()
                used_ocr = True
        return ExtractedDocument(text=text, tables=tables, used_ocr=used_ocr)
    finally:
        doc.close()


def _extract_tables(page) -> list[list[list[str | None]]]:
    try:
        finder = page.find_tables()
    except Exception:
        return []

    tables = getattr(finder, "tables", finder) or []
    out: list[list[list[str | None]]] = []
    for table in tables:
        try:
            extracted = table.extract()
        except Exception:
            continue
        if extracted:
            out.append(extracted)
    return out


def try_ocr(doc) -> str:
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
    except ImportError:
        return "\n[OCR 未执行：缺少 pytesseract/pillow。扫描件请先: pip3 install pytesseract pillow，并安装 tesseract]\n"

    cmd = _resolve_tesseract()
    if not cmd:
        return "\n[OCR 未执行：未找到 tesseract 可执行文件]\n"
    pytesseract.pytesseract.tesseract_cmd = cmd

    chunks = ["\n[OCR 结果开始]\n"]
    with tempfile.TemporaryDirectory(prefix="hmu_ocr_") as tmp:
        tmp_path = Path(tmp)
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False)
            img_path = tmp_path / f"page_{i}.png"
            pix.save(str(img_path))
            try:
                txt = pytesseract.image_to_string(
                    Image.open(img_path), lang="chi_sim+eng"
                )
            except Exception:
                try:
                    txt = pytesseract.image_to_string(Image.open(img_path), lang="eng")
                except Exception as exc:
                    chunks.append(f"\n--- 第 {i} 页 OCR 失败: {exc} ---\n")
                    continue
            chunks.append(f"\n--- 第 {i} 页 ---\n{txt}\n")
    return "".join(chunks)


def _resolve_tesseract() -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found
    for cmd in TESSERACT_CANDIDATES:
        if os.path.exists(cmd):
            return cmd
    return None
