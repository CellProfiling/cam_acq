"""Handle gain."""
import logging
from builtins import next, object  # pylint: disable=redefined-builtin
from collections import OrderedDict

from camacq.api import ImageEvent
from camacq.const import FIELD_NAME, WELL_NAME
from camacq.event import (ChannelEvent, FieldEvent, ImageRemovedEvent,
                          PlateEvent, WellEvent)
from camacq.image import Image

_LOGGER = logging.getLogger(__name__)


def setup_module(center, config):
    """Set up sample module."""
    _LOGGER.info('Setting up sample')


class Channel(object):
    """A channel with gain.

    Parameters
    ----------
    channel_name : str
        Name of the channel.
    gain : int
        Gain value.

    Attributes
    ----------
    name : str
        Return name of the channel.
    """

    # pylint: disable=too-few-public-methods

    __slots__ = ('name', '_gain', )

    def __init__(self, channel_name, gain):
        """Set up instance."""
        self.name = channel_name
        self._gain = gain

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
        self._gain = int(value)


class Field(object):
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
    gain_field : bool
        True if field should run gain selection analysis.
    img_ok : bool
        True if field has acquired an ok image.
    """

    __slots__ = ('_images', 'x', 'y', 'dx', 'dy', 'gain_field', 'img_ok')

    def __init__(self, images, x, y, dx, dy, gain_field, img_ok):
        """Set up instance."""
        # pylint: disable=invalid-name, too-many-arguments
        self._images = images
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.gain_field = gain_field
        self.img_ok = img_ok

    def __repr__(self):
        """Return the representation."""
        return "<Field {}: img_ok: {}>".format(self.name, self.img_ok)

    @property
    def images(self):
        """:dict: Return a dict with all images for the field."""
        return {
            image.path: image for image in list(self._images.values())
            if image.field_x == self.x and image.field_y == self.y
        }

    @property
    def name(self):
        """:str: Return a string representing the name of the field."""
        return FIELD_NAME.format(int(self.x), int(self.y))


class Well(object):
    """A well within a plate with fields and gain.

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
    channels : dict
        Dict where the keys are color channels and the values are Gain
        instances.
    """

    __slots__ = ('_images', 'x', 'y', '_fields', 'channels')

    def __init__(self, images, x, y):
        """Set up instance."""
        # pylint: disable=invalid-name
        self._images = images
        self.x = x
        self.y = y
        self._fields = OrderedDict()
        self.channels = {}

    def __repr__(self):
        """Return the representation."""
        return "<Well {}>".format(self.name)

    @property
    def fields(self):  # noqa D301, D207
        """:OrderedDict: Return a dict of Field instances.

        Example
        -------
        ::

            >>> well = Well(bus, sample, 0, 0)
            >>> well.set_field(1, 3, 0, 1, True, False)
            >>> well.fields
            {'X01--Y03': Field(x=1, y=3, dx=0, dy=1, \
gain_field=True, img_ok=False)}
        """
        return self._fields

    @property
    def images(self):
        """:dict: Return a dict with all images for the well."""
        return {
            image.path: image for image in list(self._images.values())
            if image.well_x == self.x and image.well_y == self.y
        }

    @property
    def img_ok(self):
        """:bool: Return True if all fields are imaged ok."""
        if self.fields and all(
                field.img_ok for field in list(self.fields.values())):
            return True
        return False

    @property
    def name(self):
        """:str: Return a string representing the name of the well."""
        return WELL_NAME.format(int(self.x), int(self.y))

    def set_field(
            self, xcoord, ycoord, dxpx=0, dypx=0, gain_field=False,
            img_ok=False):
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
        gain_field : bool
            True if field should run gain selection analysis.
        img_ok : bool
            True if field has acquired an ok image.

        Returns
        -------
        Field instance
            Return the Field instance.
        """
        # pylint: disable=too-many-arguments
        field = Field(
            self._images, xcoord, ycoord, dxpx, dypx, gain_field, img_ok)
        self._fields.update({field.name: field})
        return field


