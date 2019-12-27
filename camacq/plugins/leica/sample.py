"""Provide sample implementation for leica microscope."""
import logging

import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.plugins.sample import (
    Image,
    ImageContainer,
    Sample,
    SampleEvent,
    register_sample,
)

_LOGGER = logging.getLogger(__name__)
LEICA_SAMPLE_EVENT = "leica_sample_event"
CHANNEL_EVENT = "channel_event"
FIELD_EVENT = "field_event"
IMAGE_REMOVED_EVENT = "image_removed_event"
PLATE_EVENT = "plate_event"
SAMPLE_IMAGE_EVENT = "sample_image_event"
WELL_EVENT = "well_event"
Z_SLICE_EVENT = "z_slice_event"

SET_PLATE_SCHEMA = vol.Schema({vol.Required("plate_name"): vol.Coerce(str)})

SET_WELL_SCHEMA = SET_PLATE_SCHEMA.extend(
    {vol.Required("well_x"): vol.Coerce(int), vol.Required("well_y"): vol.Coerce(int)}
)

SET_FIELD_SCHEMA = SET_WELL_SCHEMA.extend(
    {
        vol.Required("field_x"): vol.Coerce(int),
        vol.Required("field_y"): vol.Coerce(int),
    }
)

SET_CHANNEL_SCHEMA = SET_WELL_SCHEMA.extend(
    {vol.Required("channel_name"): vol.Coerce(str), "channel_id": vol.Coerce(int),}
)

