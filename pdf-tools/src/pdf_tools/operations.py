"""PDF operations independent of the command-line interface."""

from __future__ import annotations

import io
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError, PdfStreamError


class PdfToolsError(Exception):
    """An expected, user-correctable PDF operation failure."""


@dataclass(frozen=True)
class PdfInfo:
    """Basic information returned by :func:`inspect_pdf`."""

    page_count: int
    metadata: dict[str, str]


def _read_pdf(path: Path) -> PdfReader:
    path = Path(path).expanduser()
    if not path.exists():
        raise PdfToolsError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise PdfToolsError(f"Input path is not a file: {path}")

    try:
        reader = PdfReader(path, strict=False)
    except (OSError, PdfReadError, ValueError) as exc:
        raise PdfToolsError(f"Could not read a valid PDF from '{path}'.") from exc

    if reader.is_encrypted:
        raise PdfToolsError(f"Encrypted PDFs are not supported: {path}")
    try:
        for page in reader.pages:
            _ = page.mediabox
    except (PdfReadError, PdfStreamError, OSError, ValueError, KeyError) as exc:
        raise PdfToolsError(f"Could not read a valid PDF from '{path}'.") from exc
    return reader


def _validate_pages(
    pages: Sequence[int], page_count: int, *, allow_duplicates: bool = False
) -> list[int]:
    if not pages:
        raise PdfToolsError("At least one page must be selected.")

    normalized: list[int] = []
    seen: set[int] = set()
    for page_number in pages:
        if isinstance(page_number, bool) or not isinstance(page_number, int):
            raise PdfToolsError("Page numbers must be integers.")
        if page_number < 1:
            raise PdfToolsError(
                f"Page numbers are 1-based; page {page_number} is invalid."
            )
        if page_number > page_count:
            raise PdfToolsError(
                f"Page {page_number} is out of range; PDF has {page_count} pages."
            )
        if not allow_duplicates and page_number in seen:
            raise PdfToolsError(f"Page {page_number} was selected more than once.")
        seen.add(page_number)
        normalized.append(page_number)
    return normalized


def _check_output(output: Path, inputs: Sequence[Path], *, overwrite: bool) -> Path:
    output = Path(output).expanduser()
    resolved_output = output.resolve(strict=False)
    if any(
        Path(source).expanduser().resolve(strict=False) == resolved_output
        for source in inputs
    ):
        raise PdfToolsError("The output path cannot be the same as an input PDF.")
    if not output.parent.is_dir():
        raise PdfToolsError(f"Output directory does not exist: {output.parent}")
    if output.exists() and not overwrite:
        raise PdfToolsError(
            f"Output file already exists: {output}. Pass --overwrite to replace it."
        )
    return output


def _write_pdf(
    writer: PdfWriter,
    output: Path,
    inputs: Sequence[Path],
    *,
    overwrite: bool,
) -> None:
    output = _check_output(output, inputs, overwrite=overwrite)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            writer.write(stream)

        if overwrite:
            os.replace(temp_path, output)
        else:
            # Linking the completed temporary file makes creation atomic and
            # cannot replace a destination created concurrently by another process.
            os.link(temp_path, output)
            temp_path.unlink()
        temp_path = None
    except FileExistsError as exc:
        raise PdfToolsError(
            f"Output file already exists: {output}. Pass --overwrite to replace it."
        ) from exc
    except (OSError, PdfReadError, ValueError) as exc:
        raise PdfToolsError(f"Could not write PDF to '{output}'.") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _copy_metadata(reader: PdfReader, writer: PdfWriter) -> None:
    if reader.metadata:
        metadata = {
            str(key): str(value)
            for key, value in reader.metadata.items()
            if value is not None
        }
        if metadata:
            writer.add_metadata(metadata)


def merge_pdfs(
    inputs: Sequence[Path], output: Path, *, overwrite: bool = False
) -> Path:
    """Merge PDFs in the supplied order and return the output path."""

    if not inputs:
        raise PdfToolsError("At least one input PDF is required.")
    readers = [_read_pdf(Path(path)) for path in inputs]
    writer = PdfWriter()
    for reader in readers:
        writer.append(reader)
    _copy_metadata(readers[0], writer)
    output = Path(output).expanduser()
    _write_pdf(writer, output, inputs, overwrite=overwrite)
    return output


