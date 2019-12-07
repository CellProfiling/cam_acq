"""Handle sample state."""
# pylint: disable=too-many-lines
import logging
from collections import OrderedDict

import voluptuous as vol

from camacq.const import (
    CHANNEL_EVENT,
    FIELD_EVENT,
    FIELD_NAME,
    IMAGE_EVENT,
    IMAGE_REMOVED_EVENT,
    PLATE_EVENT,
    SAMPLE_EVENT,
    SAMPLE_IMAGE_EVENT,
    WELL_EVENT,
    WELL_NAME,
)
from camacq.event import Event
from camacq.helper import BASE_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)

ACTION_SET_WELL = "set_well"
ACTION_SET_PLATE = "set_plate"
ACTION_SET_FIELD = "set_field"
ACTION_SET_CHANNEL = "set_channel"

SET_PLATE_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend(
    {vol.Required("plate_name"): vol.Coerce(str)}
)

SET_WELL_ACTION_SCHEMA = SET_PLATE_ACTION_SCHEMA.extend(
    {vol.Required("well_x"): vol.Coerce(int), vol.Required("well_y"): vol.Coerce(int)}
)

SET_FIELD_ACTION_SCHEMA = SET_WELL_ACTION_SCHEMA.extend(
    {
        vol.Required("field_x"): vol.Coerce(int),
        vol.Required("field_y"): vol.Coerce(int),
        "dxpx": vol.Coerce(int),
        "dypx": vol.Coerce(int),
        # pylint: disable=no-value-for-parameter
        vol.Optional("img_ok", default=False): vol.Boolean(),
    }
)

SET_CHANNEL_ACTION_SCHEMA = SET_WELL_ACTION_SCHEMA.extend(
    {vol.Required("channel_name"): vol.Coerce(str), "gain": vol.Coerce(int)}
)

