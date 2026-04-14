#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最简版：国内成绩单 PDF -> 提取课程/学分/成绩/绩点 -> 转换为 NZ/AU 7分制、UK百分制、Canada 4分制

用法：
python3 ~/Desktop/transcript_converter.py ~/Desktop/你的成绩单.pdf

输出：
1) 同目录: xxx_extracted_text.txt
2) 同目录: xxx_converted.csv
3) 终端打印加权均分与各体系加权GPA

说明：
- 优先直接提取 PDF 文本（适合电子版成绩单）
- 若文本很少，会尝试 OCR（需要: pip install pytesseract pillow && 系统装 tesseract）
- 如果自动解析失败，可先看 extracted_text，按 CSV 模板手改后再用 Excel
"""

import csv
import os
import re
import sys
from typing import List, Dict, Optional


def ensure_deps():
    try:
        import fitz  # PyMuPDF
    except Exception:
        print("缺少依赖 PyMuPDF，正在安装...")
        os.system(f"{sys.executable} -m pip install pymupdf >/dev/null 2>&1")


def extract_text_from_pdf(pdf_path: str) -> str:
    import fitz
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text("text"))
    text = "\n".join(text_parts)

    # 文本太少，尝试 OCR
    if len(text.strip()) < 200:
        text = text + "\n" + try_ocr(doc)
    return text


def try_ocr(doc) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except Exception:
        return "\n[OCR 未执行：缺少 pytesseract/pillow 依赖]"

    # macOS 常见 tesseract 路径
    possible_cmds = [
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for cmd in possible_cmds:
        if os.path.exists(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
            break

    ocr_texts = ["\n[OCR 结果开始]\n"]
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_path = f"/tmp/transcript_page_{i+1}.png"
        pix.save(img_path)
        try:
            txt = pytesseract.image_to_string(Image.open(img_path), lang="chi_sim+eng")
            ocr_texts.append(f"\n--- Page {i+1} ---\n{txt}\n")
        except Exception as e:
            ocr_texts.append(f"\n--- Page {i+1} OCR失败: {e} ---\n")
    return "\n".join(ocr_texts)


def parse_float(s: str) -> Optional[float]:
    try:
        return float(s)
    except Exception:
        return None


def normalize_score(score: Optional[float], gpa_cn: Optional[float]) -> Optional[float]:
    if score is not None:
        return max(0.0, min(100.0, score))
    if gpa_cn is None:
        return None

    # 仅有绩点时，粗略回推（最简版）
    if gpa_cn <= 4.3:
        return max(0.0, min(100.0, gpa_cn / 4.0 * 100.0))
    if gpa_cn <= 5.0:
        return max(0.0, min(100.0, gpa_cn / 5.0 * 100.0))
    return None


def to_nz_au_7(score100: Optional[float]) -> Optional[float]:
    if score100 is None:
        return None
    s = score100
    if s >= 85:
        return 7.0
    if s >= 80:
        return 6.0
    if s >= 75:
        return 5.0
    if s >= 65:
        return 4.0
    if s >= 50:
        return 3.0
    if s >= 40:
        return 2.0
    return 0.0


def to_canada_4(score100: Optional[float]) -> Optional[float]:
    if score100 is None:
        return None
    s = score100
    if s >= 90: return 4.0
    if s >= 85: return 3.9
    if s >= 80: return 3.7
    if s >= 77: return 3.3
    if s >= 73: return 3.0
    if s >= 70: return 2.7
    if s >= 67: return 2.3
    if s >= 63: return 2.0
    if s >= 60: return 1.7
    if s >= 57: return 1.3
    if s >= 53: return 1.0
    if s >= 50: return 0.7
    return 0.0


def weighted_avg(rows: List[Dict], key: str) -> Optional[float]:
    total_c = 0.0
    total_v = 0.0
    for r in rows:
        c = r.get("credit")
        v = r.get(key)
        if c is None or v is None:
            continue
        total_c += c
        total_v += c * v
    if total_c == 0:
        return None
    return total_v / total_c


def try_parse_rows(text: str) -> List[Dict]:
    rows = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    categories = {"必修", "选修", "任选", "限选", "实践", "通识"}
    grade_map = {
        "优秀": 95.0,
        "良好": 85.0,
        "中等": 75.0,
        "及格": 60.0,
        "合格": 65.0,
        "不及格": 50.0,
    }

    def is_number_line(s: str) -> bool:
        return re.fullmatch(r"\d+(?:\.\d+)?", s) is not None

    def is_noise(s: str) -> bool:
        bad = [
            "海南医科大学学生成绩档案表", "院(系)", "培养层次", "学制", "入学时间", "学号", "专业", "行政班级", "毕业时间", "姓名",
            "课程/环节", "类别", "学分", "成绩", "绩点", "学年", "学期", "平均成绩", "打印日期", "教务处", "成绩审查",
            "毕业", "设计", "论文", "题目", "平均", "获得等级考试证书", "CET", "-----------------------------------------------"
        ]
        return any(k in s for k in bad)

    def parse_score_and_credit_point(score_line: str):
        score = None
        credit_point = None

        grade_word = None
        for g in grade_map:
            if g in score_line:
                grade_word = g
                score = grade_map[g]
                break

        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", score_line)]

        if grade_word:
            if nums:
                credit_point = nums[-1]
        else:
            if len(nums) >= 2:
                # 常见格式："87.0 18.87"
                if nums[0] <= 100:
                    score = nums[0]
                    credit_point = nums[1]
            elif len(nums) == 1:
                if nums[0] <= 100:
                    score = nums[0]

        return score, credit_point

    i = 0
    while i < len(lines) - 3:
        course = lines[i]

        if is_noise(course) or is_number_line(course) or course in categories:
            i += 1
            continue

        # 课程块格式（常见）：课程名 / 类别 / 学分 / 成绩(或等级) / 学分绩点
        if i + 3 < len(lines) and lines[i + 1] in categories and is_number_line(lines[i + 2]):
            category = lines[i + 1]
            credit = parse_float(lines[i + 2])
            score_line = lines[i + 3]

            score, credit_point = parse_score_and_credit_point(score_line)

            # 若成绩行未带学分绩点，则尝试下一行
            step = 4
            if credit_point is None and i + 4 < len(lines) and is_number_line(lines[i + 4]):
                credit_point = parse_float(lines[i + 4])
                step = 5

            gpa_cn = None
            if credit is not None and credit > 0 and credit_point is not None:
                gpa_cn = credit_point / credit

            score100 = normalize_score(score, gpa_cn)
            nz7 = to_nz_au_7(score100)
            au7 = nz7
            uk_pct = score100
            ca4 = to_canada_4(score100)

            rows.append({
                "course": re.sub(r"\s+", " ", course),
                "credit": credit,
                "score_raw": score_line,
                "gpa_cn": gpa_cn,
                "score100": score100,
                "nz7": nz7,
                "au7": au7,
                "uk_pct": uk_pct,
                "ca4": ca4,
            })

            i += step
            continue

        i += 1

    return rows


def write_csv(path: str, rows: List[Dict]):
    fields = ["course", "credit", "score_raw", "gpa_cn", "score100", "nz7", "au7", "uk_pct", "ca4"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ensure_deps()

    if len(sys.argv) < 2:
        print("用法: python3 ~/Desktop/transcript_converter.py ~/Desktop/你的成绩单.pdf")
        sys.exit(1)

    pdf_path = os.path.expanduser(sys.argv[1])
    if not os.path.exists(pdf_path):
        print(f"文件不存在: {pdf_path}")
        sys.exit(1)

    text = extract_text_from_pdf(pdf_path)

    base, _ = os.path.splitext(pdf_path)
    txt_out = base + "_extracted_text.txt"
    csv_out = base + "_converted.csv"

    with open(txt_out, "w", encoding="utf-8") as f:
        f.write(text)

    rows = try_parse_rows(text)
    write_csv(csv_out, rows)

    print(f"已输出文本: {txt_out}")
    print(f"已输出转换表: {csv_out}")
    print(f"解析到课程条数: {len(rows)}")

    if not rows:
        print("提示：自动解析为0。请先打开 extracted_text 检查原始文本，再手工整理CSV。")
        return

    avg_score = weighted_avg(rows, "score100")
    avg_nz = weighted_avg(rows, "nz7")
    avg_au = weighted_avg(rows, "au7")
    avg_ca = weighted_avg(rows, "ca4")

    def fmt(x):
        return "N/A" if x is None else f"{x:.3f}"

    print("\n=== 加权结果（按学分）===")
    print(f"百分制(UK可参考): {fmt(avg_score)}")
    print(f"NZ 7分制 GPA:      {fmt(avg_nz)}")
    print(f"AU 7分制 GPA:      {fmt(avg_au)}")
    print(f"Canada 4分制 GPA:  {fmt(avg_ca)}")


if __name__ == "__main__":
    main()
