from pathlib import Path

from conftest import page_widths
from pypdf import PdfReader, PdfWriter
from typer.testing import CliRunner

from pdf_tools.cli import app

runner = CliRunner()


def test_cli_help_shows_page_selection_example():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "pdf-tools extract report.pdf --pages 1,3-5" in result.output


def test_cli_merge_creates_output_in_input_order(make_pdf, tmp_path: Path):
    first = make_pdf("first.pdf", [100])
    second = make_pdf("second.pdf", [200])
    output = tmp_path / "merged.pdf"

    result = runner.invoke(
        app, ["merge", str(first), str(second), "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    assert "Merged 2 PDFs" in result.output
    assert page_widths(output) == [100, 200]


def test_cli_extract_parses_page_ranges(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120, 130])
    output = tmp_path / "selected.pdf"

    result = runner.invoke(
        app,
        ["extract", str(source), "--pages", "4,1-2", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert page_widths(output) == [130, 100, 110]


def test_cli_split_and_inspect(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120], title="CLI fixture")
    output_dir = tmp_path / "pages"

    split_result = runner.invoke(
        app,
        ["split", str(source), "--output-dir", str(output_dir), "--pages", "2-3"],
    )
    inspect_result = runner.invoke(app, ["inspect", str(source)])

    assert split_result.exit_code == 0, split_result.output
    assert len(list(output_dir.glob("*.pdf"))) == 2
    assert inspect_result.exit_code == 0, inspect_result.output
    assert "Pages: 3" in inspect_result.output
    assert "CLI fixture" in inspect_result.output


def test_cli_inspect_reports_when_metadata_is_missing(make_pdf):
    source = make_pdf("without-metadata.pdf", [100])
    reader = PdfReader(source)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    output_without_metadata = source.with_name("metadata-free.pdf")
    with output_without_metadata.open("wb") as stream:
        writer.write(stream)

    result = runner.invoke(app, ["inspect", str(output_without_metadata)])

    assert result.exit_code == 0, result.output
    assert "Pages: 1" in result.output
    assert "Descriptive metadata: none" in result.output
    assert "Producer: pypdf" in result.output


def test_cli_rejects_invalid_pages_with_readable_error(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110])
    output = tmp_path / "bad.pdf"

    result = runner.invoke(
        app,
        ["extract", str(source), "--pages", "1-3", "--output", str(output)],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "page 3" in result.output.lower()
    assert not output.exists()


def test_cli_rotate_and_reorder(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120])
    rotated = tmp_path / "rotated.pdf"
    reordered = tmp_path / "reordered.pdf"

    rotate_result = runner.invoke(
        app,
        [
            "rotate",
            str(source),
            "--pages",
            "2",
            "--degrees",
            "180",
            "--output",
            str(rotated),
        ],
    )
    reorder_result = runner.invoke(
        app,
        ["reorder", str(source), "--pages", "3,1,2", "--output", str(reordered)],
    )

    assert rotate_result.exit_code == 0, rotate_result.output
    assert reorder_result.exit_code == 0, reorder_result.output
    assert page_widths(reordered) == [120, 100, 110]


def test_cli_requires_explicit_overwrite(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100])
    output = make_pdf("output.pdf", [200])

    result = runner.invoke(app, ["merge", str(source), "--output", str(output)])
    overwrite_result = runner.invoke(
        app, ["merge", str(source), "--output", str(output), "--overwrite"]
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert overwrite_result.exit_code == 0, overwrite_result.output
    assert page_widths(output) == [100]


def test_cli_compress_reports_output_and_keeps_source(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100], repetitive_content=True)
    output = tmp_path / "compressed.pdf"
    original = source.read_bytes()

    result = runner.invoke(app, ["compress", str(source), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert "Compressed" in result.output
    assert output.exists()
    assert source.read_bytes() == original
    assert output.stat().st_size < source.stat().st_size
