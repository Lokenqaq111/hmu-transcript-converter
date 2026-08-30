from pathlib import Path

from tests.fixtures import SAMPLE_TEXT, write_sample_pdf
from hmu_transcript.cli import main
from hmu_transcript.export import summarize
from hmu_transcript.pipeline import convert_pdf


def test_convert_generated_pdf(tmp_path: Path):
    pdf = write_sample_pdf(tmp_path / "sample_transcript.pdf")
    result = convert_pdf(pdf, ocr=False)
    names = {c.course for c in result.courses}

    assert "人体解剖学" in names
    assert "毕业设计" in names
    assert "健康评估" in names
    assert len(result.courses) >= 6

    summaries = summarize(result)
    assert summaries[0].course_count >= 5
    assert summaries[0].score100 is not None
    assert 70 < summaries[0].score100 < 95


def test_cli_writes_csv_and_optional_json(tmp_path: Path):
    pdf = write_sample_pdf(tmp_path / "cli_transcript.pdf")
    out = tmp_path / "out"
    code = main([str(pdf), "-o", str(out), "--json", "--no-ocr"])
    assert code == 0
    csv_path = out / "cli_transcript_converted.csv"
    json_path = out / "cli_transcript_summary.json"
    text_path = out / "cli_transcript_extracted_text.txt"
    assert csv_path.exists()
    assert json_path.exists()
    assert text_path.exists()
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "人体解剖学" in content
    assert "NZ_7" in content
    assert SAMPLE_TEXT.splitlines()[0] in text_path.read_text(encoding="utf-8")


def test_cli_missing_file(tmp_path: Path, capsys):
    code = main([str(tmp_path / "missing.pdf")])
    assert code == 1
    assert "不存在" in capsys.readouterr().err
