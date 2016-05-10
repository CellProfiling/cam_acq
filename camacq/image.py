"""Handle images."""
import logging
from collections import defaultdict

import numpy as np
import tifffile
from matrixscreener import experiment
from PIL import Image

_LOGGER = logging.getLogger(__name__)


def read_image(path):
    """Read a tif image and return the data."""
    try:
        return np.array(Image.open(path))
    except IOError as exception:
        _LOGGER.error('Bad path! %s', exception)
        return np.array([])


def meta_data(path):
    """Read a tif image and return the meta data of the description."""
    try:
        with tifffile.TiffFile(path) as tif:
            return tif[0].image_description
    except IOError as exception:
        _LOGGER.error('Bad path! %s', exception)
        return ''


def save_image(path, data, metadata=None):
    """Save a tif image with image data and meta data."""
    tifffile.imsave(path, data, description=metadata)


def make_proj(path_list):
    """Make a dict of max projections from a list of image paths.

    Each channel will make one max projection.
    """
    _LOGGER.info('Making max projections')
    sorted_images = defaultdict(list)
    max_imgs = {}
    for path in path_list:
        channel = '{}'.format(experiment.attribute_as_str(path, 'C'))
        sorted_images[channel].append(read_image(path=path))
        max_imgs[channel] = np.max(sorted_images[channel], axis=0)
    return max_imgs
