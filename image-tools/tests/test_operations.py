from pathlib import Path

import cv2
import numpy as np
import pytest

from image_tools.operations import ImageToolsError, resize_image


def _write_test_image(path: Path, width: int = 12, height: int = 8) -> None:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :, 2] = 255
    assert cv2.imwrite(str(path), image)


def test_resize_image_writes_exact_dimensions_and_preserves_color(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "resized.jpg"
    _write_test_image(source)

    result = resize_image(source, output, width=63, height=81)

    resized = cv2.imread(str(result))
    assert resized is not None
    assert (resized.shape[1], resized.shape[0]) == (63, 81)
    assert resized[:, :, 2].mean() > resized[:, :, 0].mean()


@pytest.mark.parametrize(("width", "height"), [(0, 10), (10, 0), (-1, 10)])
def test_resize_image_rejects_non_positive_dimensions(
    tmp_path: Path, width: int, height: int
) -> None:
    source = tmp_path / "source.png"
    _write_test_image(source)

    with pytest.raises(ImageToolsError, match="positive"):
        resize_image(source, tmp_path / "output.png", width=width, height=height)


def test_resize_image_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(ImageToolsError, match="does not exist"):
        resize_image(tmp_path / "missing.png", tmp_path / "output.png", 10, 10)


def test_resize_image_rejects_output_equal_to_input(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _write_test_image(source)

    with pytest.raises(ImageToolsError, match="must differ"):
        resize_image(source, source, 10, 10)


def test_resize_image_refuses_to_overwrite_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    _write_test_image(source)
    output.write_bytes(b"keep this")

    with pytest.raises(ImageToolsError, match="already exists"):
        resize_image(source, output, 10, 10)

    assert output.read_bytes() == b"keep this"


def test_resize_image_rejects_unsupported_or_invalid_image(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("not an image")

    with pytest.raises(ImageToolsError, match="[Cc]ould not read"):
        resize_image(source, tmp_path / "output.jpg", 10, 10)
