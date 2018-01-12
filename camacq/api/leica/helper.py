"""Helper functions for Leica api."""
import ntpath
import os
import re
from builtins import str  # pylint: disable=redefined-builtin

from matrixscreener import experiment


def find_image_path(relpath, root):
    """Parse the relpath from the server to find file path from root.

    Convert from windows path to os path.

    Parameters
    ----------
    relpath : string
        A relative path to the image.
    root : str
        Path to directory where path should start.

    Returns
    -------
    str
        Return path to image.
    """
    if not relpath:
        return
    paths = []
    while relpath:
        relpath, tail = ntpath.split(relpath)
        paths.append(tail)
    return str(os.path.join(root, *list(reversed(paths))))


def format_new_name(image_path, root=None, new_attr=None):
    """Create filename from image path and replace specific attributes.

    Parameters
    ----------
    image_path : string
        Path to image.
    root : str
        Path to directory where path should start.
    new_attr : dict
        Dictionary which maps experiment attributes to new attribute
        ids. The new attribute ids will replace the old ids for the
        corresponding attributes.

    Returns
    -------
    str
        Return new path to image.
    """
    if root is None:
        root = get_field(image_path)

    path = 'U{}--V{}--E{}--X{}--Y{}--Z{}--C{}.ome.tif'.format(
        *(experiment.attribute_as_str(image_path, attr)
          for attr in ('U', 'V', 'E', 'X', 'Y', 'Z', 'C')))
    if new_attr:
        for attr, attr_id in new_attr.items():
            path = re.sub(attr + r'\d\d', attr + attr_id, path)

    return os.path.normpath(os.path.join(root, path))


def get_field(path):
    """Get path to field from image path.

    Parameters
    ----------
    path : string
        Path to image.

    Returns
    -------
    str
        Return path to field directory of image.
    """
    return experiment.Experiment(path).dirname  # pylint: disable=no-member


def get_well(path):
    """Get path to well from image path.

    Parameters
    ----------
    path : string
        Path to image.

    Returns
    -------
    str
        Return path to well directory of image.
    """
    # pylint: disable=no-member
    return experiment.Experiment(get_field(path)).dirname


def get_imgs(path, img_type='tif', search=''):
    """Get all images below path.

    Parameters
    ----------
    path : string
        Path to directory where to search for images.
    img_type : string
        A string representing the image file type extension.
    path : string
        A glob pattern string to use in the search.

    Returns
    -------
    str
        Return paths of all images found.
    """
    if search:
        search = '{}*'.format(search)
    patterns = [
        'slide',
        'chamber',
        'field',
        'image',
    ]
    for pattern in patterns:
        if pattern not in path:
            path = os.path.join(path, '{}--*'.format(pattern))
    return experiment.glob('{}{}.{}'.format(path, search, img_type))
