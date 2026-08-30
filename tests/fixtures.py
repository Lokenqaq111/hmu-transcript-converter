from __future__ import annotations

from pathlib import Path

CJK_FONT = Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")

SAMPLE_TEXT = """海南医科大学学生成绩档案表
院(系)
国际护理学院
培养层次
本科
学制
4
入学时间
2019-09
学号
2019XXXXXX
专业
护理学
行政班级
护理19-1
毕业时间
2023-06
姓名
测试学生

课程/环节
类别
学分
成绩
绩点
学年
学期

人体解剖学
必修
3.5
87.0 12.25
2019-2020
1

生理学
必修
4.0
良好
3.70
2019-2020
2

医学伦理学
选修
1.5
优秀
2019-2020
1

中国近现代史纲要
必修
3.0
78.0
2.80
2020-2021
1

健康评估 必修 3.0 92.0 4.00 2020-2021 1

军事训练
必修
1.0
通过
2020-2021
1

毕业设计
必修
8.0
88.0
3.80
2022-2023
2

毕业论文题目
护理实习生临床适应研究
平均成绩
85.2
打印日期
2023-06-20
"""

SAMPLE_TABLE = [
    ["课程/环节", "类别", "学分", "成绩", "绩点", "学年", "学期"],
    ["病理学", "必修", "4.0", "81.0", "3.10", "2020-2021", "2"],
    ["护理学导论", "选修", "2.0", "良好", "3.70", "2019-2020", "1"],
]


def write_sample_pdf(path: Path, text: str = SAMPLE_TEXT) -> Path:
    import pymupdf

    if not CJK_FONT.exists():
        raise FileNotFoundError(f"缺少中文字体: {CJK_FONT}")

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="hei", fontfile=str(CJK_FONT))
    y = 48.0
    for line in text.splitlines():
        if y > 800:
            page = doc.new_page(width=595, height=842)
            page.insert_font(fontname="hei", fontfile=str(CJK_FONT))
            y = 48.0
        page.insert_text((48, y), line, fontname="hei", fontsize=11)
        y += 16
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path
