# Transcript Converter (HMU template)

最简工具：把海南医科大学成绩单 PDF 转为 CSV，并给出 NZ/AU 7分制、UK百分制、Canada 4分制参考结果。

## 使用

macOS：双击 `成绩单一键转换.command`，然后输入/拖入 PDF 路径。

或命令行：

```bash
python3 transcript_converter.py /path/to/成绩单.pdf
```

## 输出

- `xxx_extracted_text.txt`
- `xxx_converted.csv`

## 说明

- 当前规则按 HMU 导出模板适配。
- 等级映射与国际分制换算为“参考简化版”，最终以目标院校官方评估为准。
- 请勿上传任何包含真实姓名/学号的成绩单样本。