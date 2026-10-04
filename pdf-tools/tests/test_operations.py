from pathlib import Path

import pymupdf
import pytest
from conftest import page_widths
from pypdf import PdfReader
from pypdf.errors import PdfReadError

import pdf_tools.operations as operations
from pdf_tools.operations import (
    PdfToolsError,
    compress_pdf,
    extract_pages,
    inspect_pdf,
    merge_pdfs,
    parse_page_spec,
    reorder_pages,
    rotate_pages,
    split_pdf,
)


def test_merge_preserves_input_order_and_sources(make_pdf, tmp_path: Path):
    first = make_pdf("first.pdf", [100, 110], title="First input")
    second = make_pdf("second.pdf", [200], title="Second input")
    before = (first.read_bytes(), second.read_bytes())
    output = tmp_path / "merged.pdf"

    merge_pdfs([first, second], output)

    assert page_widths(output) == [100, 110, 200]
    assert inspect_pdf(output).metadata["title"] == "First input"
    assert (first.read_bytes(), second.read_bytes()) == before


def test_merge_rejects_empty_inputs(tmp_path: Path):
    with pytest.raises(PdfToolsError, match="[Aa]t least one input"):
        merge_pdfs([], tmp_path / "out.pdf")


def test_operations_reject_missing_and_malformed_inputs(tmp_path: Path):
    with pytest.raises(PdfToolsError, match="does not exist"):
        inspect_pdf(tmp_path / "missing.pdf")

    malformed = tmp_path / "malformed.pdf"
    malformed.write_text("not a PDF", encoding="utf-8")
    with pytest.raises(PdfToolsError, match="valid PDF"):
        inspect_pdf(malformed)


def test_operations_reject_encrypted_pdfs(make_pdf, tmp_path: Path):
    encrypted = make_pdf("encrypted.pdf", [100], encrypted=True)
    with pytest.raises(PdfToolsError, match="Encrypted PDFs are not supported"):
        inspect_pdf(encrypted)


def test_merge_never_uses_an_input_as_output(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100])
    original = source.read_bytes()

    with pytest.raises(PdfToolsError, match="same as an input"):
        merge_pdfs([source], source)

    assert source.read_bytes() == original


def test_outputs_are_not_overwritten_without_opt_in(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100])
    output = make_pdf("existing.pdf", [300])
    original = output.read_bytes()

    with pytest.raises(PdfToolsError, match="already exists"):
        merge_pdfs([source], output)
    assert output.read_bytes() == original

    merge_pdfs([source], output, overwrite=True)
    assert page_widths(output) == [100]


def test_split_writes_selected_pages_in_requested_order(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120])
    output_dir = tmp_path / "split"

    outputs = split_pdf(source, output_dir, pages=[3, 1])

    assert [path.name for path in outputs] == [
        "source-page-003.pdf",
        "source-page-001.pdf",
    ]
    assert [page_widths(path) for path in outputs] == [[120], [100]]


def test_split_rejects_existing_outputs_without_overwrite(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110])
    output_dir = tmp_path / "split"
    output_dir.mkdir()
    existing = output_dir / "source-page-001.pdf"
    existing.write_bytes(b"keep me")

    with pytest.raises(PdfToolsError, match="already exists"):
        split_pdf(source, output_dir)
    assert existing.read_bytes() == b"keep me"


def test_split_rolls_back_outputs_if_a_later_page_write_fails(
    make_pdf, tmp_path: Path, monkeypatch
):
    source = make_pdf("source.pdf", [100, 110, 120])
    output_dir = tmp_path / "split"
    real_write = operations._write_pdf
    calls = 0

    def fail_on_second_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PdfToolsError("simulated write failure")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(operations, "_write_pdf", fail_on_second_write)
    with pytest.raises(PdfToolsError, match="simulated write failure"):
        split_pdf(source, output_dir)

    assert list(output_dir.glob("*.pdf")) == []


def test_extract_uses_one_based_page_numbers_and_requested_order(
    make_pdf, tmp_path: Path
):
    source = make_pdf("source.pdf", [100, 110, 120])
    output = tmp_path / "extracted.pdf"

    extract_pages(source, [3, 1], output)

    assert page_widths(output) == [120, 100]


@pytest.mark.parametrize("pages", [[], [0], [4], [1, 1]])
def test_extract_rejects_empty_invalid_or_duplicate_page_selection(
    make_pdf, tmp_path: Path, pages: list[int]
):
    source = make_pdf("source.pdf", [100, 110, 120])

    with pytest.raises(PdfToolsError):
        extract_pages(source, pages, tmp_path / "extracted.pdf")


