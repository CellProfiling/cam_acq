"""Test the leica helper functions."""
from pathlib import PureWindowsPath

from camacq.plugins.leica.helper import find_image_path

from tests.common import IMAGE_PATH


def test_find_image_path():
    """Test find image path."""
    parts = IMAGE_PATH.parts
    root = parts[0]
    relpath = parts[1:]
    windows_path = PureWindowsPath("")
    relpath = windows_path.joinpath(*relpath)

    path = find_image_path(str(relpath), root)

    assert path == str(IMAGE_PATH)
