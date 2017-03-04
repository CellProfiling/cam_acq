"""Handle gain."""
import logging
import subprocess
import sys
from collections import defaultdict, namedtuple

from jinja2 import Template
from matrixscreener.experiment import attribute
from pkg_resources import resource_filename

from camacq.command import cam_com, gain_com
from camacq.const import (BLUE, FIELD_NAME, FOV_NAME, GREEN, JOB_ID, RED, WELL,
                          WELL_NAME, YELLOW)
from camacq.helper import read_csv

_LOGGER = logging.getLogger(__name__)
# Make these constants configurable.
GAIN_OFFSET_BLUE = 0
GAIN_OFFSET_RED = 25
NA = 'NA'
TEN_X = '10x'
FORTY_X = '40x'
SIXTYTHREE_X = '63x'
GAIN_DEFAULT = {
    TEN_X: {GREEN: 1000, BLUE: 985, YELLOW: 805, RED: 705},
    FORTY_X: {GREEN: 800, BLUE: 585, YELLOW: 655, RED: 630},
    SIXTYTHREE_X: {GREEN: 800, BLUE: 505, YELLOW: 655, RED: 630},
}
CHANNELS = [GREEN, BLUE, YELLOW, RED, ]
DETECTOR_MAP = {GREEN: '1', BLUE: '1', YELLOW: '2', RED: '2', }
JOB_MAP = {GREEN: 0, BLUE: 1, YELLOW: 1, RED: 2, }
GAIN_SCAN = 'gain_scan'
GAIN_FROM_WELL = 'gain_from_well'
TEMPLATE = 'template'
FOV = 'fov'
DX_PX = 'dxPx'
DY_PX = 'dyPx'
CAM = 'CAM'


def process_output(well, output, well_map):
    """Process output from the R script."""
    channels = output.split()
    for index, gain in enumerate(channels):
        well_map[well].update({CHANNELS[index]: int(gain)})
    return well_map


