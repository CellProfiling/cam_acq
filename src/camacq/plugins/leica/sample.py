"""Provide sample implementation for leica microscope."""

import json

import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.plugins.sample import (
    BASE_SET_SAMPLE_ACTION_SCHEMA,
    Image,
    ImageContainer,
    Sample,
    SampleEvent,
    register_sample,
)

LEICA_SAMPLE_EVENT = "leica_sample_event"
CHANNEL_EVENT = "channel_event"
FIELD_EVENT = "field_event"
PLATE_EVENT = "plate_event"
WELL_EVENT = "well_event"
Z_SLICE_EVENT = "z_slice_event"

SET_PLATE_SCHEMA = BASE_SET_SAMPLE_ACTION_SCHEMA.extend(
    {vol.Required("name"): "plate", vol.Required("plate_name"): vol.Coerce(str)}
)

SET_WELL_SCHEMA = SET_PLATE_SCHEMA.extend(
    {
        vol.Required("name"): "well",
        vol.Required("well_x"): vol.Coerce(int),
        vol.Required("well_y"): vol.Coerce(int),
        "values": vol.Schema({"well_img_ok": vol.Coerce(bool)}, extra=vol.ALLOW_EXTRA),
    }
)

SET_FIELD_SCHEMA = SET_WELL_SCHEMA.extend(
    {
        vol.Required("name"): "field",
        vol.Required("field_x"): vol.Coerce(int),
        vol.Required("field_y"): vol.Coerce(int),
        "values": vol.Schema({"field_img_ok": vol.Coerce(bool)}, extra=vol.ALLOW_EXTRA),
    }
)

SET_CHANNEL_SCHEMA = SET_WELL_SCHEMA.extend(
    {
        vol.Required("name"): "channel",
        vol.Required("channel_id"): vol.Coerce(int),
        "values": vol.Schema({"gain": vol.Coerce(float)}, extra=vol.ALLOW_EXTRA),
    }
)

SET_Z_SLICE_SCHEMA = SET_WELL_SCHEMA.extend(
    {vol.Required("name"): "z_slice", vol.Required("z_slice_id"): vol.Coerce(int)}
)

SET_IMAGE_SCHEMA = SET_FIELD_SCHEMA.extend(
    {
        vol.Required("name"): "image",
        vol.Required("path"): vol.Coerce(str),
        vol.Required("channel_id"): vol.Coerce(int),
        vol.Required("z_slice_id"): vol.Coerce(int),
    }
)

