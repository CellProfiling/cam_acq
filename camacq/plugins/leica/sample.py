"""Provide sample implementation for leica microscope."""
# pylint: disable=too-many-lines
import logging

import voluptuous as vol

from camacq.const import (
    CHANNEL_EVENT,
    FIELD_EVENT,
    IMAGE_EVENT,
    PLATE_EVENT,
    SAMPLE_EVENT,
    WELL_EVENT,
)
from camacq.event import Event
from camacq.plugins.sample import Image, ImageContainer, Sample, register_sample

_LOGGER = logging.getLogger(__name__)

SET_PLATE_SCHEMA = vol.Schema({vol.Required("plate_name"): vol.Coerce(str)})

SET_WELL_SCHEMA = SET_PLATE_SCHEMA.extend(
    {vol.Required("well_x"): vol.Coerce(int), vol.Required("well_y"): vol.Coerce(int)}
)

SET_FIELD_SCHEMA = SET_WELL_SCHEMA.extend(
    {
        vol.Required("field_x"): vol.Coerce(int),
        vol.Required("field_y"): vol.Coerce(int),
        "dxpx": vol.Coerce(int),
        "dypx": vol.Coerce(int),
        # pylint: disable=no-value-for-parameter
        vol.Optional("img_ok", default=False): vol.Boolean(),
    }
)

