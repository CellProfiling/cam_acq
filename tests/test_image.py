"""Provide tests for the image module."""

from pathlib import Path
import tempfile

import numpy as np
import pytest

from camacq import image

from tests.common import IMAGE_PATH


@pytest.fixture(name="save_path")
def save_path_fixture():
    """Return a path to temporary dir."""
    temp_dir = tempfile.gettempdir()
    test_image_path = Path(temp_dir) / "test.tif"
    yield test_image_path.as_posix()
    if not test_image_path.is_file():
        return
    test_image_path.unlink()


def test_save_image(save_path):
    """Test save image."""
    data = image.read_image(IMAGE_PATH.as_posix())
    image.save_image(save_path, data)
    saved_data = image.read_image(save_path)

    assert np.array_equal(data, saved_data)


def test_image_data(save_path):
    """Test ImageData class."""
    orig_path = IMAGE_PATH.as_posix()
    img = image.ImageData(orig_path)
    print(img.metadata)
    orig_data = img.data
    orig_metadata = img.metadata
    img.save(save_path)
    img = image.ImageData(save_path)

    assert np.array_equal(orig_data, img.data)
    assert orig_metadata == img.metadata
