"""Typer command-line interface for local PDF operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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

app = typer.Typer(
    name="pdf-tools",
    help="Merge, split, extract, rotate, reorder, and inspect local PDFs.",
    no_args_is_help=True,
)


def _run(operation):
    try:
        return operation()
    except PdfToolsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def merge(
    inputs: Annotated[list[Path], typer.Argument(help="Input PDFs, in merge order.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Merged PDF path.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Merge PDFs in the order supplied."""

    _run(lambda: merge_pdfs(inputs, output, overwrite=overwrite))
    typer.echo(f"Merged {len(inputs)} PDFs into {output}")


@app.command()
def compress(
    input: Annotated[Path, typer.Argument(help="PDF to compress.")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Compressed PDF path.")
    ],
    dpi: Annotated[
        int | None,
        typer.Option(
            "--dpi",
            min=36,
            max=600,
            help="Downsample images to this DPI; omit for lossless compression.",
        ),
    ] = None,
    quality: Annotated[
        int,
        typer.Option(
            "--quality",
            min=1,
            max=95,
            help="JPEG quality for downsampled images (1-95).",
        ),
    ] = 75,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Compress page streams and optionally downsample/recompress images."""

    output_path = _run(
        lambda: compress_pdf(
            input, output, overwrite=overwrite, dpi=dpi, quality=quality
        )
    )
    input_size = input.expanduser().stat().st_size
    output_size = output_path.stat().st_size
    if output_size < input_size:
        change = f"{(input_size - output_size) / input_size:.1%} smaller"
    elif output_size > input_size:
        change = f"{(output_size - input_size) / input_size:.1%} larger"
    else:
        change = "same size"
    typer.echo(
        f"Compressed {input} to {output_path}: "
        f"{input_size:,} -> {output_size:,} bytes ({change})"
    )


@app.command()
def split(
    input: Annotated[Path, typer.Argument(help="PDF to split.")],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="Directory for one-page PDFs.")
    ],
    pages: Annotated[
        str | None,
        typer.Option(
            "--pages", help="Optional pages/ranges, e.g. 1,3-5. Default: all."
        ),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace existing page files.")
    ] = False,
) -> None:
    """Write one PDF per selected page."""

    selected = _run(lambda: parse_page_spec(pages)) if pages is not None else None
    outputs = _run(
        lambda: split_pdf(input, output_dir, pages=selected, overwrite=overwrite)
    )
    typer.echo(f"Wrote {len(outputs)} page PDFs to {output_dir}")


@app.command()
def extract(
    input: Annotated[Path, typer.Argument(help="Source PDF.")],
    pages: Annotated[
        str, typer.Option("--pages", help="Pages/ranges to extract, e.g. 1,3-5.")
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Extract selected pages in the requested order."""

    selected = _run(lambda: parse_page_spec(pages))
    _run(lambda: extract_pages(input, selected, output, overwrite=overwrite))
    typer.echo(f"Extracted {len(selected)} pages to {output}")


@app.command()
def rotate(
    input: Annotated[Path, typer.Argument(help="Source PDF.")],
    pages: Annotated[
        str, typer.Option("--pages", help="Pages/ranges to rotate, e.g. 1,3-5.")
    ],
    degrees: Annotated[
        int, typer.Option("--degrees", help="Clockwise rotation: 90, 180, or 270.")
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Rotate selected pages clockwise."""

    selected = _run(lambda: parse_page_spec(pages))
    _run(lambda: rotate_pages(input, selected, degrees, output, overwrite=overwrite))
    typer.echo(f"Rotated {len(selected)} pages by {degrees} degrees into {output}")


@app.command()
def reorder(
    input: Annotated[Path, typer.Argument(help="Source PDF.")],
    pages: Annotated[
        str, typer.Option("--pages", help="Complete new page order, e.g. 3,1,2.")
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Reorder all pages using a 1-based page sequence."""

    selected = _run(lambda: parse_page_spec(pages))
    _run(lambda: reorder_pages(input, selected, output, overwrite=overwrite))
    typer.echo(f"Reordered {len(selected)} pages into {output}")


@app.command("inspect")
def inspect_command(
    input: Annotated[Path, typer.Argument(help="PDF to inspect.")],
) -> None:
    """Show page count and common document metadata."""

    info = _run(lambda: inspect_pdf(input))
    typer.echo(f"Pages: {info.page_count}")
    for key, value in info.metadata.items():
        typer.echo(f"{key.replace('_', ' ').title()}: {value}")


if __name__ == "__main__":
    app()