ACTION_TO_METHOD = {
    ACTION_SET_PLATE: {"method": ACTION_SET_PLATE, "schema": SET_PLATE_ACTION_SCHEMA},
    ACTION_SET_WELL: {"method": ACTION_SET_WELL, "schema": SET_WELL_ACTION_SCHEMA},
    ACTION_SET_FIELD: {"method": ACTION_SET_FIELD, "schema": SET_FIELD_ACTION_SCHEMA},
    ACTION_SET_CHANNEL: {
        "method": ACTION_SET_CHANNEL,
        "schema": SET_CHANNEL_ACTION_SCHEMA,
    },
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
        await getattr(center.sample, method)(**kwargs)

    for action_id, options in ACTION_TO_METHOD.items():
        schema = options["schema"]
        center.actions.register("sample", action_id, handle_action, schema)


class Image:
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
    path : str
        The path to the image.
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

    __slots__ = (
        "path",
        "z_slice",
        "channel_id",
        "field_x",
        "field_y",
        "well_x",
        "well_y",
        "plate_name",
    )

    def __init__(
        self,
        path=None,
        channel_id=None,
        z_slice=None,
        field_x=None,
        field_y=None,
        well_x=None,
        well_y=None,
        plate_name=None,
    ):
        """Set up instance."""
        self.path = path
        self.channel_id = channel_id
        self.z_slice = z_slice
        self.field_x = field_x
        self.field_y = field_y
        self.well_x = well_x
        self.well_y = well_y
        self.plate_name = plate_name

    def __repr__(self):
        """Return the representation."""
        return "<Image(path={0!r})>".format(self.path)


class Channel:
    """A channel with attributes.

    Parameters
    ----------
    channel_name : str
        Name of the channel.
    values : Optional dict of values.

    Attributes
    ----------
    name : str
        Return name of the channel.
    """

    # pylint: disable=too-few-public-methods

    __slots__ = ("name", "_gain")

    def __init__(self, channel_name, **values):
        """Set up instance."""
        self.name = channel_name
        self._gain = None
        for attr, val in values.items():
            setattr(self, attr, val)

    def __repr__(self):
        """Return the representation."""
        return "<Channel {}: gain: {}>".format(self.name, self._gain)

    @property
    def gain(self):
        """:int: Return gain value.

        :setter: Set the gain value and convert to int.
        """
        return self._gain

    @gain.setter
    def gain(self, value):
        """Set gain."""
        try:
            self._gain = int(value)
        except TypeError:
            _LOGGER.warning(
                "Invalid gain value %s, falling back to %s", value, self._gain
            )


class Field:
    """A field within a well.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    x : int
        Coordinate of field in x.
    y : int
        Coordinate of field in y.
    dx : int
        Pixel coordinate of region of interest within image field in X.
    dy : int
        Pixel coordinate of region of interest within image field in Y.
    img_ok : bool
        True if field has acquired an ok image.
    """

    __slots__ = ("_images", "x", "y", "dx", "dy", "img_ok")

    def __init__(self, images, x, y, dx, dy, img_ok):
        """Set up instance."""
        # pylint: disable=invalid-name, too-many-arguments
        self._images = images
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.img_ok = img_ok

    def __repr__(self):
        """Return the representation."""
        return "<Field {}: img_ok: {}>".format(self.name, self.img_ok)

    @property
    def images(self):
        """:dict: Return a dict with all images for the field."""
        return {
            image.path: image
            for image in list(self._images.values())
            if image.field_x == self.x and image.field_y == self.y
        }

    @property
    def name(self):
        """:str: Return a string representing the name of the field."""
        return FIELD_NAME.format(int(self.x), int(self.y))


class Well:
    """A well within a plate with fields and channels.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    x : int
        x coordinate of the well, minimum 0.
    y : int
        y coordinate of the well, minimum 0.

    Attributes
    ----------
    x : int
        Number showing the x coordinate of the well, from 0.
    y : int
        Number showing the y coordinate of the well, from 0.
    """

    __slots__ = ("_images", "x", "y", "_channels", "_fields")

    def __init__(self, images, x, y):
        """Set up instance."""
        # pylint: disable=invalid-name
        self._images = images
        self.x = int(x)
        self.y = int(y)
        self._fields = OrderedDict()
        self._channels = {}

    def __repr__(self):
        """Return the representation."""
        return "<Well {}: channels: {}: fields: {}>".format(
            self.name, self.channels, self.fields
        )

    @property
    def channels(self):
        """:dict: Return a dict of Channel instances."""
        return self._channels

    @property
    def fields(self):  # noqa D301, D207
        """:OrderedDict: Return a dict of Field instances.

        Example
        -------
        ::

            >>> well = Well(bus, sample, 0, 0)
            >>> well.set_field(1, 3, 0, 1, True, False)
            >>> well.fields
            {(1, 3): Field(x=1, y=3, dx=0, dy=1, img_ok=False)}
        """
        return self._fields

    @property
    def images(self):
        """:dict: Return a dict with all images for the well."""
        return {
            image.path: image
            for image in list(self._images.values())
            if image.well_x == self.x and image.well_y == self.y
        }

    @property
    def img_ok(self):
        """:bool: Return True if all fields are imaged ok."""
        if self.fields and all(field.img_ok for field in list(self.fields.values())):
            return True
        return False

    @property
    def name(self):
        """:str: Return a string representing the name of the well."""
        return WELL_NAME.format(int(self.x), int(self.y))

    def set_channel(self, well_x, well_y, channel_name, **values):
        """Set values of a channel in a well.

        Create a Well instance if well not already exists.

        Parameters
        ----------
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        channel_name : str
            The name of the channel where to set attribute value.
        values : dict
            The attributes and values to set.

        Returns
        -------
        Channel instance
            Return the Channel instance.
        """
        if channel_name not in self._channels:
            self._channels[channel_name] = Channel(channel_name)
        channel = self.channels[channel_name]
        for attribute, value in values.items():
            setattr(channel, attribute, value)
        return channel

    def set_field(self, xcoord, ycoord, dxpx=0, dypx=0, img_ok=False):
        """Set a field in the well.

        Parameters
        ----------
        xcoord : int
            Coordinate of field in x.
        ycoord : int
            Coordinate of field in y.
        dxpx : int
            Pixel x coordinate of region of interest within image.
        dypx : int
            Pixel y coordinate of region of interest within image.
        img_ok : bool
            True if field has acquired an ok image.

        Returns
        -------
        Field instance
            Return the Field instance.
        """
        # pylint: disable=too-many-arguments
        field = Field(self._images, xcoord, ycoord, dxpx, dypx, img_ok)
        self._fields[(xcoord, ycoord)] = field
        return field


class Plate:
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

    def __init__(self, images, name):
        """Set up instance."""
        self._images = images
        self.name = name
        self._wells = {}

    def __repr__(self):
        """Return the representation."""
        return "<Plate {}: wells: {}>".format(self.name, self._wells)

    @property
    def images(self):
        """:dict: Return a dict with all images for the plate."""
        return {
            image.path: image
            for image in list(self._images.values())
            if image.plate_name == self.name
        }

    @property
    def wells(self):
        """:dict: Return all the wells of the plate."""
        return self._wells

    def set_well(self, well_x, well_y):
        """Create a Well instance with well_name stored in wells.

        Parameters
        ----------
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.

        Returns
        -------
        Well instance
            Return the Well instance.
        """
        well = Well(self._images, well_x, well_y)
        self._wells[(well_x, well_y)] = well
        return well


class Sample:
    """Representation of the state of the sample.

    The sample can have plates, wells, fields, channels and images.

    Parameters
    ----------
    bus : EventBus instance
        The EventBus instance.
    """

    def __init__(self, bus):
        """Set up instance."""
        self._bus = bus
        self._plates = {}
        self._images = {}
        bus.register(IMAGE_EVENT, self._set_image_on_event)

    def __repr__(self):
        """Return the representation."""
        return "<Sample: plates: {}>".format(self._plates)

    @property
    def images(self):
        """:dict: Return all the images of the sample."""
        return self._images

    @property
    def plates(self):
        """:dict: Return all the plates of the sample."""
        return self._plates

    async def _set_image_on_event(self, center, event):
        """Set sample image on an image event from a microscope API."""
        await self.set_image(
            event.path,
            channel_id=event.channel_id,
            z_slice=event.z_slice,
            field_x=event.field_x,
            field_y=event.field_y,
            well_x=event.well_x,
            well_y=event.well_y,
            plate_name=event.plate_name,
        )

    def get_plate(self, plate_name):
        """Get plate via plate_name.

        Parameters
        ----------
        plate_name : str
            The name of the plate.

        Returns
        -------
        Plate instance
            Return a Plate instance. If no plate is found, return None.
        """
        plate = self._plates.get(plate_name)
        return plate

    async def set_plate(self, plate_name):
        """Create a plate with name for the sample.

        Parameters
        ----------
        plate_name : str
            The name of the plate.

        Returns
        -------
        Plate instance
            Return the Plate instance.
        """
        plate = Plate(self._images, plate_name)
        self._plates[plate.name] = plate
        await self._bus.notify(PlateEvent({"sample": self, "plate": plate}))
        return plate

    def get_well(self, plate_name, well_x, well_y):
        """Get well from plate.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should return the well.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.

        Returns
        -------
        Well instance
            Return a Well instance. If no well is found, return None.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            return None
        well = plate.wells.get((well_x, well_y))
        return well

    async def set_well(self, plate_name, well_x, well_y):
        """Set a well on a plate.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should hold the well.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.

        Returns
        -------
        Well instance
            Return the Well instance.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            plate = await self.set_plate(plate_name)
        well = plate.set_well(well_x, well_y)
        event = WellEvent({"sample": self, "plate": plate, "well": well})
        await self._bus.notify(event)
        return well

    def get_channel(self, plate_name, well_x, well_y, channel_name):
        """Get channel from a well on a plate.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should return the well.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        channel_name : str
            The channel name.

        Returns
        -------
        Channel instance
            Return a Channel instance. If no channel is found, return None.
        """
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            return None
        channel = well.channels.get(channel_name)
        return channel

    async def set_channel(self, plate_name, well_x, well_y, channel_name, **values):
        """Set attribute value in a channel in a well of a plate.

        Create a Well instance if well not already exists. Pick the
        first plate if no plate is specified.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should hold the well with the
            channel.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        channel_name : str
            The name of the channel where to set attribute value.
        values : dict
            The attributes and values of the channel to set.

        Returns
        -------
        Channel instance
            Return the Channel instance.
        """
        # pylint: disable=too-many-arguments
        plate = self.get_plate(plate_name)
        if not plate:
            plate = await self.set_plate(plate_name)
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            well = await self.set_well(plate_name, well_x, well_y)
        channel = well.set_channel(well_x, well_y, channel_name, **values)
        event = ChannelEvent(
            {"sample": self, "plate": plate, "well": well, "channel": channel}
        )
        await self._bus.notify(event)
        return channel

    def get_field(self, plate_name, well_x, well_y, field_x, field_y):
        """Get field from a well on a plate.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should return the field.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        field_x : int
            Coordinate of field in x.
        field_y : int
            Coordinate of field in y.

        Returns
        -------
        Field instance
            Return a Field instance. If no field, well or plate is
            found, return None.
        """
        # pylint: disable=too-many-arguments
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            return None
        field = well.fields.get((field_x, field_y))
        return field

    async def set_field(
        self, plate_name, well_x, well_y, field_x, field_y, dxpx=0, dypx=0, img_ok=False
    ):
        """Set a field in a well of a plate.

        Pick the first plate if no plate is specified.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should hold the field.
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        field_x : int
            Coordinate of field in x.
        field_y : int
            Coordinate of field in y.
        dxpx : int
            Pixel x coordinate of region of interest within image.
        dypx : int
            Pixel y coordinate of region of interest within image.
        img_ok : bool
            True if field has acquired an ok image.

        Returns
        -------
        Field instance
            Return the Field instance.
        """
        # pylint: disable=too-many-arguments
        plate = self.get_plate(plate_name)
        if not plate:
            plate = await self.set_plate(plate_name)
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            well = await self.set_well(plate_name, well_x, well_y)
        field = well.set_field(field_x, field_y, dxpx, dypx, img_ok)
        event = FieldEvent(
            {"sample": self, "plate": plate, "well": well, "field": field}
        )
        await self._bus.notify(event)
        return field

    def get_image(self, path):
        """Get image instance via path to image.

        Parameters
        ----------
        path : str
            The path to the image.

        Returns
        -------
        Image instance
            Return an Image instance. If no image is found, return
            None.
        """
        return self._images.get(path)

    async def set_image(
        self,
        path,
        channel_id=None,
        z_slice=None,
        field_x=None,
        field_y=None,
        well_x=None,
        well_y=None,
        plate_name=None,
    ):
        """Add an image to the sample.

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
            The name of the plate of the image.

        Returns
        -------
        Image instance
            Return the Image instance.
        """
        # pylint: disable=too-many-arguments, too-many-locals
        image = Image(
            path, channel_id, z_slice, field_x, field_y, well_x, well_y, plate_name
        )
        self._images[image.path] = image

        await self._bus.notify(SampleImageEvent({"image": image}))

        if all(
            name is not None for name in (plate_name, well_x, well_y, field_x, field_y)
        ):
            field = self.get_field(plate_name, well_x, well_y, field_x, field_y)
            if not field:
                await self.set_field(
                    plate_name,
                    well_x,
                    well_y,
                    field_x,
                    field_y,
                    dxpx=0,
                    dypx=0,
                    img_ok=False,
                )
            return image

        if all(name is not None for name in (plate_name, well_x, well_y)):
            well = self.get_well(plate_name, well_x, well_y)
            if not well:
                well = await self.set_well(plate_name, well_x, well_y)
            return image

        if plate_name is None:
            return image
        plate = self.get_plate(plate_name)
        if not plate:
            plate = await self.set_plate(plate_name)
        return image

    async def remove_image(self, path):
        """Remove an image from the sample.

        Parameters
        ----------
        path : str
            The path to the image that should be removed.

        Returns
        -------
        Image instance
            Return the Image instance that was removed.
        """
        image = self._images.pop(path, None)
        if image is not None:
            await self._bus.notify(ImageRemovedEvent({"image": image}))
        return image


# pylint: disable=too-few-public-methods
class SampleEvent(Event):
    """An event produced by a sample change event."""

    __slots__ = ()

    event_type = SAMPLE_EVENT

    @property
    def sample(self):
        """:Sample instance: Return the sample instance of the event."""
        return self.data.get("sample")

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.sample)


