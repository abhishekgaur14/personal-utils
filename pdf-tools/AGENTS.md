# PDF Tools project guidance

- This is a local command-line PDF utility built with Typer and pypdf. Keep command parsing in `src/pdf_tools/cli.py` and PDF logic in `src/pdf_tools/operations.py`.
- CLI page numbers are 1-based. Validate page lists and angles before writing output.
- Compression is lossless by default. Optional lossy mode recompresses embedded images using Pillow and PyMuPDF while retaining text and vector content.
- Keep all imports at the top of each Python file; do not add imports inside functions or methods.
- Ruff is the project linter and import sorter. Run `uv run ruff check .` and `uv run ruff format --check .`; use `uv run ruff check --fix .` to auto-fix lint and sort imports, and `uv run ruff format .` to format files.
- Never modify input PDFs. Reject an output path that resolves to an input path, refuse existing outputs unless overwrite is explicitly requested, and write outputs atomically.
- Use generated synthetic PDFs for tests. Do not read, copy, print, commit, or upload PDFs from the repository's root `test_pdfs/` folder.
- Keep this project self-contained and manage it with uv. Run its suite with `uv run pytest` from this directory.
- Do not push changes unless the user explicitly asks.