def get_gain_com(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for channel, gain in channels.iteritems():
        job = job_list[JOB_MAP[channel]]
        detector = DETECTOR_MAP[channel]
        gain = str(gain.gain)
        commands.append(gain_com(exp=job, num=detector, value=gain))
    return commands


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
        self._fields = {}
        self.channels = {}

    def __repr__(self):
        """Return the representation."""
        return "<Well {}: channels {}>".format(
            WELL_NAME.format(int(self.U), int(self.V)), self.channels)

    def add_field(
            self, xcoord, ycoord, dxpx=0, dypx=0,
            gain_field=False, img_ok=False):
        """Add a field to the well."""
        # pylint: disable=too-many-arguments
        self._fields.update({
            FIELD_NAME.format(xcoord, ycoord):
            self._field._make(
                (xcoord, ycoord, dxpx, dypx, gain_field, img_ok))})

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
        """:bool: Return True if all fields of the well are imaged ok."""
        return all(field.img_ok for field in self.fields.values())


class GainMap(object):
    """
    Contain the information and methods to calculate gain for each well.

    Parameters
    ----------
    args : dict
        Dict with command line arguments from the start of the program.
    job_info : tuple
        Tuple of job_list, pattern_g, and pattern, which will be attributes.

    Attributes
    ----------
    args : dict
        Dict with command line arguments from the start of the program.
    job_list : list
        List of names of the jobs for the objective and experiment.
    pattern_g : str
        Name of the pattern for the gain job.
    pattern : str
        Name of the pattern for the experiment job.
    template : collections.defaultdict
        A defaultdict of dicts that maps wells and gain analysis wells,
        where to run the experiment.
    coords : collections.defaultdict
        A defaultdict of dicts that map wells and selected positions with
        pixel coordinates. The coordinates represent where to acquire the
        images in the wells, relative to the center of each field.
        The pixel coordinates have the same size as the chosen objective.
    wells: dict
        A dict where the keys are the wells and each value is Well object.
    """

    def __init__(self, args, job_info):
        """Set up instance."""
        self.args = args
        self.job_list, self.pattern_g, self.pattern = job_info
        if args.template_file is None:
            self.template = None
        else:
            self.template = read_csv(args.template_file, WELL)
            self.args.last_well = sorted(self.template.keys())[-1]
        if args.coord_file is None:
            self.coords = defaultdict(dict)
        else:
            self.coords = read_csv(args.coord_file, FOV)
        self.wells = {}

    def __repr__(self):
        """Return the representation."""
        return "<Wells {}>".format(self.wells)

    def calc_gain(self, bases, wells):
        """Run R scripts and calculate gain values for the wells."""
        # Get a unique set of filebases from the csv paths.
        gain_dict = defaultdict(dict)
        filebases = sorted(set(bases))
        # Get a unique set of names of the experiment wells.
        fin_wells = sorted(set(wells))
        r_script = resource_filename(__name__, 'data/gain.r')
        if self.args.end_10x:
            init_gain = resource_filename(__name__, 'data/10x_gain.csv')
        elif self.args.end_40x:
            init_gain = resource_filename(__name__, 'data/40x_gain.csv')
        elif self.args.end_63x:
            init_gain = resource_filename(__name__, 'data/63x_gain.csv')
        if self.args.init_gain:
            init_gain = self.args.init_gain
        for fbase, well in zip(filebases, fin_wells):
            _LOGGER.info('WELL: %s', well)
            try:
                _LOGGER.info('Starting R...')
                r_output = subprocess.check_output(['Rscript',
                                                    r_script,
                                                    self.args.imaging_dir,
                                                    fbase,
                                                    init_gain])
                gain_dict = process_output(well, r_output, gain_dict)
            except OSError as exc:
                _LOGGER.error('Execution failed: %s', exc)
                sys.exit()
            except subprocess.CalledProcessError as exc:
                _LOGGER.error(
                    'Subprocess returned a non-zero exit status: %s', exc)
                sys.exit()
            _LOGGER.debug(r_output)
        return gain_dict

    def sanitize_gain(self, channel, gain):
        """Make sure all channels have a reasonable gain value."""
        if self.args.end_10x:
            obj = TEN_X
        elif self.args.end_40x:
            obj = FORTY_X
        elif self.args.end_63x:
            obj = SIXTYTHREE_X
        if gain == NA:
            gain = GAIN_DEFAULT[obj][channel]
        if channel == GREEN:
            # Round gain values to multiples of 10 in green channel
            if self.args.end_63x:
                gain = int(min(
                    round(int(gain), -1), GAIN_DEFAULT[SIXTYTHREE_X][GREEN]))
            else:
                gain = int(round(int(gain), -1))
        # Add gain offset to blue and red channel.
        if channel == BLUE:
            gain += GAIN_OFFSET_BLUE
        if channel == RED:
            gain += GAIN_OFFSET_RED
        return gain

    def set_gain(self, well, channel, gain):
        """Set gain in a channel in a well.

        Create a Well instance if well not already exists.
        """
        if well not in self.wells:
            self.wells[well] = Well(well)
        self.wells[well].channels.update({channel: Channel(channel, gain)})

    def distribute_gain(self, gain_dict):
        """Collate gain values and distribute them to the wells."""
        for gain_well, channels in gain_dict.iteritems():
            for channel, gain in channels.iteritems():
                gain = self.sanitize_gain(channel, gain)
                if self.template:
                    # Add template class with functions and options, later.
                    tmpl = Template(self.template[gain_well][TEMPLATE])
                    try:
                        gain = int(tmpl.render(gain=gain))
                    except ValueError:
                        pass
                    wells = [
                        well for well, settings in self.template.iteritems()
                        if settings[GAIN_FROM_WELL] == gain_well]
                    for well in wells:
                        self.set_gain(well, channel, gain)
                else:
                    self.set_gain(gain_well, channel, gain)

    def set_fields(self, well, x_fields, y_fields):
        """Set fields."""
        for i in range(y_fields):
            for j in range(x_fields):
                # Only add selected fovs from file (arg) to cam list
                fov = FOV_NAME.format(well.U, well.V, j, i)
                if fov in self.coords.keys():
                    dxcoord = self.coords[fov][DX_PX]
                    dycoord = self.coords[fov][DY_PX]
                    well.add_field(
                        j, i, dxcoord, dycoord,
                        j == 0 and i == 0 or j == 1 and i == 1)
                elif not self.coords:
                    well.add_field(
                        j, i, 0, 0, j == 0 and i == 0 or j == 1 and i == 1)

    def get_com(self, x_fields, y_fields):
        """Get command."""
        # Lists for storing command strings.
        com_list = []
        end_com_list = []
        # FIXME: CHECK GAINS AND RUN JOBS SMART  pylint: disable=fixme
        # Ie use one job for multiple wells where the gain is the same
        # or similar.
        for well in self.wells.values():
            self.set_fields(well, x_fields, y_fields)
            if well.img_ok:
                # Only get commands for wells that are not imaged ok.
                continue
            end_com = []
            com = get_gain_com([], well.channels, self.job_list)
            for field in well.fields.values():
                com.append(cam_com(
                    self.pattern, well.U, well.V, field.X, field.Y, field.dX,
                    field.dY))
                end_com = [
                    CAM, WELL_NAME.format(well.U, well.V),
                    JOB_ID.format(self.args.first_job + 2),
                    FIELD_NAME.format(field.X, field.Y)]
            # Store the commands in lists.
            com_list.append(com)
            end_com_list.append(end_com)
        return {'com': com_list, 'end_com': end_com_list}

    def get_init_com(self):
        """Get command for gain analysis."""
        wells = []
        if self.template:
            # Selected wells from template file.
            for well, row in self.template.iteritems():
                if 'true' in row[GAIN_SCAN]:
                    wells.append(well)
        else:
            # All wells.
            for ucoord in range(
                    attribute('--{}'.format(self.args.last_well), 'U') + 1):
                for vcoord in range(attribute(
                        '--{}'.format(self.args.last_well), 'V') + 1):
                    wells.append(WELL_NAME.format(ucoord, vcoord))
        # Lists and strings for storing command strings.
        com_list = []
        end_com_list = []
        end_com = []
        # Selected objective gain job cam command in wells.
        for well in sorted(wells):
            com = []
            well_u_id = attribute('--{}'.format(well), 'U')
            well_v_id = attribute('--{}'.format(well), 'V')
            for i in range(2):
                com.append(cam_com(
                    self.pattern_g, well_u_id, well_v_id, i, i, '0', '0'))
                end_com = [
                    CAM, well, JOB_ID.format(2), FIELD_NAME.format(i, i)]
            com_list.append(com)
            end_com_list.append(end_com)

        # Join the list of lists of command lists into a list of a command
        # list if dry a objective is used.
        if self.args.end_10x or self.args.end_40x:
            com_list_bak = list(com_list)
            com_list = []
            for com in com_list_bak:
                com_list.extend(com)
            com_list = [com_list]
            end_com_list = [end_com_list[-1]]
        return {'com': com_list, 'end_com': end_com_list}
