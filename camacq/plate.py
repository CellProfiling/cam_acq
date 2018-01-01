"""Handle gain."""
from collections import OrderedDict, namedtuple

from matrixscreener.experiment import attribute

from camacq.const import FIELD_NAME, WELL_NAME


class Channel(object):
    """Represent a channel with gain.

    Parameters
    ----------
    channel : str
        Name of the channel.
    gain : int
        Gain value.

    Attributes
    ----------
    channel : str
        Return name of the channel.
    """

    # pylint: disable=too-few-public-methods

    __slots__ = ['channel', '_gain', ]

    def __init__(self, channel, gain):
        """Set up instance."""
        self.channel = channel
        self._gain = gain

    def __repr__(self):
        """Return the representation."""
        return "<Channel {}: gain {}>".format(self.channel, self._gain)

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


class Field(namedtuple('Field', 'x y dx dy gain_field img_ok')):
    """Represent a field.

    Parameters
    ----------
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

    @property
    def name(self):
        """:str: Return a string representing the name of the field."""
        return FIELD_NAME.format(int(self.x), int(self.y))


class Well(object):
    """Represent a well with fields and gain.

    Parameters
    ----------
    name : str
        Name of the well in format 'U00-V00'.

    Attributes
    ----------
    x : int
        Number showing the x coordinate of the well, from 0.
    y : int
        Number showing the y coordinate of the well, from 0.
    channels : dict
        Dict where keys are color channels and values are Gain instances.
    """

    def __init__(self, x, y):
        """Set up instance."""
        # pylint: disable=invalid-name
        self.x = x
        self.y = y
        self._field = Field(0, 0, 0, 0, False, False)
        self._fields = OrderedDict()
        self.channels = {}

    def __repr__(self):
        """Return the representation."""
        return "<Well {}: channels {}>".format(self.name, self.channels)

    @property
    def fields(self):  # noqa D301, D207
        """:dict: Return a dict of field coordinates as named tuples.

        :setter: Sets the coordinates of multiple fields.
            Should be a sequence or iterable of tuples or lists.

        Example
        -------
        ::

            >>> well = Well(0, 0)
            >>> well.fields = [[1, 3, 0, 1, True, False], ]
            >>> well.fields
            {'X01--Y03': Field(x=1, y=3, dx=0, dy=1, \
gain_field=True, img_ok=False)}
        """
        return self._fields

    @fields.setter
    def fields(self, fields):
        """Set the fields."""
        self._fields = {
            FIELD_NAME.format(field[0], field[1]): self._field._make(field)
            for field in fields}

    @property
    def img_ok(self):
        """:bool: Return True if there are fields and all are imaged ok."""
        if self.fields and all(field.img_ok for field in self.fields.values()):
            return True
        return False

    @property
    def name(self):
        """:str: Return a string representing the name of the well."""
        return WELL_NAME.format(int(self.x), int(self.y))

    def add_field(
            self, xcoord, ycoord, dxpx=0, dypx=0, gain_field=False,
            img_ok=False):
        """Add a field to the well."""
        # pylint: disable=too-many-arguments
        field = self._field._make(
            (xcoord, ycoord, dxpx, dypx, gain_field, img_ok))
        self._fields.update({field.name: field})  # pylint: disable=no-member

    def set_fields(self, fields_x, fields_y):
        """Set fields."""
        for i in range(fields_y):
            for j in range(fields_x):
                self.add_field(
                    j, i, 0, 0, j == 0 and i == 0 or j == 1 and i == 1)


class Plate(object):
    """
    Hold the wells in one container.

    Attributes
    ----------
    wells: dict
        A dict where the keys are the wells and each value is Well object.
    """

    def __init__(self):
        """Set up instance."""
        self.wells = {}

    def __repr__(self):
        """Return the representation."""
        return "<Wells {}>".format(self.wells)

    def set_gain(self, well_name, channel, gain):
        """Set gain in a channel in a well.

        Create a Well instance if well not already exists.
        """
        if well_name not in self.wells:
            well_x = attribute('--{}'.format(well_name), 'U')
            well_y = attribute('--{}'.format(well_name), 'V')
            self.add_well(well_x, well_y)
        self.wells[well_name].channels.update(
            {channel: Channel(channel, gain)})

    def add_well(self, well_x, well_y):
        """Add a Well instance to wells with well_name."""
        well = Well(well_x, well_y)
        self.wells[well.name] = well
