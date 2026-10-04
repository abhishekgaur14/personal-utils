# PDF Tools

A local CLI for common PDF tasks. Documents are processed on this machine and are not sent to a service.

Commands support merging, splitting, extracting, rotating, reordering, compressing, and inspecting PDFs. Page numbers are 1-based. Encrypted PDFs are not supported yet.

Compression is lossless by default: it deflates page content streams and removes duplicate/unreferenced objects. For scanned PDFs, opt into lossy image recompression with `--dpi` (36–600) and `--quality` (1–95); both ranges are inclusive. This changes embedded image pixels while preserving page text and vector content.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
uv run pdf-tools --help
```

## Examples

```sh
uv run pdf-tools merge one.pdf two.pdf --output combined.pdf
uv run pdf-tools split combined.pdf --output-dir pages --pages 2-4
uv run pdf-tools extract combined.pdf --pages 1,3-4 --output selected.pdf
uv run pdf-tools rotate combined.pdf --pages 2 --degrees 90 --output rotated.pdf
uv run pdf-tools reorder combined.pdf --pages 3,1,2 --output reordered.pdf
uv run pdf-tools compress combined.pdf --output compressed.pdf
uv run pdf-tools compress scanned.pdf --output smaller.pdf --dpi 150 --quality 70
uv run pdf-tools inspect combined.pdf
```

`split` writes files such as `combined-page-002.pdf` into the requested directory. Inputs are preserved. Existing output files are not replaced unless `--overwrite` is supplied.
