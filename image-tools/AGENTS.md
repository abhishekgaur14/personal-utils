# Image Tools project guidance

- This is a local command-line image utility built with Typer and OpenCV. Keep command parsing in `src/image_tools/cli.py` and image processing in `src/image_tools/operations.py`.
- Keep all imports at the top of each Python file; do not add imports inside functions or conditionals.
- Ruff is the project linter and import sorter. Run `uv run ruff check .` and `uv run ruff format --check .`; use `uv run ruff check --fix .` to auto-fix lint and sort imports, and `uv run ruff format .` to format files.
- Run the suite with `uv run pytest` from this directory. Use generated synthetic images for automated tests.
- Treat all files in the repository root `test_assets/` folder as private local inputs. Never copy them elsewhere, print their contents, commit them, or upload them.
- Image outputs must use exact requested pixel dimensions. Reject invalid sizes, unreadable inputs, output paths resolving to the input, and existing outputs; do not silently overwrite.
- Do not push changes unless the user explicitly asks.