def test_rotate_changes_only_selected_pages(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120])
    output = tmp_path / "rotated.pdf"

    rotate_pages(source, [2], 90, output)

    reader = PdfReader(output)
    assert [int(page.get("/Rotate", 0)) for page in reader.pages] == [0, 90, 0]
    assert page_widths(output) == [100, 110, 120]


@pytest.mark.parametrize("degrees", [0, 45, -90, 360])
def test_rotate_rejects_unsupported_angles(make_pdf, tmp_path: Path, degrees: int):
    source = make_pdf("source.pdf", [100, 110])

    with pytest.raises(PdfToolsError, match="90, 180, or 270"):
        rotate_pages(source, [1], degrees, tmp_path / "rotated.pdf")


def test_rotate_rejects_invalid_page_numbers(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110])
    with pytest.raises(PdfToolsError):
        rotate_pages(source, [3], 90, tmp_path / "rotated.pdf")


def test_reorder_requires_a_complete_permutation(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100, 110, 120])
    output = tmp_path / "reordered.pdf"

    reorder_pages(source, [3, 1, 2], output)
    assert page_widths(output) == [120, 100, 110]

    with pytest.raises(PdfToolsError, match="each page exactly once"):
        reorder_pages(source, [1, 1, 3], tmp_path / "invalid.pdf")


def test_inspect_reports_page_count_and_metadata(make_pdf):
    source = make_pdf("source.pdf", [100, 110], title="Synthetic test")

    info = inspect_pdf(source)

    assert info.page_count == 2
    assert info.metadata["title"] == "Synthetic test"
    assert info.metadata["author"] == "pytest fixture"


def test_inspect_handles_missing_metadata(make_pdf):
    source = make_pdf("source.pdf", [100])
    info = inspect_pdf(source)
    assert info.page_count == 1
    assert "title" not in info.metadata
    assert "author" not in info.metadata


def test_inspect_translates_errors_deferred_until_page_access(
    monkeypatch, tmp_path: Path
):
    class LazyMalformedReader:
        is_encrypted = False

        @property
        def pages(self):
            raise PdfReadError("deferred parse failure")

    monkeypatch.setattr(
        operations, "PdfReader", lambda *_args, **_kwargs: LazyMalformedReader()
    )
    source = tmp_path / "lazy-malformed.pdf"
    source.write_bytes(b"synthetic parser fixture")

    with pytest.raises(PdfToolsError, match="valid PDF"):
        inspect_pdf(source)


def test_compress_is_lossless_and_reduces_repetitive_content(make_pdf, tmp_path: Path):
    source = make_pdf(
        "source.pdf", [100, 110], title="Compression fixture", repetitive_content=True
    )
    output = tmp_path / "compressed.pdf"
    original = source.read_bytes()

    compress_pdf(source, output)

    assert page_widths(output) == [100, 110]
    assert inspect_pdf(output).metadata["title"] == "Compression fixture"
    assert output.stat().st_size < source.stat().st_size
    assert source.read_bytes() == original


def test_compress_respects_output_overwrite_protection(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100])
    output = make_pdf("output.pdf", [200])
    original = output.read_bytes()

    with pytest.raises(PdfToolsError, match="already exists"):
        compress_pdf(source, output)
    assert output.read_bytes() == original

    compress_pdf(source, output, overwrite=True)
    assert page_widths(output) == [100]


def test_compress_validates_lossy_settings(make_pdf, tmp_path: Path):
    source = make_pdf("source.pdf", [100])
    with pytest.raises(PdfToolsError, match="DPI"):
        compress_pdf(source, tmp_path / "bad-dpi.pdf", dpi=20)
    with pytest.raises(PdfToolsError, match="quality"):
        compress_pdf(source, tmp_path / "bad-quality.pdf", dpi=150, quality=100)


def test_compress_reduces_embedded_image_resolution(make_image_pdf, tmp_path: Path):
    source = make_image_pdf("source-image.pdf")
    output = tmp_path / "compressed-image.pdf"

    compress_pdf(source, output, dpi=72, quality=65)

    source_doc = pymupdf.open(source)
    output_doc = pymupdf.open(output)
    try:
        assert len(output_doc) == 1
        assert output_doc[0].rect == source_doc[0].rect
        assert output.stat().st_size < source.stat().st_size
        assert output_doc[0].get_images()[0][2:4] == (600, 400)
    finally:
        source_doc.close()
        output_doc.close()


def test_parse_page_spec_supports_lists_and_inclusive_ranges():
    assert parse_page_spec(" 4, 1-2, 6 ") == [4, 1, 2, 6]


@pytest.mark.parametrize("specification", ["", "1,,2", "3-1", "0", "1,1", "a", "+1"])
def test_parse_page_spec_rejects_invalid_selections(specification: str):
    with pytest.raises(PdfToolsError):
        parse_page_spec(specification)
