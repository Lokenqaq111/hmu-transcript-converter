from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .export import render_terminal, write_csv, write_json, write_text
from .pipeline import convert_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hmu-transcript",
        description="把海南医科大学成绩单 PDF 转为 CSV，并给出 NZ / AU / UK / Canada 参考分制。",
    )
    parser.add_argument("pdf", nargs="+", help="成绩单 PDF 路径，可一次处理多个")
    parser.add_argument("-o", "--output-dir", help="输出目录（默认与 PDF 同目录）")
    parser.add_argument("--no-ocr", action="store_true", help="文本很少时也不走 OCR")
    parser.add_argument("--no-text", action="store_true", help="不写出 _extracted_text.txt")
    parser.add_argument("--json", action="store_true", help="额外写出 _summary.json")
    parser.add_argument("-q", "--quiet", action="store_true", help="只保留必要输出")
    parser.add_argument("-V", "--version", action="version", version=f"hmu-transcript {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exit_code = 0
    for raw in args.pdf:
        try:
            _convert_one(raw, args)
        except SystemExit as exc:
            message = exc.code if isinstance(exc.code, str) else str(exc)
            print(message, file=sys.stderr)
            exit_code = 1
        except Exception as exc:
            print(f"处理失败: {raw}\n{exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


def _convert_one(raw: str, args: argparse.Namespace) -> None:
    pdf_path = Path(raw).expanduser()
    if not pdf_path.exists():
        raise SystemExit(f"文件不存在: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise SystemExit(f"请提供 PDF 文件: {pdf_path}")

    result = convert_pdf(pdf_path, ocr=not args.no_ocr)
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem

    csv_path = output_dir / f"{stem}_converted.csv"
    write_csv(csv_path, result)

    text_path = None
    if not args.no_text:
        text_path = output_dir / f"{stem}_extracted_text.txt"
        write_text(text_path, result.text)

    json_path = None
    if args.json:
        json_path = output_dir / f"{stem}_summary.json"
        write_json(json_path, result)

    if not args.quiet:
        print(render_terminal(result))
        print("")
        print(f"已输出转换表: {csv_path}")
        if text_path:
            print(f"已输出文本:   {text_path}")
        if json_path:
            print(f"已输出 JSON:  {json_path}")
        print("")


if __name__ == "__main__":
    sys.exit(main())
