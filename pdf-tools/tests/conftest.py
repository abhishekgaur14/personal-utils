from pathlib import Path

import pymupdf
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject


@pytest.fixture
def make_pdf(tmp_path: Path):
    """Create a small synthetic PDF with distinguishable page widths."""

    def _make_pdf(
        name: str,
        widths: list[int],
        *,
        title: str | None = None,
        encrypted: bool = False,
        repetitive_content: bool = False,
    ) -> Path:
        writer = PdfWriter()
        for width in widths:
            page = writer.add_blank_page(width=width, height=200)
            if repetitive_content:
                stream = DecodedStreamObject()
                stream.set_data(b"q Q\n" * 4_000)
                page[NameObject("/Contents")] = writer._add_object(stream)
        if title:
            writer.add_metadata({"/Title": title, "/Author": "pytest fixture"})
        if encrypted:
            writer.encrypt("fixture-password")

        path = tmp_path / name
        with path.open("wb") as stream:
            writer.write(stream)
        return path

    return _make_pdf


def page_widths(path: Path) -> list[float]:
    reader = PdfReader(path)
    return [float(page.mediabox.width) for page in reader.pages]


@pytest.fixture
def make_image_pdf(tmp_path: Path):
    """Create an image-only PDF for compression coverage."""

    def _make_image_pdf(name: str) -> Path:
        image_path = tmp_path / "fixture.png"
        Image.new("RGB", (1200, 800), color=(220, 230, 240)).save(image_path)
        path = tmp_path / name
        document = pymupdf.open()
        page = document.new_page(width=600, height=400)
        page.insert_image(page.rect, filename=str(image_path))
        document.save(path)
        document.close()
        return path

    return _make_image_pdf