class PlateEvent(SampleEvent):
    """An event produced by a sample plate change event."""

    __slots__ = ()

    event_type = PLATE_EVENT

    @property
    def plate(self):
        """:Plate instance: Return the plate instance of the event."""
        return self.data.get("plate")

    @property
    def plate_name(self):
        """:str: Return the name of the plate."""
        return self.plate.name

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.plate)


class WellEvent(PlateEvent):
    """An event produced by a sample well change event."""

    __slots__ = ()

    event_type = WELL_EVENT

    @property
    def well(self):
        """:Well instance: Return the well of the event."""
        return self.data.get("well")

    @property
    def well_x(self):
        """:int: Return the well x coordinate of the event."""
        return self.well.x

    @property
    def well_y(self):
        """:int: Return the well y coordinate of the event."""
        return self.well.y

    @property
    def well_img_ok(self):
        """:bool: Return if the well has all images acquired ok."""
        return self.well.img_ok

    @property
    def well_name(self):
        """:str: Return the name of the well."""
        return self.well.name

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.well)


class ChannelEvent(WellEvent):
    """An event produced by a sample channel change event."""

    __slots__ = ()

    event_type = CHANNEL_EVENT

    @property
    def channel(self):
        """:Channel instance: Return the channel of the event."""
        return self.data.get("channel")

    @property
    def channel_name(self):
        """:str: Return the channel name of the event."""
        return self.channel.name

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.channel)


