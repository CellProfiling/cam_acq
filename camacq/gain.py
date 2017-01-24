"""Handle gain."""
import logging
import subprocess
import sys
from collections import defaultdict

from jinja2 import Template
from pkg_resources import resource_filename

from command import cam_com, gain_com, get_wfx, get_wfy
from helper import read_csv

_LOGGER = logging.getLogger(__name__)
# Make these constants configurable.
GAIN_OFFSET_BLUE = 0
GAIN_OFFSET_RED = 25
NA = 'NA'
GREEN = 'green'
BLUE = 'blue'
YELLOW = 'yellow'
RED = 'red'
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


def process_output(well, output, well_map):
    """Process output from the R script."""
    channels = output.split()
    for index, gain in enumerate(channels):
        well_map[well].update({CHANNELS[index]: gain})
    return well_map


def set_gain(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for channel, gain in channels.iteritems():
        job = job_list[JOB_MAP[channel]]
        detector = DETECTOR_MAP[channel]
        gain = str(gain.gain)
        commands.append(gain_com(exp=job, num=detector, value=gain))
    return commands


class Gain(object):
    """Gain class."""

    __slots__ = ['channel', '_gain', ]

    def __init__(self, channel, gain):
        """Set up instance."""
        self.channel = channel
        self._gain = gain

    @property
    def gain(self):
        """Return gain."""
        return self._gain

    @gain.setter
    def gain(self, value):
        """Set gain."""
        self._gain = int(value)


class GainMap(object):
    """
    Contain the information and methods to calculate gain for each well.

    Parameters
    ----------
    args : dict
        Dict with command line arguments from the start of the program.
    job_list : list
        List of names of the jobs for the objective and experiment.
    pattern_g : str
        Name of the pattern for the gain job.
    pattern : str
        Name of the pattern for the experiment job.

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
    wells: collections.defaultdict
        A defaultdict of dicts where the keys are the wells and
        each sub dict (value) maps the channel and gain object.
    """

    def __init__(self, args, job_info):
        """Set up instance."""
        self.args = args
        self.job_list, self.pattern_g, self.pattern = job_info
        if args.template_file is None:
            self.template = None
        else:
            self.template = read_csv(args.template_file, 'well')
            self.args.last_well = sorted(self.template.keys())[-1]
        if args.coord_file is None:
            self.coords = defaultdict(dict)
        else:
            self.coords = read_csv(args.coord_file, 'fov')
        self.wells = defaultdict(dict)

    def calc_gain(self, data, gain_dict):
        """Run R scripts and calculate gain values for the wells."""
        # Get a unique set of filebases from the csv paths.
        filebases = sorted(set(data['bases']))
        # Get a unique set of names of the experiment wells.
        fin_wells = sorted(set(data['wells']))
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

    def distribute_gain(self, gain_dict):
        """Collate gain values and distribute them to the wells."""
        for gain_well, channels in gain_dict.iteritems():
            for channel, gain in channels.iteritems():
                gain = self.sanitize_gain(channel, gain)
                if self.template:
                    # Add template class with functions and options, later.
                    tmpl = Template(self.template[gain_well]['template'])
                    try:
                        gain = int(tmpl.render(gain=gain))
                    except ValueError:
                        pass
                    wells = [
                        well for well, settings in self.template.iteritems()
                        if settings['gain_from_well'] == gain_well]
                    for well in wells:
                        self.wells[well].update({channel: Gain(channel, gain)})
                else:
                    self.wells[
                        gain_well].update({channel: Gain(channel, gain)})

    # #FIXME:10 Merge get_com and get_init_com functions, trello:egmsbuN8
    def get_com(self, x_fields, y_fields):
        """Get command."""
        dxcoord = 0
        dycoord = 0
        # Lists for storing command strings.
        com_list = []
        end_com_list = []
        for well, channels in self.wells:
            end_com = []
            com = set_gain([], channels, self.job_list)
            for i in range(y_fields):
                for j in range(x_fields):
                    # Only add selected fovs from file (arg) to cam list
                    fov = '{}--X0{}--Y0{}'.format(well, j, i)
                    if fov in self.coords.keys():
                        dxcoord = self.coords[fov]['dxPx']
                        dycoord = self.coords[fov]['dyPx']
                        fov_is = True
                    elif not self.coords:
                        fov_is = True
                    else:
                        fov_is = False
                    if fov_is:
                        com.append(cam_com(self.pattern,
                                           well,
                                           'X0{}--Y0{}'.format(j, i),
                                           dxcoord,
                                           dycoord))
                        end_com = ['CAM',
                                   well,
                                   'E0' + str(self.args.first_job + 2),
                                   'X0{}--Y0{}'.format(j, i)]
            # Store the commands in lists.
            com_list.append(com)
            end_com_list.append(end_com)
        # Empty wells after all commands have been fetched.
        self.wells = defaultdict(dict)
        return {'com': com_list, 'end_com': end_com_list}

    def get_init_com(self):
        """Get command for gain analysis."""
        wells = []
        if self.template:
            # Selected wells from template file.
            for well, row in self.template.iteritems():
                if 'true' in row['gain_scan']:
                    wells.append(well)
        else:
            # All wells.
            for ucoord in range(int(get_wfx(self.args.last_well))):
                for vcoord in range(int(get_wfy(self.args.last_well))):
                    wells.append('U{0:02d}--V{1:02d}'.format(ucoord, vcoord))
        # Lists and strings for storing command strings.
        com_list = []
        end_com_list = []
        end_com = []
        # Selected objective gain job cam command in wells.
        for well in sorted(wells):
            com = []
            for i in range(2):
                com.append(cam_com(self.pattern_g, well,
                                   'X0{}--Y0{}'.format(i, i), '0', '0'))
                end_com = ['CAM', well, 'E0' + str(2),
                           'X0{}--Y0{}'.format(i, i)]
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
            end_com_list = [end_com]
        return {'com': com_list, 'end_com': end_com_list}
