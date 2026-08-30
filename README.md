# 海医成绩单转换

把海南医科大学教务导出的成绩单 PDF，转成带学分加权结果的 CSV，并给出留学常用分制参考。

适合先自己核算一轮 NZ / AU / UK / Canada 的申请材料，**最终以目标院校或官方评估机构为准**。

## 现在会做什么

- 优先读电子版 PDF 文本，也尝试识别表格
- 文本很少时再走 OCR（需本机已装 tesseract）
- 同时支持「一行一块」的海医常见排版，和「课程 类别 学分 成绩 …」单行记录
- 区分绩点与学分绩点，避免把 `87.0 12.25` 里的学分绩点当成 4 分制绩点
- 等级制（优秀 / 良好 / 通过）按参考中位值换算；通过/不通过不计入加权
- 分别给出 AU 7 分制（HD/D/C/P）和更细的 NZ 7 / NZ 9
- 保留中国百分制作为 UK 参考，并另给 First / 2:1 / 2:2 等级估测
- 输出全部课程加权，以及仅必修加权

## 使用

先安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

macOS：把 `成绩单一键转换.command` 和本仓库放在同一目录，双击后拖入 PDF；也可以把 PDF 直接拖到 `.command` 上。

命令行：

```bash
python3 transcript_converter.py /path/to/成绩单.pdf
python3 -m hmu_transcript /path/to/成绩单.pdf -o ./out --json
```

常用参数：

| 参数 | 作用 |
| --- | --- |
| `-o DIR` | 指定输出目录 |
| `--json` | 额外写一份汇总 JSON |
| `--no-ocr` | 不尝试 OCR |
| `--no-text` | 不写提取文本 |

扫描件 OCR（可选）：

```bash
python3 -m pip install pytesseract pillow
# macOS: brew install tesseract tesseract-lang
# Debian/Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

## 输出

与 PDF 同目录（或 `-o` 指定目录）：

- `xxx_converted.csv`：课程明细 + 文末加权汇总，Excel 可直接打开
- `xxx_extracted_text.txt`：原始提取文本，解析异常时先看这个
- `xxx_summary.json`：仅在 `--json` 时生成

CSV 列包括：课程、类别、学分、学年、学期、原始成绩、百分制、中国绩点、NZ_7、NZ_9、AU_7、UK百分制、UK等级、Canada_4、备注。

## 换算说明（参考）

| 体系 | 规则摘要 |
| --- | --- |
| AU 7 | 85+ = 7，75–84 = 6，65–74 = 5，50–64 = 4，其余 0 |
| NZ 7 | 85+ = 7，之后按 80 / 75 / 70 / 65 / 50 递减 |
| NZ 9 | 接近奥克兰大学常见百分制区间（90=9 … 50=1） |
| Canada 4 | 常见 Ontario 细表，90=4.0，85=3.9，80=3.7 … |
| UK | 百分制沿用国内成绩；等级按国内 85/75/65/60 估 First / 2:1 / 2:2 / Third |

等级制：优秀 95，良好 85，中等 75，及格 60，合格 65。只有绩点、没有百分制时，按 `百分制 ≈ 绩点 × 10 + 50` 回推，并在备注里标明。

## 开发

```bash
python3 -m pip install -r requirements.txt pytest
python3 -m pytest -q
```

测试使用匿名样例文本/生成 PDF，请勿把含真实姓名或学号的成绩单提交进仓库。
