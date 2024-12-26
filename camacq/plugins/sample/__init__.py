"""Handle sample state."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod

import voluptuous as vol

from camacq.event import Event
from camacq.exceptions import SampleError
from camacq.helper import BASE_ACTION_SCHEMA
from camacq.util import dotdict

_LOGGER = logging.getLogger(__name__)
SAMPLE_EVENT = "sample_event"
SAMPLE_IMAGE_SET_EVENT = "sample_image_set_event"

ACTION_SET_SAMPLE = "set_sample"
SET_SAMPLE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend(
    {"sample_name": vol.Coerce(str)}, extra=vol.ALLOW_EXTRA
)
BASE_SET_SAMPLE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend(
    {vol.Required("name"): vol.Coerce(str), "values": dict}
)

ACTION_TO_METHOD = {
    ACTION_SET_SAMPLE: {"method": "set_sample", "schema": SET_SAMPLE_ACTION_SCHEMA},
}


async def setup_module(center, config):
    """Set up sample module.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """

    async def handle_action(**kwargs):
        """Handle action call to add a state to the sample.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to a
            method when an action is called.
        """
        action_id = kwargs.pop("action_id")
        method = ACTION_TO_METHOD[action_id]["method"]
        sample_name = kwargs.pop("sample_name", None)
        silent = kwargs.pop("silent", False)
        if sample_name:
            samples = [center.samples[sample_name]]
        else:
            samples = list(center.samples.values())
        tasks = []
        for sample in samples:
            try:
                kwargs = sample.set_sample_schema(kwargs)
            except vol.Invalid as exc:
                _LOGGER.log(
                    logging.DEBUG if silent else logging.ERROR,
                    "Invalid action call parameters %s: %s for action: %s.%s",
                    kwargs,
                    exc,
                    "sample",
                    action_id,
                )
                continue

            _LOGGER.debug(
                "Handle sample %s action %s: %s", sample.name, action_id, kwargs
            )
            tasks.append(center.create_task(getattr(sample, method)(**kwargs)))
        if tasks:
            await asyncio.wait(tasks)

    for action_id, options in ACTION_TO_METHOD.items():
        schema = options["schema"]
        center.actions.register("sample", action_id, handle_action, schema)


class Samples(dotdict):
    """Hold all samples."""

    # pylint: disable=too-few-public-methods

    def __getattr__(self, sample_name):
        """Get a sample by name."""
        try:
            return self[sample_name]
        except KeyError as exc:
            raise SampleError(f"Unable to get sample with name {sample_name}") from exc


def register_sample(center, sample):
    """Register sample."""
    sample.center = center
    sample.data = {}
    center.bus.register(sample.image_event_type, sample.on_image)
    center.samples[sample.name] = sample


class ImageContainer(ABC):
    """A container for images."""

    @property
    @abstractmethod
    def change_event(self):
        """:Event: Return an event class to fire on container change."""

    @property
    @abstractmethod
    def images(self):
        """:dict: Return a dict with all images for the container."""

    @property
    @abstractmethod
    def name(self):
        """:str: Return an identifying name for the container."""

    @property
    @abstractmethod
    def values(self):
        """:dict: Return a dict with the values set for the container."""


class Sample(ImageContainer, ABC):
    """Representation of the state of the sample."""

    center = None
    data = None

    @property
    @abstractmethod
    def image_event_type(self):
        """:str: Return the image event type to listen to for the sample."""

    @property
    @abstractmethod
    def name(self):
        """:str: Return the name of the sample."""

    @property
    @abstractmethod
    def set_sample_schema(self):
        """Return the validation schema of the set_sample method."""

    @abstractmethod
    async def on_image(self, center, event):
        """Handle image event for this sample."""

    def get_sample(self, name, **kwargs):
        """Get an image container of the sample.

        Parameters
        ----------
        name : str
            The name of the container type.
        **kwargs
            Arbitrary keyword arguments.
            These will be used to create the id string of the container.

        Returns
        -------
        ImageContainer instance
            Return the found ImageContainer instance.
        """
        id_string = json.dumps({"name": name, **kwargs})
        return self.data.get(id_string)

    async def set_sample(self, name, values=None, **kwargs):
        """Set an image container of the sample.

        Parameters
        ----------
        name : str
            The name of the container type.
        values : dict
            The optional values to set on the container.
        **kwargs
            Arbitrary keyword arguments.
            These will be used to create the id string of the container.

        Returns
        -------
        ImageContainer instance
            Return the ImageContainer instance that was updated.
        """
        id_string = json.dumps({"name": name, **kwargs})
        values = values or {}
        container = self.data.get(id_string)
        event = None

        if container is None:
            container = await self._set_sample(name, values, **kwargs)
            event_class = container.change_event
            event = event_class({"container": container})

        container.values.update(values)
        self.data[id_string] = container

        if name == "image":
            self.images[container.path] = container

        if not event and values:
            event_class = container.change_event
            event = event_class({"container": container})

        if event:
            await self.center.bus.notify(event)
        return container

    @abstractmethod
    async def _set_sample(self, name, values, **kwargs):
        """Set an image container of the sample.

        Parameters
        ----------
        name : str
            The name of the container type.
        values : dict
            The values to set on the container.
        **kwargs
            Arbitrary keyword arguments.

        Returns
        -------
        ImageContainer instance
            Return the ImageContainer instance that was updated.
        """


class Image(ImageContainer):
    """An image with path and position info."""

    def __init__(self, path, values=None, **kwargs):
        """Set up instance."""
        self._path = path
        self._values = values or {}
        for attr, val in kwargs.items():
            setattr(self, attr, val)

    def __repr__(self):
        """Return the representation."""
        return f"<Image(path={self.path}, values={self.values})>"

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return SampleImageSetEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the container."""
        return {self.path: self}

    @property
    def name(self):
        """:str: Return an identifying name for the container."""
        return "image"

    @property
    def path(self):
        """:str: Return the path of the image."""
        return self._path

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class SampleEvent(Event):
    """An event produced by a sample change event."""

    __slots__ = ()

    event_type = SAMPLE_EVENT

    @property
    def container(self):
        """:ImageContainer instance: Return the container instance of the event."""
        return self.data.get("container")

    @property
    def container_name(self):
        """:str: Return the container name of the event."""
        return self.container.name

    @property
    def images(self):
        """:dict: Return the container images of the event."""
        return self.container.images

    @property
    def values(self):
        """:dict: Return the container values of the event."""
        return self.container.values

    def __repr__(self):
        """Return the representation."""
        data = {"container": self.container}
        return f"{type(self).__name__}(data={data})"


class SampleImageSetEvent(SampleEvent):
    """An event produced by a new image on the sample."""

    __slots__ = ()

    event_type = SAMPLE_IMAGE_SET_EVENT


def get_matched_samples(sample, name, attrs=None, values=None):
    """Return the sample items that match."""
    attrs = attrs or {}
    values = values or {}
    items = [
        cont
        for cont in sample.data.values()
        if cont.name == name
        and (
            not attrs
            or all(getattr(cont, attr, None) == val for attr, val in attrs.items())
        )
        and (
            not values
            or all(cont.values.get(key) == val for key, val in values.items())
        )
    ]
    return items
