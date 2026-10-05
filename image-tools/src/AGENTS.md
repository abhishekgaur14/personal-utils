# Image Tools source guidance

- Keep CLI wiring in `image_tools/cli.py` and image operations in `image_tools/operations.py`.
- Keep every import at the top of the file.
- Raise `ImageToolsError` for expected user-correctable operation errors; the CLI translates these into concise messages.
