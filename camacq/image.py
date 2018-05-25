"""Handle images."""
import logging
from builtins import object  # pylint: disable=redefined-builtin
from collections import defaultdict

import numpy as np
import tifffile

_LOGGER = logging.getLogger(__name__)


def read_image(path):
    """Read a tif image and return the data.

    Parameters
    ----------
    path : str
        The path to the image.

    Returns
    -------
    numpy array
        Return a numpy array with image data.
    """
    try:
        return tifffile.imread(path, key=0)
    except IOError as exception:
        _LOGGER.error('Bad path to image: %s', exception)
        return np.array([])


def get_metadata(path):
    """Read a tif image and return the meta data of the description.

    Parameters
    ----------
    path : str
        The path to the image.

    Returns
    -------
    str
        Return the meta data of the description.
    """
    try:
        with tifffile.TiffFile(path) as tif:
            return tif.ome_metadata
    except IOError as exception:
        _LOGGER.error('Bad path to image: %s', exception)
        return {}


def save_image(path, data, metadata=None):
    """Save a tif image with image data and meta data.

    Parameters
    ----------
    path : str
        The path to the image.
    data : numpy array
        A numpy array with the image data.
    metadata : dict
        The meta data of the image as a JSON dict.
    """
    tifffile.imsave(path, data, metadata=metadata)


def make_proj(images):
    """Make a dict of max projections from a dict of channels and paths.

    Each channel will make one max projection.

    Parameters
    ----------
    images : dict
        Dict of channel ids and paths.

    Returns
    -------
    dict
        Return a dict of channels that map ImageData objects.
        Each image object have a max projection as data.
    """
    _LOGGER.info('Making max projections...')
    sorted_images = defaultdict(list)
    max_imgs = {}
    for channel, path in images.items():
        image = ImageData(path=path)
        # Exclude images with 0, 16 or 256 pixel side.
        # pylint: disable=len-as-condition
        if (len(image.data) == 0 or len(image.data) == 16 or
                len(image.data) == 256):
            continue
        sorted_images[channel].append(image)
        proj = np.max([img.data for img in sorted_images[channel]], axis=0)
        max_imgs[channel] = ImageData(
            path=path, data=proj, metadata=image.metadata)
    return max_imgs


class ImageData(object):
    """Represent the data of an image with path, data, metadata and histogram.

    Parameters
    ----------
    path : str
        Path to the image.
    data : numpy array
        A numpy array with the image data.
    metadata : dict
        The meta data of the image as a JSON dict.

    Attributes
    ----------
    path : str
        The path to the image.
    """

    # pylint: disable=too-many-arguments, too-many-instance-attributes

    def __init__(self, path=None, data=None, metadata=None):
        """Set up instance."""
        self.path = path
        self._data = data
        self._metadata = metadata or {}

    @property
    def data(self):
        """:numpy array: Return the data of the image.

        :setter: Set the data of the image.
        """
        if self._data is None:
            self._load_image_data()
        return self._data

    @data.setter
    def data(self, value):
        """Set the data of the image."""
        self._data = value

    @property
    def metadata(self):
        """:str: Return metadata of image.

        :setter: Set the meta data of the image.
        """
        if not self._metadata:
            self._load_image_data()
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        """Set the metadata of the image."""
        self._metadata = value

    @property
    def histogram(self):
        """:numpy array: Calculate and return image histogram."""
        if self._data is None:
            self._load_image_data()
        if self._data.dtype.name == 'uint16':
            max_int = 65535
        else:
            max_int = 255
        return np.histogram(self._data, 256, (0, max_int))

    def _load_image_data(self):
        """Load image data from path."""
        try:
            with tifffile.TiffFile(self.path) as tif:
                self._data = tif.asarray(key=0)
                self._metadata = tif.ome_metadata
        except (IOError, ValueError) as exception:
            _LOGGER.error('Bad path %s to image: %s', self.path, exception)
            self._data = np.array([])
            self._metadata = {}

    def save(self, path=None, data=None, metadata=None):
        """Save image with image data and optional meta data.

        Parameters
        ----------
        path : str
            The path to the image.
        data : numpy array
            A numpy array with the image data.
        metadata : dict
            The meta data of the image as a JSON dict.
        """
        if path is None:
            path = self.path
        if data is None:
            data = self._data
        if metadata is None:
            metadata = self._metadata
        save_image(path, data, metadata)

    def __repr__(self):
        """Return the representation."""
        return '<ImageData(path={0!r})>'.format(self.path)