def compress_pdf(
    input_path: Path,
    output: Path,
    *,
    overwrite: bool = False,
    dpi: int | None = None,
    quality: int = 75,
) -> Path:
    """Compress PDF streams, optionally downsampling and recompressing images."""

    if dpi is not None and (type(dpi) is not int or dpi < 36 or dpi > 600):
        raise PdfToolsError("Image DPI must be between 36 and 600.")
    if type(quality) is not int or quality < 1 or quality > 95:
        raise PdfToolsError("JPEG quality must be between 1 and 95.")

    input_path = Path(input_path).expanduser()
    reader = _read_pdf(input_path)
    if dpi is not None:
        document = pymupdf.open(input_path)
        try:
            for page in document:
                for image_info in page.get_images(full=True):
                    xref = image_info[0]
                    extracted = document.extract_image(xref)
                    image = Image.open(io.BytesIO(extracted["image"])).convert("RGB")
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue
                    # Keep the requested density for the largest placement.
                    displayed_width = max(rect.width for rect in rects)
                    displayed_height = max(rect.height for rect in rects)
                    target = (
                        max(1, round(displayed_width / 72 * dpi)),
                        max(1, round(displayed_height / 72 * dpi)),
                    )
                    if image.width > target[0] or image.height > target[1]:
                        image.thumbnail(target, Image.Resampling.LANCZOS)
                    encoded = io.BytesIO()
                    image.save(encoded, format="JPEG", quality=quality, optimize=True)
                    page.replace_image(xref, stream=encoded.getvalue())
            output = Path(output).expanduser()
            output = _check_output(output, [input_path], overwrite=overwrite)
            with tempfile.NamedTemporaryFile(
                prefix=f".{output.name}.",
                suffix=".tmp",
                dir=output.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                document.save(temp_path, garbage=4, deflate=True)
                if overwrite:
                    os.replace(temp_path, output)
                else:
                    os.link(temp_path, output)
            except FileExistsError as exc:
                raise PdfToolsError(
                    f"Output file already exists: {output}. "
                    "Pass --overwrite to replace it."
                ) from exc
            finally:
                temp_path.unlink(missing_ok=True)
        except PdfToolsError:
            raise
        except Exception as exc:
            raise PdfToolsError(f"Could not compress PDF: {input_path}") from exc
        finally:
            document.close()
        return output

    writer = PdfWriter()
    try:
        writer.append(reader)
        _copy_metadata(reader, writer)
        for page in writer.pages:
            page.compress_content_streams(level=9)
        writer.compress_identical_objects(
            remove_duplicates=True, remove_unreferenced=True
        )
    except (PdfReadError, PdfStreamError, OSError, ValueError, KeyError) as exc:
        raise PdfToolsError(f"Could not compress PDF: {input_path}") from exc

    output = Path(output).expanduser()
    _write_pdf(writer, output, [input_path], overwrite=overwrite)
    return output


def split_pdf(
    input_path: Path,
    output_dir: Path,
    *,
    pages: Sequence[int] | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Write selected pages as separate PDFs in the requested page order."""

    input_path = Path(input_path).expanduser()
    reader = _read_pdf(input_path)
    selected = list(range(1, len(reader.pages) + 1)) if pages is None else list(pages)
    selected = _validate_pages(selected, len(reader.pages))

    output_dir = Path(output_dir).expanduser()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PdfToolsError(f"Could not create output directory: {output_dir}") from exc
    if not output_dir.is_dir():
        raise PdfToolsError(f"Output path is not a directory: {output_dir}")

    outputs = [
        output_dir / f"{input_path.stem}-page-{page_number:03d}.pdf"
        for page_number in selected
    ]
    for output in outputs:
        _check_output(output, [input_path], overwrite=overwrite)

    written: list[Path] = []
    try:
        for page_number, output in zip(selected, outputs, strict=True):
            writer = PdfWriter()
            writer.add_page(reader.pages[page_number - 1])
            _copy_metadata(reader, writer)
            _write_pdf(writer, output, [input_path], overwrite=overwrite)
            written.append(output)
    except Exception:
        if not overwrite:
            for output in written:
                output.unlink(missing_ok=True)
        raise
    return outputs


def extract_pages(
    input_path: Path,
    pages: Sequence[int],
    output: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Extract pages in the supplied 1-based order."""

    input_path = Path(input_path).expanduser()
    reader = _read_pdf(input_path)
    selected = _validate_pages(pages, len(reader.pages))
    writer = PdfWriter()
    for page_number in selected:
        writer.add_page(reader.pages[page_number - 1])
    _copy_metadata(reader, writer)
    output = Path(output).expanduser()
    _write_pdf(writer, output, [input_path], overwrite=overwrite)
    return output


def rotate_pages(
    input_path: Path,
    pages: Sequence[int],
    degrees: int,
    output: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Rotate selected pages clockwise by 90, 180, or 270 degrees."""

    if type(degrees) is not int or degrees not in {90, 180, 270}:
        raise PdfToolsError("Rotation must be 90, 180, or 270 degrees clockwise.")

    input_path = Path(input_path).expanduser()
    reader = _read_pdf(input_path)
    selected = _validate_pages(pages, len(reader.pages))
    writer = PdfWriter()
    for page_number, page in enumerate(reader.pages, start=1):
        if page_number in selected:
            page.rotate(degrees)
        writer.add_page(page)
    _copy_metadata(reader, writer)
    output = Path(output).expanduser()
    _write_pdf(writer, output, [input_path], overwrite=overwrite)
    return output


def reorder_pages(
    input_path: Path,
    pages: Sequence[int],
    output: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Reorder every page according to a 1-based permutation."""

    input_path = Path(input_path).expanduser()
    reader = _read_pdf(input_path)
    selected = _validate_pages(pages, len(reader.pages), allow_duplicates=True)
    if len(selected) != len(reader.pages) or set(selected) != set(
        range(1, len(reader.pages) + 1)
    ):
        raise PdfToolsError("Reordering must list each page exactly once.")

    writer = PdfWriter()
    for page_number in selected:
        writer.add_page(reader.pages[page_number - 1])
    _copy_metadata(reader, writer)
    output = Path(output).expanduser()
    _write_pdf(writer, output, [input_path], overwrite=overwrite)
    return output


def inspect_pdf(input_path: Path) -> PdfInfo:
    """Return page count and common document metadata."""

    reader = _read_pdf(Path(input_path))
    metadata: dict[str, str] = {}
    if reader.metadata:
        for key, value in reader.metadata.items():
            name = str(key).lstrip("/").lower()
            if value is not None and str(value).strip():
                metadata[name] = str(value)
    return PdfInfo(page_count=len(reader.pages), metadata=metadata)


def parse_page_spec(specification: str) -> list[int]:
    """Parse comma-separated 1-based pages and inclusive ranges."""

    if not specification.strip():
        raise PdfToolsError("Page selection cannot be empty.")

    pages: list[int] = []
    for raw_part in specification.split(","):
        part = raw_part.strip()
        if not part:
            raise PdfToolsError(f"Invalid page selection: '{specification}'.")
        if "-" in part:
            if part.count("-") != 1:
                raise PdfToolsError(f"Invalid page range: '{part}'.")
            start_text, end_text = (value.strip() for value in part.split("-"))
            if not re.fullmatch(r"[0-9]+", start_text) or not re.fullmatch(
                r"[0-9]+", end_text
            ):
                raise PdfToolsError(f"Invalid page range: '{part}'.")
            start, end = int(start_text), int(end_text)
            if start < 1 or end < 1:
                raise PdfToolsError("Page numbers are 1-based and must be positive.")
            if start > end:
                raise PdfToolsError(f"Page range must ascend: '{part}'.")
            pages.extend(range(start, end + 1))
        else:
            if not re.fullmatch(r"[0-9]+", part):
                raise PdfToolsError(f"Invalid page number: '{part}'.")
            page_number = int(part)
            pages.append(page_number)

    _validate_pages(pages, max(pages, default=0))
    return pages
