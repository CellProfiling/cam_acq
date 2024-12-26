"""Handle images."""

import logging
from collections import defaultdict

import numpy as np
import tifffile
import xmltodict

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
    except OSError as exception:
        _LOGGER.error("Bad path to image: %s", exception)
        return None


def save_image(path, data, description=None):
    """Save a tif image with image data and meta data.

    Parameters
    ----------
    path : str
        The path to the image.
    data : numpy array
        A numpy array with the image data.
    description : str
        The description string of the image.
    """
    tifffile.imwrite(path, data, description=description)


def make_proj(images):
    """Make a dict of max projections from a dict of channels and paths.

    Each channel will make one max projection.

    Parameters
    ----------
    images : dict
        Dict of paths and channel ids.

    Returns
    -------
    dict
        Return a dict of channels that map ImageData objects.
        Each image object have a max projection as data.
    """
    _LOGGER.info("Making max projections...")
    sorted_images = defaultdict(list)
    max_imgs = {}
    for path, channel in images.items():
        image = ImageData(path=path)
        # Exclude images with 0, 16 or 256 pixel side.
        # pylint: disable=len-as-condition
        if len(image.data) == 0 or len(image.data) == 16 or len(image.data) == 256:
            continue
        sorted_images[channel].append(image)
        proj = np.max([img.data for img in sorted_images[channel]], axis=0)
        max_imgs[channel] = ImageData(path=path, data=proj, metadata=image.metadata)
    return max_imgs


class ImageData:
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
        self.description = None
        if metadata is not None:
            self.metadata = metadata

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
        if self.description is None:
            self._load_image_data()
        return xmltodict.parse(self.description)

    @metadata.setter
    def metadata(self, value):
        """Set the metadata of the image."""
        self.description = xmltodict.unparse(value)

    @property
    def histogram(self):
        """:numpy array: Calculate and return image histogram."""
        if self._data is None:
            self._load_image_data()
        if self._data.dtype.name == "uint16":
            max_int = 65535
        else:
            max_int = 255
        return np.histogram(self._data, bins=256, range=(0, max_int))

    def _load_image_data(self):
        """Load image data from path."""
        try:
            with tifffile.TiffFile(self.path) as tif:
                self._data = tif.asarray(key=0)
                self.description = tif.pages[0].description
        except (OSError, ValueError) as exception:
            _LOGGER.error("Bad path %s to image: %s", self.path, exception)

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
            data = self.data
        if metadata is None:
            metadata = self.metadata
        description = xmltodict.unparse(metadata)
        save_image(path, data, description)

    def __repr__(self):
        """Return the representation."""
        return f"ImageData(path={self.path})"