SET_CHANNEL_SCHEMA = SET_WELL_SCHEMA.extend(
    {
        vol.Required("channel_name"): vol.Coerce(str),
        "channel_id": vol.Coerce(int),
        "gain": vol.Coerce(int),
    }
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
    plates : dict
        A dict of plates of the sample.

    Attributes
    ----------
    images : dict
        Return a dict of Image instances.
    plates : dict
        Return a dict of Plate instances.
    """

    def __init__(self, images=None, plates=None):
        """Set up instance."""
        self._images = images or {}
        self.plates = plates or {}

    def __repr__(self):
        """Return the representation."""
        return f"Sample(images={self._images}, plates={self.plates})"

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change."""
        return SampleEvent({"sample": self})

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

    async def on_image(self, center, event):
        """Handle image event for this sample."""
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

    def _set_sample(self, **values):
        """Set an image container of the sample."""
        plate_name = values.pop("plate_name", None)
        well_x = values.pop("well_x", None)
        well_y = values.pop("well_y", None)
        field_x = values.pop("field_x", None)
        field_y = values.pop("field_y", None)
        channel_name = values.pop("channel_name", None)
        dxpx = values.pop("dxpx", 0)
        dypx = values.pop("dypx", 0)
        img_ok = values.pop("img_ok", False)

        if all(
            name is not None for name in (plate_name, well_x, well_y, field_x, field_y)
        ):
            field = self.set_field(
                plate_name,
                well_x,
                well_y,
                field_x,
                field_y,
                dxpx=dxpx,
                dypx=dypx,
                img_ok=img_ok,
            )
            return field

        if all(name is not None for name in (plate_name, well_x, well_y, channel_name)):
            channel = self.set_channel(
                plate_name, well_x, well_y, channel_name, **values
            )
            return channel

        if all(name is not None for name in (plate_name, well_x, well_y)):
            well = self.set_well(plate_name, well_x, well_y)
            return well

        if plate_name is None:
            return None
        plate = self.set_plate(plate_name)
        return plate

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
        plate = self.plates.get(plate_name)
        return plate

    def set_plate(self, plate_name):
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
        event = PlateEvent({"sample": self, "plate": plate})
        plate.change_event = event
        self.plates[plate.name] = plate
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

    def set_well(self, plate_name, well_x, well_y):
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
            plate = self.set_plate(plate_name)
        well = plate.set_well(well_x, well_y)
        event = WellEvent({"sample": self, "plate": plate, "well": well})
        well.change_event = event
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

    def set_channel(self, plate_name, well_x, well_y, channel_name, **values):
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
            plate = self.set_plate(plate_name)
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            well = self.set_well(plate_name, well_x, well_y)
        channel = well.set_channel(channel_name, **values)
        event = ChannelEvent(
            {"sample": self, "plate": plate, "well": well, "channel": channel}
        )
        channel.change_event = event
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

    def set_field(
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
            plate = self.set_plate(plate_name)
        well = self.get_well(plate_name, well_x, well_y)
        if not well:
            well = self.set_well(plate_name, well_x, well_y)
        field = well.set_field(field_x, field_y, dxpx, dypx, img_ok)
        event = FieldEvent(
            {"sample": self, "plate": plate, "well": well, "field": field}
        )
        field.change_event = event
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
        self, path, channel_id, z_slice, field_x, field_y, well_x, well_y, plate_name,
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
        image = LeicaImage(
            path, channel_id, z_slice, field_x, field_y, well_x, well_y, plate_name
        )
        self._images[image.path] = image

        await self.set_sample(
            plate_name=plate_name,
            well_x=well_x,
            well_y=well_y,
            field_x=field_x,
            field_y=field_y,
            dxpx=0,
            dypx=0,
            img_ok=False,
        )
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
        return image


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
    wells : dict
        Return a dict of Well instances.
    """

    def __init__(self, images, name, wells=None):
        """Set up instance."""
        self._event = None
        self._images = images
        self.name = name
        self.wells = wells or {}

    def __repr__(self):
        """Return the representation."""
        return f"Plate(images={self._images}, name={self.name}, wells={self.wells})"

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change.

        :setter: Set the change event.
        """
        return self._event

    @change_event.setter
    def change_event(self, event):
        """Set the change event."""
        self._event = event

    @property
    def images(self):
        """:dict: Return a dict with all images for the plate."""
        return {
            image.path: image
            for image in self._images.values()
            if image.plate_name == self.name
        }

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
        self.wells[(well_x, well_y)] = well
        return well


class Well(ImageContainer):
    """A well within a plate with fields and channels.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    x : int
        x coordinate of the well, minimum 0.
    y : int
        y coordinate of the well, minimum 0.
    channels : dict
        A dict of Channel instances.
    fields : dict
        A dict of Field instances.

    Attributes
    ----------
    x : int
        Number showing the x coordinate of the well, from 0.
    y : int
        Number showing the y coordinate of the well, from 0.
    channels : dict
        Return a dict of Channel instances.
    fields : dict
        Return a dict of Field instances.
    """

    def __init__(self, images, x, y, channels=None, fields=None):
        """Set up instance."""
        # pylint: disable=invalid-name, too-many-arguments
        self._event = None
        self._images = images
        self.x = int(x)
        self.y = int(y)
        self.channels = channels or {}
        self.fields = fields or {}

    def __repr__(self):
        """Return the representation."""
        return (
            f"Well(images={self._images}, x={self.x}, y={self.y}, "
            f"channels={self.channels}, fields={self.fields})"
        )

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change.

        :setter: Set the change event.
        """
        return self._event

    @change_event.setter
    def change_event(self, event):
        """Set the change event."""
        self._event = event

    @property
    def images(self):
        """:dict: Return a dict with all images for the well."""
        return {
            image.path: image
            for image in self._images.values()
            if image.well_x == self.x and image.well_y == self.y
        }

    @property
    def img_ok(self):
        """:bool: Return True if all fields are imaged ok."""
        if self.fields and all(field.img_ok for field in self.fields.values()):
            return True
        return False

    def set_channel(self, channel_name, channel_id=None, **values):
        """Set values of a channel in a well.

        Create a Well instance if well not already exists.

        Parameters
        ----------
        channel_name : str
            The name of the channel where to set attribute value.
        channel_id : str
            The id of the channel where to set attribute value.
        values : dict
            The attributes and values to set.

        Returns
        -------
        Channel instance
            Return the Channel instance.
        """
        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(
                self._images, self.x, self.y, channel_name, channel_id
            )
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
        self.fields[(xcoord, ycoord)] = field
        return field


class Field(ImageContainer):
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

    def __init__(self, images, x, y, dx, dy, img_ok):
        """Set up instance."""
        # pylint: disable=invalid-name, too-many-arguments
        self._event = None
        self._images = images
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.img_ok = img_ok

    def __repr__(self):
        """Return the representation."""
        return (
            f"Field(images={self._images}, x={self.x}, y={self.y}, "
            f"dx={self.dx}, dy={self.dy}, img_ok={self.img_ok})"
        )

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change.

        :setter: Set the change event.
        """
        return self._event

    @change_event.setter
    def change_event(self, event):
        """Set the change event."""
        self._event = event

    @property
    def images(self):
        """:dict: Return a dict with all images for the field."""
        return {
            image.path: image
            for image in self._images.values()
            if image.field_x == self.x and image.field_y == self.y
        }


class Channel(ImageContainer):
    """A channel with attributes.

    Parameters
    ----------
    images : dict
        All the images of the sample.
    x : int
        x coordinate of the well of the channel, minimum 0.
    y : int
        y coordinate of the well of the channel, minimum 0.
    channel_name : str
        Name of the channel.
    channel_id : int
        ID of the channel.
    values : Optional dict of values.

    Attributes
    ----------
    name : str
        Return name of the channel.
    """

    def __init__(self, images, x, y, channel_name, channel_id, **values):
        """Set up instance."""
        # pylint: disable=invalid-name, too-many-arguments
        self._images = images
        self.x = x
        self.y = y
        self._event = None
        self.name = channel_name
        self.id = channel_id
        self._gain = None
        for attr, val in values.items():
            setattr(self, attr, val)

    def __repr__(self):
        """Return the representation."""
        return (
            f"Channel(images={self._images}, x={self.x}, y={self.y}, "
            f"channel_name={self.name}, channel_id={self.id}, gain={self.gain})"
        )

    @property
    def change_event(self):
        """:Event: Return an event that should be fired on container change.

        :setter: Set the change event.
        """
        return self._event

    @change_event.setter
    def change_event(self, event):
        """Set the change event."""
        self._event = event

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

    @property
    def images(self):
        """:dict: Return a dict with all images for the channel."""
        return {
            image.path: image
            for image in self._images.values()
            if image.well_x == self.x
            and image.well_y == self.y
            and image.channel_id == self.id
        }


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
        data = dict(sample=self.sample)
        return f"{type(self).__name__}({data})"


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
        data = dict(sample=self.sample, plate=self.plate)
        return f"{type(self).__name__}({data})"


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

    def __repr__(self):
        """Return the representation."""
        data = dict(sample=self.sample, plate=self.plate, well=self.well)
        return f"{type(self).__name__}({data})"


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
        data = dict(
            sample=self.sample, plate=self.plate, well=self.well, channel=self.channel
        )
        return f"{type(self).__name__}({data})"


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

    def __repr__(self):
        """Return the representation."""
        data = dict(
            sample=self.sample, plate=self.plate, well=self.well, field=self.field
        )
        return f"{type(self).__name__}({data})"