class Plate(object):
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
    wells: dict
        A dict where keys are well names and values are Well instances.
    """

    def __init__(self, images, name):
        """Set up instance."""
        self._images = images
        self.name = name
        self.wells = {}

    def __repr__(self):
        """Return the representation."""
        return "<Plate {}: wells: {}>".format(self.name, self.wells)

    @property
    def images(self):
        """:dict: Return a dict with all images for the plate."""
        return {
            image.path: image for image in list(self._images.values())
            if image.plate_name == self.name
        }

    def set_gain(self, well_x, well_y, channel_name, gain):
        """Set gain in a channel in a well.

        Create a Well instance if well not already exists.

        Parameters
        ----------
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        channel_name : str
            The name of the channel where to set gain.
        gain : int
            The gain value to set.
        """
        well_name = WELL_NAME.format(well_x, well_y)
        if well_name not in self.wells:
            self.set_well(well_x, well_y)
        well = self.wells[well_name]
        channel = Channel(channel_name, gain)
        well.channels.update({channel_name: channel})
        return channel

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
        self.wells[well.name] = well
        return well


class Sample(object):
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
        bus.register(ImageEvent, self._set_image_on_event)

    def __repr__(self):
        """Return the representation."""
        return "<Sample: plates: {}>".format(self._plates)

    @property
    def images(self):
        """:dict: Return all the images of the sample."""
        return self._images

    def _set_image_on_event(self, center, event):
        """Set sample image on an image event from a microscope API."""
        self.set_image(
            event.path, channel_id=event.channel_id, field_x=event.field_x,
            field_y=event.field_y, well_x=event.well_x, well_y=event.well_y)

    def get_plate(self, plate_name=None):
        """Get plate via plate_name.

        Parameters
        ----------
        plate_name : str
            The name of the plate to get.

        Returns
        -------
        Plate instance
            Return a Plate instance. If no plate is found, return None.
        """
        if plate_name:
            plate = self._plates.get(plate_name)
        else:
            plate = next((plate for plate in list(
                self._plates.values())), None)
        if not plate:
            _LOGGER.warning(
                'Plate name %s missing from sample %s', plate_name, self)
            return None
        return plate

    def set_plate(self, plate_name):
        """Create a plate with name for the sample.

        Parameters
        ----------
        plate_name : str
            The name of the plate to set.
        """
        plate = Plate(self._images, plate_name)
        self._plates[plate.name] = plate
        self._bus.notify(PlateEvent({'sample': self, 'plate': plate}))
        return plate

    def all_wells(self, plate_name=None):
        """Get all wells of a plate.

        Parameters
        ----------
        plate_name : str
            The name of the plate that should return the wells.

        Returns
        -------
        list
            Return a list with Well instances. If no plate is found,
            return None.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            return None
        return list(plate.wells.values())

    def get_well(self, well_name, plate_name=None):
        """Get well from plate.

        Parameters
        ----------
        well_name : str
            The name of the well to get.
        plate_name : str
            The name of the plate that should return the well.

        Returns
        -------
        Well instance
            Return a Well instance. If no well is found, return None.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            return None
        well = plate.wells.get(well_name)
        if not well:
            _LOGGER.warning(
                'Well name %s missing from sample %s', well_name, self)
            return None
        return well

    def set_well(self, well_x, well_y, plate_name=None):
        """Set a well on a plate.

        Parameters
        ----------
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        plate_name : str
            The name of the plate that should hold the well.

        Returns
        -------
        Well instance
            Return the Well instance. If no plate is found, return
            None.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            return
        well = plate.set_well(well_x, well_y)
        event = WellEvent({'sample': self, 'plate': plate, 'well': well})
        self._bus.notify(event)
        return well

    def set_gain(self, well_x, well_y, channel_name, gain, plate_name=None):
        """Set gain in a channel in a well of a plate.

        Create a Well instance if well not already exists. Pick the
        first plate if no plate is specified.

        Parameters
        ----------
        well_x : int
            x coordinate of the well.
        well_y : int
            y coordinate of the well.
        channel_name : str
            The name of the channel where to set gain.
        gain : int
            The gain value to set.
        plate_name : str
            The name of the plate that should hold the well with the
            channel.
        """
        # pylint: disable=too-many-arguments
        plate = self.get_plate(plate_name)
        if not plate:
            return
        channel = plate.set_gain(well_x, well_y, channel_name, gain)
        well_name = WELL_NAME.format(well_x, well_y)
        well = plate.wells[well_name]
        event = ChannelEvent({
            'sample': self, 'plate': plate, 'well': well, 'channel': channel})
        self._bus.notify(event)

    def all_fields(self, well_name, plate_name=None):
        """Get all fields of a well of a plate.

        Parameters
        ----------
        well_name : str
            The name of the well that should return the fields.
        plate_name : str
            The name of the plate that should return the fields.

        Returns
        -------
        list
            Return a list with a Field instances. If no fields are
            found, return None.
        """
        plate = self.get_plate(plate_name)
        if not plate:
            return None
        well = self.get_well(well_name, plate_name)
        if not well:
            return None
        return list(well.fields.values())

    def get_field(self, field_name, well_name, plate_name=None):
        """Get field from a well on a plate.

        Parameters
        ----------
        field_name : str
            The name of the field to get.
        well_name : str
            The name of the well that should return the field.
        plate_name : str
            The name of the plate that should return the field.

        Returns
        -------
        Field instance
            Return a Field instance. If no field, well or plate is
            found, return None.
        """
        well = self.get_well(well_name, plate_name)
        field = well.fields.get(field_name)
        if not field:
            _LOGGER.warning(
                'Field name %s missing from sample %s', field_name, self)
            return None
        return field

    def set_field(
            self, well_name, field_x, field_y, dxpx=0, dypx=0,
            gain_field=False, img_ok=False, plate_name=None):
        """Set a field in a well of a plate.

        Pick the first plate if no plate is specified.

        Parameters
        ----------
        well_name : str
            The name of the well that should hold the field.
        field_x : int
            Coordinate of field in x.
        field_y : int
            Coordinate of field in y.
        dxpx : int
            Pixel x coordinate of region of interest within image.
        dypx : int
            Pixel y coordinate of region of interest within image.
        gain_field : bool
            True if field should run gain selection analysis.
        img_ok : bool
            True if field has acquired an ok image.
        plate_name : str
            The name of the plate that should hold the field.
        """
        # pylint: disable=too-many-arguments
        plate = self.get_plate(plate_name)
        if not plate:
            return
        well = self.get_well(well_name, plate_name)
        if not well:
            return
        field = well.set_field(
            field_x, field_y, dxpx, dypx, gain_field, img_ok)
        event = FieldEvent({
            'sample': self, 'plate': plate, 'well': well, 'field': field})
        self._bus.notify(event)

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

    def set_image(
            self, path, data=None, metadata=None, channel_id=None,
            field_x=None, field_y=None, well_x=None, well_y=None,
            plate_name=None):
        """Add an image to the sample.

        Parameters
        ----------
        path : str
            Path to the image.
        data : numpy array
            A numpy array with the image data.
        metadata : str
            The meta data of the image.
        channel_id : int
            The channel id of the image.
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
        """
        # pylint: disable=too-many-arguments, too-many-locals
        image = Image(
            path, data, metadata, channel_id, field_x, field_y, well_x, well_y,
            plate_name)
        self._images[image.path] = image

        if plate_name is not None:
            plate = self.get_plate(plate_name)
            if not plate:
                plate = self.set_plate(plate_name)

        if all(name is not None for name in (plate_name, well_x, well_y)):
            well_name = WELL_NAME.format(well_x, well_y)
            well = self.get_well(well_name)
            if not well:
                well = self.set_well(well_x, well_y, plate_name=plate_name)

        if all(
                name is not None
                for name in (plate_name, well_x, well_y, field_x, field_y)):
            field_name = FIELD_NAME.format(field_x, field_y)
            field = self.get_field(field_name, well_name)
            if not field:
                self.set_field(
                    well_name, field_x, field_y, dxpx=0, dypx=0,
                    gain_field=False, img_ok=False, plate_name=plate_name)

    def remove_image(self, path):
        """Remove an image from the sample.

        Parameters
        ----------
        path : str
            The path to the image that should be removed.
        """
        image = self._images.pop(path, None)
        if image is not None:
            self._bus.notify(ImageRemovedEvent({'image': image}))
