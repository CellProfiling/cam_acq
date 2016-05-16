"""Handle gain."""
import logging
import subprocess
import sys
from collections import defaultdict

import numpy as np
from pkg_resources import resource_filename

from command import cam_com, gain_com, get_wfx, get_wfy
from helper import read_csv

_LOGGER = logging.getLogger(__name__)


def process_output(well, output, dict_list):
    """Process output from the R scripts."""
    for channel in output.split():
        dict_list[well].append(channel)
    return dict_list


def set_gain(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for i, channel in enumerate(channels):
        gain = str(channel)
        if i < 2:
            detector = '1'
            job = job_list[i]
        if i >= 2:
            detector = '2'
            job = job_list[i - 1]
        commands.append(gain_com(exp=job, num=detector, value=gain))
    return commands


class Gain(object):
    """
    Gain class.

    Attributes:
        gain_dict: A defaultdict of lists where the keys are the wells and
        each list (value) contains the gain values of the (four) channels.
    """

    def __init__(self, args, gain_dict, job_list, pattern_g, pattern):
        """Set up instance."""
        self.args = args
        self.gain_dict = gain_dict
        self.job_list = job_list
        self.pattern_g = pattern_g
        self.pattern = pattern
        if args.template_file is None:
            self.template = None
        else:
            self.template = read_csv(
                args.template_file, 'gain_from_well', ['well'])
            self.args.last_well = sorted(self.template.keys())[-1]
        if args.coord_file is None:
            self.coords = defaultdict(list)
        else:
            self.coords = read_csv(args.coord_file, 'fov', ['dxPx', 'dyPx'])
        self.green_sorted = defaultdict(list)
        self.medians = defaultdict(int)

    def calc_gain(self, data):
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
            _LOGGER.debug('WELL: %s', well)
            try:
                _LOGGER.info('Starting R...')
                r_output = subprocess.check_output(['Rscript',
                                                    r_script,
                                                    self.args.imaging_dir,
                                                    fbase,
                                                    init_gain])
                self.gain_dict = process_output(well, r_output, self.gain_dict)
            except OSError as exc:
                _LOGGER.error('Execution failed: %s', exc)
                sys.exit()
            except subprocess.CalledProcessError as exc:
                _LOGGER.error(
                    'Subprocess returned a non-zero exit status: %s', exc)
                sys.exit()
            _LOGGER.debug(r_output)
        return self.gain_dict

    def distribute_gain(self):
        """Collate gain values and distribute them to the wells."""
        self.green_sorted = defaultdict(list)
        self.medians = defaultdict(int)
        for i, channel in enumerate(['green', 'blue', 'yellow', 'red']):
            mlist = []
            for key, val in self.gain_dict.iteritems():
                # Sort gain data into a list dict with green gain as key
                # and where the value is a list of well ids.
                if channel == 'green':
                    # Round gain values to multiples of 10 in green channel
                    if self.args.end_63x:
                        green_val = int(min(round(int(val[i]), -1), 800))
                    else:
                        green_val = int(round(int(val[i]), -1))
                    if self.template:
                        for well in self.template[key]:
                            self.green_sorted[green_val].append(well)
                    else:
                        self.green_sorted[green_val].append(key)
                else:
                    # Find the median value of all gains in
                    # blue, yellow and red channels.
                    mlist.append(int(val[i]))
                    self.medians[channel] = int(np.median(mlist))

    # #FIXME:10 Merge get_com and get_init_com functions, trello:egmsbuN8
    def get_com(self, x_fields, y_fields):
        """Get command."""
        dxcoord = 0
        dycoord = 0
        # Lists for storing command strings.
        com_list = []
        end_com_list = []
        for gain, wells in self.green_sorted.iteritems():
            end_com = []
            channels = [gain,
                        self.medians['blue'],
                        self.medians['yellow'],
                        self.medians['red']]
            com = set_gain([], channels, self.job_list)
            for well in sorted(wells):
                for i in range(y_fields):
                    for j in range(x_fields):
                        # Only add selected fovs from file (arg) to cam list
                        fov = '{}--X0{}--Y0{}'.format(well, j, i)
                        if fov in self.coords.keys():
                            dxcoord = self.coords[fov][0]
                            dycoord = self.coords[fov][1]
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
        return {'com': com_list, 'end_com': end_com_list}

    def get_init_com(self):
        """Get command for gain analysis."""
        wells = []
        if self.template:
            # Selected wells from template file.
            wells = self.template.keys()
        else:
            # All wells.
            for ucoord in range(int(get_wfx(self.args.last_well))):
                for vcoord in range(int(get_wfy(self.args.last_well))):
                    wells.append('U0' + str(ucoord) + '--V0' + str(vcoord))
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
