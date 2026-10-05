from pathlib import Path

import cv2
import numpy as np
from typer.testing import CliRunner

from image_tools.cli import app

runner = CliRunner()


def test_resize_command_creates_requested_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "resized.jpg"
    image = np.zeros((8, 12, 3), dtype=np.uint8)
    assert cv2.imwrite(str(source), image)

    result = runner.invoke(
        app,
        [
            "resize",
            str(source),
            "--width",
            "63",
            "--height",
            "81",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    resized = cv2.imread(str(output))
    assert resized is not None
    assert (resized.shape[1], resized.shape[0]) == (63, 81)


def test_resize_command_reports_operation_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "resize",
            str(tmp_path / "missing.png"),
            "--width",
            "63",
            "--height",
            "81",
            "--output",
            str(tmp_path / "output.jpg"),
        ],
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output