SET_SAMPLE_SCHEMA = vol.Any(
    SET_PLATE_SCHEMA, SET_WELL_SCHEMA, SET_FIELD_SCHEMA, SET_CHANNEL_SCHEMA
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
    sample = LeicaSample()
    register_sample(center, sample)


class LeicaSample(Sample):
    """Representation of the state of the sample.

    The sample can have plates, wells, fields, channels and images.

    Parameters
    ----------
    images : dict
        A dict of images of the sample.

    Attributes
    ----------
    images : dict
        Return a dict of Image instances.
    """

    def __init__(self, images=None, values=None):
        """Set up instance."""
        self._images = images or {}
        self._values = values or {}

    def __repr__(self):
        """Return the representation."""
        return f"Sample(images={self._images}, values={self._values})"

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return LeicaSampleEvent

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
        return "leica"

    @property
    def set_sample_schema(self):
        """Return the validation schema of the set_sample method."""
        return SET_SAMPLE_SCHEMA

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values

    async def on_image(self, center, event):
        """Handle image event for this sample."""
        field_args = {
            "plate_name": event.plate_name,
            "well_x": event.well_x,
            "well_y": event.well_y,
            "field_x": event.field_x,
            "field_y": event.field_y,
        }
        image = LeicaImage(
            event.path, channel_id=event.channel_id, z_slice=event.z_slice, **field_args
        )
        await self.set_image(image)
        await self.set_sample(**field_args)
        field_args.pop("field_x")
        field_args.pop("field_y")
        z_slice_args = {**field_args, "z_slice": event.z_slice}
        await self.set_sample(**z_slice_args)
        z_slice_args.pop("z_slice")
        channel_args = {**z_slice_args, "channel_id": event.channel_id}
        await self.set_sample(**channel_args)

    async def _set_sample(self, values, **kwargs):
        """Set an image container of the sample."""
        plate_name = kwargs.get("plate_name")
        well_x = kwargs.get("well_x")
        well_y = kwargs.get("well_y")
        field_x = kwargs.get("field_x")
        field_y = kwargs.get("field_y")
        z_slice = kwargs.get("z_slice")
        channel_id = kwargs.get("channel_id")

        if all(
            name is not None for name in (plate_name, well_x, well_y, field_x, field_y)
        ):
            await self.set_sample(plate_name=plate_name)
            await self.set_sample(plate_name=plate_name, well_x=well_x, well_y=well_y)

            field = Field(
                self._images,
                plate_name=plate_name,
                well_x=well_x,
                well_y=well_y,
                field_x=field_x,
                field_y=field_y,
                values=values,
            )
            return field

        if all(name is not None for name in (plate_name, well_x, well_y, channel_id)):
            await self.set_sample(plate_name=plate_name)
            await self.set_sample(plate_name=plate_name, well_x=well_x, well_y=well_y)

            channel = Channel(
                self._images,
                plate_name=plate_name,
                well_x=well_x,
                well_y=well_y,
                channel_id=channel_id,
                values=values,
            )
            return channel

        if all(name is not None for name in (plate_name, well_x, well_y, z_slice)):
            await self.set_sample(plate_name=plate_name)
            await self.set_sample(plate_name=plate_name, well_x=well_x, well_y=well_y)

            z_slice_container = ZSlice(
                self._images,
                plate_name=plate_name,
                well_x=well_x,
                well_y=well_y,
                z_slice=z_slice,
                values=values,
            )
            return z_slice_container

        if all(name is not None for name in (plate_name, well_x, well_y)):
            await self.set_sample(plate_name=plate_name)

            well = Well(
                self._images,
                plate_name=plate_name,
                well_x=well_x,
                well_y=well_y,
                values=values,
            )
            return well

        if plate_name is None:
            return None
        plate = Plate(self._images, plate_name=plate_name, values=values)
        return plate


class Plate(ImageContainer):
    """A container for wells.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    name: str
        The name of the plate.

    Attributes
    ----------
    name: str
        The name of the plate.
    """

    def __init__(self, images, plate_name, **kwargs):
        """Set up instance."""
        self._images = images
        self.plate_name = plate_name
        self._values = kwargs.pop("values", {})

    def __repr__(self):
        """Return the representation."""
        return (
            f"Plate(images={self._images}, name={self.plate_name}, "
            f"values={self._values})"
        )

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return PlateEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the plate."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.plate_name
        }

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class Well(Plate, ImageContainer):
    """A well within a plate with fields and channels.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    well_x : int
        x coordinate of the well, minimum 0.
    well_y : int
        y coordinate of the well, minimum 0.

    Attributes
    ----------
    well_x : int
        Number showing the x coordinate of the well, from 0.
    well_y : int
        Number showing the y coordinate of the well, from 0.
    """

    def __init__(self, images, well_x, well_y, **kwargs):
        """Set up instance."""
        self._images = images
        self.well_x = well_x
        self.well_y = well_y
        self._values = kwargs.pop("values", {})
        super().__init__(images, **kwargs)

    def __repr__(self):
        """Return the representation."""
        return (
            f"Well(images={self._images}, well_x={self.well_x}, "
            f"well_y={self.well_y}, values={self._values})"
        )

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return WellEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the well."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.plate_name
            and image.well_x == self.well_x
            and image.well_y == self.well_y
        }

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class Field(Well, ImageContainer):
    """A field within a well.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    field_x : int
        Coordinate of field in x.
    field_y : int
        Coordinate of field in y.

    Attributes
    ----------
    field_x : int
        Number showing the x coordinate of the field, from 0.
    field_y : int
        Number showing the y coordinate of the field, from 0.
    """

    def __init__(self, images, field_x, field_y, **kwargs):
        """Set up instance."""
        self._images = images
        self.field_x = field_x
        self.field_y = field_y
        self._values = kwargs.pop("values", {})
        super().__init__(images, **kwargs)

    def __repr__(self):
        """Return the representation."""
        return (
            f"Field(images={self._images}, field_x={self.field_x}, "
            f"field_y={self.field_y}, values={self._values})"
        )

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return FieldEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the field."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.plate_name
            and image.well_x == self.well_x
            and image.well_y == self.well_y
            and image.field_x == self.field_x
            and image.field_y == self.field_y
        }

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class Channel(Well, ImageContainer):
    """A channel with attributes.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    channel_id : int
        ID of the channel.
    values : Optional dict of values.

    Attributes
    ----------
    channel_id : int
        Return channel_id of the channel.
    """

    def __init__(self, images, channel_id, **kwargs):
        """Set up instance."""
        self._images = images
        self.channel_id = channel_id
        self._values = kwargs.pop("values", {})
        super().__init__(images, **kwargs)

    def __repr__(self):
        """Return the representation."""
        return (
            f"Channel(images={self._images}, channel_id={self.channel_id}, "
            f"values={self._values})"
        )

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return ChannelEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the channel."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.plate_name
            and image.well_x == self.well_x
            and image.well_y == self.well_y
            and image.channel_id == self.channel_id
        }

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class ZSlice(Well, ImageContainer):
    """A channel with attributes.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    z_slice : int
        ID of the slice.
    values : Optional dict of values.

    Attributes
    ----------
    z_slice : int
        Return z_slice of the channel.
    """

    def __init__(self, images, z_slice, **kwargs):
        """Set up instance."""
        self._images = images
        self.z_slice = z_slice
        self._values = kwargs.pop("values", {})
        super().__init__(images, **kwargs)

    def __repr__(self):
        """Return the representation."""
        return (
            f"ZSlice(images={self._images}, slice_id={self.z_slice}, "
            f"values={self._values})"
        )

    @property
    def change_event(self):
        """:Event: Return an event class to fire on container change."""
        return ZSliceEvent

    @property
    def images(self):
        """:dict: Return a dict with all images for the channel."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.plate_name
            and image.well_x == self.well_x
            and image.well_y == self.well_y
            and image.z_slice == self.z_slice
        }

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


class LeicaImage(Image):
    """An image with path and position info.

    Parameters
    ----------
    path : str
        Path to the image.
    channel_id : int
        The channel id of the image.
    z_slice : int
        The z index of the image.
    field_x : int
        The field x coordinate of the image.
    field_y : int
        The field y coordinate of the image.
    well_x : int
        The well x coordinate of the image.
    well_y : int
        The well y coordinate of the image.
    plate_name : str
        The name of the plate.

    Attributes
    ----------
    channel_id : int
        The channel id of the image.
    z_slice : int
        The z index of the image.
    field_x : int
        The field x coordinate of the image.
    field_y : int
        The field y coordinate of the image.
    well_x : int
        The well x coordinate of the image.
    well_y : int
        The well y coordinate of the image.
    plate_name : str
        The name of the plate.
    """

    # pylint: disable=too-many-arguments, too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self, path, channel_id, z_slice, field_x, field_y, well_x, well_y, plate_name,
    ):
        """Set up instance."""
        self._path = path
        self.channel_id = channel_id
        self.z_slice = z_slice
        self.field_x = field_x
        self.field_y = field_y
        self.well_x = well_x
        self.well_y = well_y
        self.plate_name = plate_name

    @property
    def path(self):
        """Return the path of the image."""
        return self._path


# pylint: disable=too-few-public-methods
class LeicaSampleEvent(SampleEvent):
    """An event produced by a sample change event."""

    __slots__ = ()

    event_type = LEICA_SAMPLE_EVENT


class PlateEvent(LeicaSampleEvent):
    """An event produced by a sample plate change event."""

    __slots__ = ()

    event_type = PLATE_EVENT

    @property
    def plate_name(self):
        """:str: Return the name of the plate."""
        return self.container.plate_name


class WellEvent(PlateEvent):
    """An event produced by a sample well change event."""

    __slots__ = ()

    event_type = WELL_EVENT

    @property
    def well_x(self):
        """:int: Return the well x coordinate of the event."""
        return self.container.well_x

    @property
    def well_y(self):
        """:int: Return the well y coordinate of the event."""
        return self.container.well_y

    @property
    def well_img_ok(self):
        """:bool: Return if the well has all images acquired ok."""
        return self.container.values.get("well_img_ok", False)


class ChannelEvent(WellEvent):
    """An event produced by a sample channel change event."""

    __slots__ = ()

    event_type = CHANNEL_EVENT

    @property
    def channel_id(self):
        """:int: Return the channel id of the event."""
        return self.container.channel_id

    @property
    def channel_name(self):
        """:str: Return the channel name of the event."""
        return self.container.values.get("channel_name")


class FieldEvent(WellEvent):
    """An event produced by a sample field change event."""

    __slots__ = ()

    event_type = FIELD_EVENT

    @property
    def field_x(self):
        """:int: Return the field x coordinate of the event."""
        return self.container.field_x

    @property
    def field_y(self):
        """:int: Return the field y coordinate of the event."""
        return self.container.field_y

    @property
    def field_img_ok(self):
        """:bool: Return if the field has all images acquired ok."""
        return self.container.values.get("field_img_ok", False)


class ZSliceEvent(WellEvent):
    """An event produced by a sample z slice change event."""

    __slots__ = ()

    event_type = Z_SLICE_EVENT

    @property
    def z_slice(self):
        """:int: Return the z_slice of the event."""
        return self.container.z_slice