SET_SAMPLE_SCHEMA = vol.Any(
    SET_PLATE_SCHEMA,
    SET_WELL_SCHEMA,
    SET_FIELD_SCHEMA,
    SET_Z_SLICE_SCHEMA,
    SET_CHANNEL_SCHEMA,
    SET_IMAGE_SCHEMA,
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
    values : dict
        Optional dict of values.
    """

    def __init__(self, images=None, values=None):
        """Set up instance."""
        self._images = images or {}
        self._values = values or {}

    def __repr__(self):
        """Return the representation."""
        return f"LeicaSample(images={self._images}, values={self._values})"

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
        """:str: Return the name of the sample."""
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
        await self.set_sample(
            "image",
            path=event.path,
            plate_name=event.plate_name,
            well_x=event.well_x,
            well_y=event.well_y,
            field_x=event.field_x,
            field_y=event.field_y,
            z_slice_id=event.z_slice_id,
            channel_id=event.channel_id,
        )

    async def _set_sample(self, name, values, **kwargs):
        """Set an image container of the sample."""
        sample = None

        if name == "image":
            params = SET_FIELD_SCHEMA({"name": "field", **kwargs})
            await self.set_sample(**params)
            params = SET_Z_SLICE_SCHEMA({"name": "z_slice", **kwargs})
            await self.set_sample(**params)
            params = SET_CHANNEL_SCHEMA({"name": "channel", **kwargs})
            await self.set_sample(**params)

            sample = Image(values=values, **kwargs)

        if name == "field":
            params = SET_PLATE_SCHEMA({"name": "plate", **kwargs})
            await self.set_sample(**params)
            params = SET_WELL_SCHEMA({"name": "well", **kwargs})
            await self.set_sample(**params)

            sample = Field(self._images, values=values, **kwargs)

        if name == "channel":
            params = SET_PLATE_SCHEMA({"name": "plate", **kwargs})
            await self.set_sample(**params)
            params = SET_WELL_SCHEMA({"name": "well", **kwargs})
            await self.set_sample(**params)

            sample = Channel(self._images, values=values, **kwargs)

        if name == "z_slice":
            params = SET_PLATE_SCHEMA({"name": "plate", **kwargs})
            await self.set_sample(**params)
            params = SET_WELL_SCHEMA({"name": "well", **kwargs})
            await self.set_sample(**params)

            sample = ZSlice(self._images, values=values, **kwargs)

        if name == "well":
            params = SET_PLATE_SCHEMA({"name": "plate", **kwargs})
            await self.set_sample(**params)

            sample = Well(self._images, values=values, **kwargs)

        if name == "plate":
            sample = Plate(self._images, values=values, **kwargs)

        return sample


class Plate(ImageContainer):
    """A container for wells.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    plate_name: str
        The name of the plate.
    values : dict
        Optional dict of values.

    Attributes
    ----------
    plate_name: str
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
            f"Plate(images={self._images}, plate_name={self.plate_name}, "
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
    def name(self):
        """:str: Return an identifying name for the container."""
        return "plate"

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
    plate_name: str
        The name of the plate.
    values : dict
        Optional dict of values.

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
    def name(self):
        """:str: Return an identifying name for the container."""
        return "well"

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
    well_x : int
        x coordinate of the well, minimum 0.
    well_y : int
        y coordinate of the well, minimum 0.
    plate_name: str
        The name of the plate.
    values : dict
        Optional dict of values.

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
    def name(self):
        """:str: Return an identifying name for the container."""
        return "field"

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
    well_x : int
        x coordinate of the well, minimum 0.
    well_y : int
        y coordinate of the well, minimum 0.
    plate_name: str
        The name of the plate.
    values : dict
        Optional dict of values.

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
    def name(self):
        """:str: Return an identifying name for the container."""
        return "channel"

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
    z_slice_id : int
        ID of the slice.
    well_x : int
        x coordinate of the well, minimum 0.
    well_y : int
        y coordinate of the well, minimum 0.
    plate_name: str
        The name of the plate.
    values : dict
        Optional dict of values.

    Attributes
    ----------
    z_slice_id : int
        Return z_slice_id of the channel.
    """

    def __init__(self, images, z_slice_id, **kwargs):
        """Set up instance."""
        self._images = images
        self.z_slice_id = z_slice_id
        self._values = kwargs.pop("values", {})
        super().__init__(images, **kwargs)

    def __repr__(self):
        """Return the representation."""
        return (
            f"ZSlice(images={self._images}, z_slice_id={self.z_slice_id}, "
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
            and image.z_slice_id == self.z_slice_id
        }

    @property
    def name(self):
        """:str: Return an identifying name for the container."""
        return "z_slice"

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values


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
    def z_slice_id(self):
        """:int: Return the z_slice id of the event."""
        return self.container.z_slice_id


def next_well_xy(sample, plate_name, x_wells=None, y_wells=None):
    """Return the next not done well for the given plate x, y format."""
    if json.dumps({"name": "plate", "plate_name": plate_name}) not in sample.data:
        return None, None
    if x_wells is None or y_wells is None:
        not_done = (
            (cont.well_x, cont.well_y)
            for cont in sample.data.values()
            if cont.name == "well"
            and cont.plate_name == plate_name
            and not cont.values.get("well_img_ok", False)
        )
    else:
        done = {
            (cont.well_x, cont.well_y)
            for cont in sample.data.values()
            if cont.name == "well"
            and cont.plate_name == plate_name
            and cont.values.get("well_img_ok", False)
        }
        not_done = (
            (x_well, y_well)
            for x_well in range(x_wells)
            for y_well in range(y_wells)
            if (x_well, y_well) not in done
        )

    x_well, y_well = next(not_done, (None, None))
    return x_well, y_well
