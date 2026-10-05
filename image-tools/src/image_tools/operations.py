"""Image processing operations."""

from pathlib import Path

import cv2


class ImageToolsError(Exception):
    """Expected error caused by invalid input or operation parameters."""


def resize_image(
    source: Path,
    output: Path,
    width: int,
    height: int,
    *,
    overwrite: bool = False,
) -> Path:
    """Resize an image to exact pixel dimensions."""

    if width <= 0 or height <= 0:
        raise ImageToolsError("Width and height must be positive pixel dimensions.")

    source_path = source.expanduser().resolve()
    output_path = output.expanduser().resolve()
    if source_path == output_path:
        raise ImageToolsError("Input and output paths must differ.")
    if not source_path.is_file():
        raise ImageToolsError(f"Input image does not exist or is not a file: {source}")
    if output_path.exists() and not overwrite:
        raise ImageToolsError(f"Output already exists: {output}")
    if not output_path.parent.is_dir():
        raise ImageToolsError(f"Output directory does not exist: {output_path.parent}")
    if not output_path.suffix:
        raise ImageToolsError("Output path must have an image extension.")

    image = cv2.imread(str(source_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ImageToolsError(f"Could not read an image from: {source}")

    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    try:
        success, encoded = cv2.imencode(output_path.suffix, resized)
    except cv2.error as exc:
        raise ImageToolsError(
            f"Unsupported output image extension: {output_path.suffix}"
        ) from exc
    if not success:
        raise ImageToolsError(f"Could not encode output image: {output}")

    try:
        output_path.write_bytes(encoded.tobytes())
    except OSError as exc:
        raise ImageToolsError(f"Could not write output image: {output}") from exc
    return output_path
