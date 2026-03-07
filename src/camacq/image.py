"""Handle images."""

from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any

import numpy as np
from numpy import typing as npt
import tifffile
import xmltodict

_LOGGER = logging.getLogger(__name__)


def read_image(path: str) -> npt.NDArray[Any] | None:
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


def save_image(
    path: str, data: npt.NDArray[Any], description: str | None = None
) -> None:
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


def make_proj(images: dict[str, int]) -> dict[int, ImageData]:
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
    sorted_images: dict[int, list[ImageData]] = defaultdict(list)
    max_imgs: dict[int, ImageData] = {}
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

    def __init__(
        self,
        path: str | None = None,
        data: npt.NDArray[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Set up instance."""
        self.path = path
        self._data = data
        self.description: str | None = None
        if metadata is not None:
            self.metadata = metadata

    @property
    def data(self) -> npt.NDArray[Any]:
        """:numpy array: Return the data of the image.

        :setter: Set the data of the image.
        """
        if self._data is None:
            self._load_image_data()
            assert self._data is not None  # noqa: S101
        return self._data

    @data.setter
    def data(self, value: npt.NDArray[Any]) -> None:
        """Set the data of the image."""
        self._data = value

    @property
    def metadata(self) -> dict[str, Any]:
        """:str: Return metadata of image.

        :setter: Set the meta data of the image.
        """
        if self.description is None:
            self._load_image_data()
        description = self.description
        if description is None:
            return {}
        return xmltodict.parse(description)

    @metadata.setter
    def metadata(self, value: dict[str, Any]) -> None:
        """Set the metadata of the image."""
        self.description = xmltodict.unparse(value)

    @property
    def histogram(self) -> tuple[npt.NDArray[Any], npt.NDArray[Any]]:
        """:numpy array: Calculate and return image histogram."""
        if self._data is None:
            self._load_image_data()
        data = self._data
        assert data is not None  # noqa: S101
        if data.dtype.name == "uint16":
            max_int = 65535
        else:
            max_int = 255
        return np.histogram(data, bins=256, range=(0, max_int))

    def _load_image_data(self) -> None:
        """Load image data from path."""
        if self.path is None:
            _LOGGER.error("Cannot load image data: path is None")
            return
        try:
            with tifffile.TiffFile(self.path) as tif:
                self._data = tif.asarray(key=0)
                page = tif.pages[0]
                self.description = getattr(page, "description", "")
        except (OSError, ValueError) as exception:
            _LOGGER.error("Bad path %s to image: %s", self.path, exception)

    def save(
        self,
        path: str | None = None,
        data: npt.NDArray[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
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
        save_image(path, data, description)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        """Return the representation."""
        return f"ImageData(path={self.path})"
