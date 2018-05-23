"""Handle images."""
import logging
from collections import defaultdict

import numpy as np
import tifffile
from matrixscreener import experiment

_LOGGER = logging.getLogger(__name__)


def read_image(path):
    """Read a tif image and return the data."""
    try:
        return tifffile.imread(path, key=0)
    except IOError as exception:
        _LOGGER.error('Bad path to image! %s', exception)
        return np.array([])


def get_metadata(path):
    """Read a tif image and return the meta data of the description."""
    try:
        with tifffile.TiffFile(path) as tif:
            return tif[0].image_description
    except IOError as exception:
        _LOGGER.error('Bad path to image! %s', exception)
        return ''


def save_image(path, data, metadata=None):
    """Save a tif image with image data and meta data."""
    tifffile.imsave(path, data, description=metadata)


def make_proj(path_list):
    """Make a dict of max projections from a list of image paths.

    Each channel will make one max projection.

    Parameters
    ----------
    path_list : list
        List of paths to images.

    Returns
    -------
    dict
        Return a dict of channels that map image objects.
        Each image object have a max projection as data.
    """
    _LOGGER.info('Making max projections...')
    sorted_images = defaultdict(list)
    max_imgs = {}
    for path in path_list:
        channel = '{}'.format(experiment.attribute_as_str(path, 'C'))
        image = Image(path)
        # Exclude images with 0, 16 or 256 pixel side.
        if (len(image.data) == 0 or len(image.data) == 16 or
                len(image.data) == 256):
            continue
        sorted_images[channel].append(image)
        proj = np.max([img.data for img in sorted_images[channel]], axis=0)
        max_imgs[channel] = Image(data=proj, metadata=image.metadata)
    return max_imgs


class Image(object):
    """Represent an image with a path, data, metadata and histogram.

    Attributes
    ----------
    path : str
        Path to image.
    """

    def __init__(self, path=None, data=None, metadata=None):
        """Set up instance attributes.

        Parameters
        ----------
        path : str
            Path to image.
        data : numpy.ndarray
            Numpy array with data of image.
        metadata : str
            Metadata (description) of image.
        """
        self.path = path
        self._data = data
        self._metadata = metadata
        if path:
            try:
                with tifffile.TiffFile(path) as tif:
                    self._data = tif[0].asarray()
                    self._metadata = tif[0].image_description
            except IOError as exception:
                _LOGGER.error('Bad path to image! %s', exception)

    @property
    def data(self):
        """Return the data of the image."""
        return self._data

    @data.setter
    def data(self, value):
        """Set the data of the image."""
        self._data = value

    @property
    def metadata(self):
        """Return metadata of image."""
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        """Set the metadata of the image."""
        self._metadata = value

    @property
    def histogram(self):
        """Calculate and return image histogram."""
        if self._data.dtype.name == 'uint16':
            max_int = 65535
        else:
            max_int = 255
        return np.histogram(self._data, 256, (0, max_int))

    def save(self, path=None, data=None, metadata=None):
        """Save image with image data and optional meta data."""
        if path is None:
            path = self.path
        if data is None:
            data = self._data
        if metadata is None:
            metadata = self._metadata
        save_image(path, data, metadata)

    def __repr__(self):
        """Return the representation."""
        return '<Image(path={0!r}, data={1!r}, metadata={2!r})>'.format(
            self.path, self._data, self._metadata)
