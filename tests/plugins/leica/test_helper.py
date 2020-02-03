"""Test the leica helper functions."""
from pathlib import PureWindowsPath

from camacq.plugins.leica.helper import find_image_path, get_field, get_imgs, get_well

from tests.common import FIELD_PATH, IMAGE_PATH, WELL_PATH


def test_find_image_path():
    """Test find image path."""
    parts = IMAGE_PATH.parts
    root = parts[0]
    relpath = parts[1:]
    windows_path = PureWindowsPath("")
    relpath = windows_path.joinpath(*relpath)

    path = find_image_path(str(relpath), root)

    assert path == str(IMAGE_PATH)


def test_get_field():
    """Test get field."""
    path = get_field(IMAGE_PATH)

    assert path == str(IMAGE_PATH.parent)


def test_get_well():
    """Test get well."""
    path = get_well(IMAGE_PATH)

    assert path == str(WELL_PATH)


def test_get_imgs():
    """Test get imgs."""
    images = get_imgs(str(WELL_PATH), search="C31")

    assert len(images) == 6

    images = get_imgs(str(FIELD_PATH), search="C22")

    assert len(images) == 3
