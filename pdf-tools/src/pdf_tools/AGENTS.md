# pdf_tools package guidance

- Keep public operations typed, path-oriented, and independent of Typer.
- Use a project-level PDF exception for expected validation and parsing failures; do not leak low-level parser tracebacks through the CLI.
- Page selections use 1-based integers at the public API boundary. Convert to zero-based indices only when accessing pypdf pages.
- Preserve source files and metadata where pypdf supports it. Treat encrypted PDFs explicitly; do not silently emit incomplete output.
