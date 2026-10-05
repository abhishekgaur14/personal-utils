"""Typer command-line interface for local image operations."""

from pathlib import Path
from typing import Annotated

import typer

from image_tools.operations import ImageToolsError, resize_image

app = typer.Typer(name="image-tools", help="Resize local images.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Resize local images to exact pixel dimensions."""


@app.command()
def resize(
    input: Annotated[Path, typer.Argument(help="Source image path.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output image path.")],
    width: Annotated[int, typer.Option(help="Exact output width in pixels.")],
    height: Annotated[int, typer.Option(help="Exact output height in pixels.")],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
) -> None:
    """Resize an image to the exact requested pixel dimensions."""

    try:
        output_path = resize_image(input, output, width, height, overwrite=overwrite)
    except ImageToolsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Resized {input} to {width}x{height}: {output_path}")


if __name__ == "__main__":
    app()
