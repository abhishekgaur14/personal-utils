# Tests guidance

- Build tiny synthetic PDFs in pytest temporary directories with unique page dimensions/markers.
- Never access the user's root `test_pdfs/` directory or include supplied PDFs in test fixtures, logs, or remote workflows.
- Assert page count, order, rotation, metadata, paths, and stable user-facing errors; avoid byte-for-byte PDF comparisons.
- Cover both public operation functions and representative Typer commands. Keep tests deterministic and network-free.
