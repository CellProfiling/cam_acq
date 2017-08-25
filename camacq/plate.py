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


class Field(namedtuple('Field', 'X Y dX dY gain_field img_ok')):
    """Represent a field.

    Parameters
    ----------
    X : int
        Coordinate of field in X.
    Y : int
        Coordinate of field in Y.
    dX : int
        Pixel coordinate of region of interest within image field in X.
    dY : int
        Pixel coordinate of region of interest within image field in Y.
    gain_field : bool
        True if field should run gain selection analysis.
    img_ok : bool
        True if field has acquired an ok image.
    """


class Well(object):
    """Represent a well with fields and gain.

    Parameters
    ----------
    name : str
        Name of the well in format 'U00-V00'.

    Attributes
    ----------
    U : int
        Number showing the U coordinate of the well, from 0.
    V : int
        Number showing the V coordinate of the well, from 0.
    channels : dict
        Dict where keys are color channels and values are Gain instances.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, name):
        """Set up instance."""
        # pylint: disable=invalid-name
        self.U = attribute('--{}'.format(name), 'U')
        self.V = attribute('--{}'.format(name), 'V')
        self._field = Field(0, 0, 0, 0, False, False)
        self._fields = OrderedDict()
        self.channels = {}

    def __repr__(self):
        """Return the representation."""
        return "<Well {}: channels {}>".format(
            WELL_NAME.format(int(self.U), int(self.V)), self.channels)

    @property
    def fields(self):  # noqa D301, D207
        """:dict: Return a dict of field coordinates as named tuples.

        :setter: Sets the coordinates of multiple fields.
            Should be a sequence or iterable of tuples or lists.

        Example
        -------
        ::

            >>> well = Well('U00--V00')
            >>> well.fields = [[1, 3, 0, 1, True, False], ]
            >>> well.fields
            {'X01--Y03': Field(X=1, Y=3, dX=0, dY=1, \
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

    def add_field(
            self, xcoord, ycoord, dxpx=0, dypx=0, gain_field=False,
            img_ok=False):
        """Add a field to the well."""
        # pylint: disable=too-many-arguments
        self._fields.update({
            FIELD_NAME.format(xcoord, ycoord):
            self._field._make(
                (xcoord, ycoord, dxpx, dypx, gain_field, img_ok))})

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
            self.set_well(well_name)
        self.wells[well_name].channels.update(
            {channel: Channel(channel, gain)})

    def set_well(self, well_name):
        """Add a Well instance to wells with well_name."""
        self.wells[well_name] = Well(well_name)
