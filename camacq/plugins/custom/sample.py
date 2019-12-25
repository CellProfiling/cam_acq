"""Provide custom sample."""
import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.plugins.sample import (
    Image,
    ImageContainer,
    Sample,
    SampleEvent,
    register_sample,
)

SET_SAMPLE_SCHEMA = vol.Schema(
    {vol.Required("fov_x"): vol.Coerce(int), vol.Required("fov_y"): vol.Coerce(int)}
)


async def setup_module(center, config):
    """Set up sample module.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    sample = CustomSample()
    register_sample(center, sample)


class CustomSample(Sample):
    """Represent a custom sample."""

    def __init__(self, images=None):
        """Set up instance."""
        self._images = images or {}

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change."""
        return SampleEvent

    @property
    def image_event_type(self):
        """:str: Return the image event type to listen to for the sample."""
        return IMAGE_EVENT

    @property
    def images(self):
        """:dict: Return a dict with all images for the container."""
        return self._images

    @property
    def name(self):
        """Return the name of the sample."""
        return "custom"

    @property
    def set_sample_schema(self):
        """Return the validation schema of the set_sample method."""
        return SET_SAMPLE_SCHEMA

    async def on_image(self, center, event):
        """Handle image event for this sample."""
        await self.set_image(event.path, event.fov_x, event.fov_y)

    def _set_sample(self, values, **kwargs):
        """Set an image container of the sample."""
        fov_x = kwargs.pop("fov_x", None)
        fov_y = kwargs.pop("fov_y", None)
        fov = FOVContainer(self._images, fov_x, fov_y, values)
        return fov

    async def set_image(self, path, fov_x, fov_y):
        """Add an image to the sample."""
        image = CustomImage(path, fov_x, fov_y)
        self._images[image.path] = image

        await self.set_sample(fov_x=fov_x, fov_y=fov_y)
        return image


class CustomImage(Image):
    """Represent an image with path and position info."""

    # pylint: disable=too-few-public-methods

    def __init__(self, path, fov_x, fov_y):
        """Set up instance."""
        self._path = path
        self.fov_x = fov_x
        self.fov_y = fov_y

    @property
    def path(self):
        """Return the path of the image."""
        return self._path


class FOVContainer(ImageContainer):
    """A FOV within sample."""

    def __init__(self, images, fov_x, fov_y, values):
        """Set up instance."""
        self._images = images
        self.fov_x = fov_x
        self.fov_y = fov_y
        for attr, val in values.items():
            setattr(self, attr, val)

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change.

        :setter: Set the change event.
        """
        return FOVEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the field."""
        return {
            image.path: image
            for image in self._images.values()
            if image.fov_x == self.fov_x and image.fov_y == self.fov_y
        }


class FOVEvent(SampleEvent):
    """An event produced by a sample field change event."""

    __slots__ = ()

    event_type = "xy_event"

    @property
    def fov_x(self):
        """:int: Return the field x coordinate of the event."""
        return self.container.fov_x

    @property
    def fov_y(self):
        """:int: Return the field y coordinate of the event."""
        return self.container.fov_y
