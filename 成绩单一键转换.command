#!/bin/bash
# 用法1：把 PDF 拖到这个文件上（可多个）
# 用法2：双击后按提示输入 PDF 路径

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/transcript_converter.py"

if [ -f "$SCRIPT" ]; then
  RUN=(python3 "$SCRIPT")
elif [ -d "$DIR/hmu_transcript" ]; then
  RUN=(python3 -m hmu_transcript)
else
  echo "未找到转换脚本: $SCRIPT"
  echo "请把本文件和 transcript_converter.py、hmu_transcript 文件夹放在同一目录。"
  read -r -p "按回车退出..."
  exit 1
fi

cd "$DIR" || exit 1

normalize_pdf() {
  local PDF="$1"
  PDF="${PDF#\"}"
  PDF="${PDF%\"}"
  PDF="${PDF#\'}"
  PDF="${PDF%\'}"

  if [ -e "$PDF" ]; then
    printf '%s\n' "$PDF"
    return 0
  fi

  local PDF_UNESCAPED
  PDF_UNESCAPED=$(python3 -c 'import sys, shlex
s = sys.argv[1]
parts = shlex.split(s)
print(parts[0] if parts else s)' "$PDF" 2>/dev/null)
  if [ -n "$PDF_UNESCAPED" ] && [ -e "$PDF_UNESCAPED" ]; then
    printf '%s\n' "$PDF_UNESCAPED"
    return 0
  fi
  return 1
}

run_one() {
  local RAW="$1"
  local PDF
  if ! PDF="$(normalize_pdf "$RAW")"; then
    echo "文件不存在: $RAW"
    return 1
  fi
  "${RUN[@]}" "$PDF"
}

if [ "$#" -gt 0 ]; then
  for RAW in "$@"; do
    run_one "$RAW"
    echo ""
  done
else
  echo "请输入 PDF 完整路径（可把文件拖进终端）："
  read -r RAW
  if [ -z "$RAW" ]; then
    echo "未提供文件。"
    read -r -p "按回车退出..."
    exit 1
  fi
  run_one "$RAW"
fi

echo ""
read -r -p "处理完成，按回车退出..."
