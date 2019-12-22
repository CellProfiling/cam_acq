"""Provide custom sample."""
import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.plugins.sample import Image, Sample, SampleEvent, register_sample

SET_SAMPLE_SCHEMA = vol.Schema(
    {vol.Required("x"): vol.Coerce(int), vol.Required("y"): vol.Coerce(int)}
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
        await self.set_image(event.path, event.x, event.y)

    def _set_sample(self, ids, **values):
        """Set an image container of the sample."""

    async def set_image(self, path, x, y):  # pylint: disable=invalid-name
        """Add an image to the sample."""
        image = CustomImage(path, x, y)
        self._images[image.path] = image

        await self.set_sample({"x": x, "y": y})
        return image


class CustomImage(Image):
    """Represent an image with path and position info."""

    # pylint: disable=too-few-public-methods, invalid-name

    def __init__(self, path, x, y):
        """Set up instance."""
        self._path = path
        self.x = x
        self.y = y

    @property
    def path(self):
        """Return the path of the image."""
        return self._path