class FieldEvent(WellEvent):
    """An event produced by a sample field change event."""

    __slots__ = ()

    event_type = FIELD_EVENT

    @property
    def field(self):
        """:Field instance: Return the field of the event."""
        return self.data.get("field")

    @property
    def field_x(self):
        """:int: Return the field x coordinate of the event."""
        return self.field.x

    @property
    def field_y(self):
        """:int: Return the field y coordinate of the event."""
        return self.field.y

    @property
    def field_dx(self):
        """:int: Return the field dx pixel coordinate of an ROI."""
        return self.field.dx

    @property
    def field_dy(self):
        """:int: Return the field dy pixel coordinate of an ROI."""
        return self.field.dy

    @property
    def field_img_ok(self):
        """:bool: Return if the field has all images acquired ok."""
        return self.field.img_ok

    @property
    def field_name(self):
        """:str: Return the name of the field."""
        return self.field.name

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.field)


class SampleImageEvent(Event):
    """An event produced by a sample image event."""

    __slots__ = ()

    event_type = SAMPLE_IMAGE_EVENT

    @property
    def image(self):
        """:Image instance: Return the image instance of the event."""
        return self.data.get("image")

    @property
    def path(self):
        """:str: Return the absolute path to the image."""
        return self.image.path

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.image.well_x

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.image.well_y

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.image.field_x

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.image.field_y

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return self.image.channel_id

    @property
    def z_slice(self):
        """:int: Return z index of the image."""
        return self.image.z_slice

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.image)


class ImageRemovedEvent(SampleImageEvent):
    """An event produced by a sample image removed event."""

    __slots__ = ()

    event_type = IMAGE_REMOVED_EVENT
