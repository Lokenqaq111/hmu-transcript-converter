#!/bin/bash
# 用法1：把PDF拖到这个文件上
# 用法2：双击后按提示输入PDF路径

SCRIPT="$HOME/Desktop/transcript_converter.py"

if [ ! -f "$SCRIPT" ]; then
  echo "未找到: $SCRIPT"
  read -p "按回车退出..."
  exit 1
fi

if [ -n "$1" ]; then
  PDF="$1"
else
  echo "请输入PDF完整路径（可把文件拖进终端）："
  read -r PDF
fi

# 兼容拖拽/手输时带转义符（\ 空格、\(、\)、\[、\] 等）
if [ ! -e "$PDF" ]; then
  PDF_UNESCAPED=$(python3 -c 'import sys,shlex; s=sys.argv[1];
parts=shlex.split(s);
print(parts[0] if parts else s)' "$PDF" 2>/dev/null)
  if [ -n "$PDF_UNESCAPED" ] && [ -e "$PDF_UNESCAPED" ]; then
    PDF="$PDF_UNESCAPED"
  fi
fi

# 去掉用户可能粘贴的首尾引号
PDF="${PDF#\"}"
PDF="${PDF%\"}"
PDF="${PDF#\'}"
PDF="${PDF%\'}"

python3 "$SCRIPT" "$PDF"
echo ""
read -p "处理完成，按回车退出..."