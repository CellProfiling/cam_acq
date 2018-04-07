"""Handle default gain feedback plugin."""
import logging
import os
import time
from builtins import range, str, zip  # pylint: disable=redefined-builtin
from collections import defaultdict, deque, namedtuple
from itertools import groupby

import matplotlib.pyplot as plt
import pandas as pd
from future import standard_library
from jinja2 import Template
from leicaexperiment import attribute
from pkg_resources import resource_filename
from scipy.optimize import curve_fit

from camacq.api import (ACTION_SEND, ACTION_START_IMAGING, ACTION_STOP_IMAGING,
                        ImageEvent, StopCommandEvent, send)
from camacq.api.leica import command
from camacq.config import load_config_file
from camacq.const import (CHANNEL_ID, CONF_PLUGINS, DEFAULT_FIELDS_X,
                          DEFAULT_FIELDS_Y, FIELD_NAME, FIELDS_X, FIELDS_Y,
                          FIRST_JOB, IMAGING_DIR, JOB_ID, LAST_WELL, PACKAGE,
                          WELL, WELL_NAME)
from camacq.event import SampleEvent
from camacq.helper import (add_fields, call_saved, handler_factory, read_csv,
                           write_csv)
from camacq.image import make_proj
from camacq.plugins.rename_image import ACTION_RENAME_IMAGE
from camacq.sample import Channel

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__)
BOX = 'box'
COUNT = 'count'
VALID = 'valid'
IMAGE = 'image'
CONF_CHANNEL = 'channel'
CONF_CHANNELS = 'channels'
CONF_GAIN = 'gain'
CONF_INIT_GAIN = 'init_gain'
COUNT_CLOSE_TO_ZERO = 2
DEFAULT_JOB_ID_GAIN = 2
DEFAULT_LAST_FIELD_GAIN = 'X01--Y01'
DEFAULT_LAST_SEQ_GAIN = 31
DEFAULT_LAST_WELL = 'U11--V07'
END_10X = 'end_10x'
END_40X = 'end_40x'
END_63X = 'end_63x'
SAVED_GAINS = 'saved_gains'

GREEN = 'green'
BLUE = 'blue'
YELLOW = 'yellow'
RED = 'red'

NA = 'NA'
CAM = 'CAM'
CHANNELS = [GREEN, BLUE, YELLOW, RED, ]
DETECTOR_MAP = {GREEN: '1', BLUE: '1', YELLOW: '2', RED: '2', }
GAIN_DEFAULT = {
    END_10X: {GREEN: 1000, BLUE: 985, YELLOW: 805, RED: 705},
    END_40X: {GREEN: 800, BLUE: 585, YELLOW: 655, RED: 630},
    END_63X: {GREEN: 800, BLUE: 505, YELLOW: 655, RED: 630},
}
GAIN_MAX = {
    END_10X: {GREEN: 1000, BLUE: 1120, YELLOW: 910, RED: 810},
    END_40X: {GREEN: 900, BLUE: 720, YELLOW: 760, RED: 735},
    END_63X: {GREEN: 800, BLUE: 610, YELLOW: 760, RED: 735},
}
GAIN_OFFSET_BLUE = 0
GAIN_OFFSET_RED = 25
GAIN_ONLY = 'gain_only'
GAIN_SCAN = 'gain_scan'
GAIN_FROM_WELL = 'gain_from_well'
INPUT_GAIN = 'input_gain'
JOB_MAP = {GREEN: 0, BLUE: 1, YELLOW: 1, RED: 2, }
TEMPLATE = 'template'
GAIN = 'gain'
PATTERN_G_10X = 'pattern7'
PATTERN_G_40X = 'pattern8'
PATTERN_G_63X = 'pattern9'
JOB_10X = ['job22', 'job23', 'job24']
PATTERN_10X = 'pattern10'
JOB_40X = ['job7', 'job8', 'job9']
PATTERN_40X = 'pattern2'
JOB_63X = ['job10', 'job11', 'job12']
PATTERN_63X = 'pattern3'
STAGE1_DEFAULT = True
STAGE2_DEFAULT = True
JOB_INFO = 'job_info'
STAGE1 = 'stage1'
STAGE2 = 'stage2'
TEMPLATE_FILE = 'template_file'
OBJECTIVE = 'objective'
LISTENERS = 'listeners'
COMMANDS = 'commands'
Data = namedtuple('Data', [BOX, GAIN, VALID])  # pylint: disable=invalid-name
ACTION_CALC_GAIN = 'calc_gain'


def setup_module(center, config):
    """Set up gain calculation plugin."""
    # pylint: disable=too-many-locals
    gain_conf = config[CONF_PLUGINS][CONF_GAIN]
    stage1 = STAGE1_DEFAULT
    stage2 = STAGE2_DEFAULT
    settings = {
        END_10X: {
            JOB_INFO: (JOB_10X, PATTERN_G_10X, PATTERN_10X),
        },
        END_40X: {
            JOB_INFO: (JOB_40X, PATTERN_G_40X, PATTERN_40X),
        },
        END_63X: {
            JOB_INFO: (JOB_63X, PATTERN_G_63X, PATTERN_63X),
        },
        GAIN_ONLY: {
            STAGE2: False,
        },
        INPUT_GAIN: {
            STAGE1: False,
        },
    }
    objective = gain_conf.get(OBJECTIVE)
    if not objective:
        _LOGGER.error('No objective selected')
        return
    job_list, pattern_g, pattern = settings[objective][JOB_INFO]
    center.data[GAIN] = {}
    center.data[GAIN][JOB_INFO] = settings[objective][JOB_INFO]

    if gain_conf.get(GAIN_ONLY):
        stage2 = settings[GAIN_ONLY][STAGE2]

    if gain_conf.get(TEMPLATE_FILE) is None:
        template = None
    else:
        template = read_csv(gain_conf[TEMPLATE_FILE], WELL)
        config[LAST_WELL] = sorted(template.keys())[-1]
    center.data[GAIN][TEMPLATE] = template

    if gain_conf.get(INPUT_GAIN):
        stage1 = settings[INPUT_GAIN][STAGE1]
        gain_dict = read_csv(gain_conf[INPUT_GAIN], WELL)
        distribute_gain(center, gain_dict, template=template)
        com_data = get_com(center, pattern, job_list)
    else:
        com_data = get_init_com(center, pattern_g, template=template)

    center.data[GAIN][LISTENERS] = []
    if stage1:
        center.data[GAIN][LISTENERS].append(center.bus.register(
            ImageEvent, handle_stage1))
    elif stage2:
        center.data[GAIN][LISTENERS].append(center.bus.register(
            ImageEvent, handle_stage2))
    center.data[GAIN][COMMANDS] = deque()
    if stage1 or stage2:
        center.sample.set_plate('0')  # Sample needs at least one plate.
        for commands, end_com in zip(com_data[0], com_data[1]):
            center.data[GAIN][COMMANDS].append((
                send_com_and_start, commands, end_com, stop_end_stage1))
        center.data[GAIN][LISTENERS].append(call_saved(
            center.data[GAIN][COMMANDS].popleft()))

    def handle_calc_gain(**kwargs):
        """Handle call to calc_gain action."""
        images = kwargs.get('images')  # list of paths to calculate gain for
        plot = kwargs.get('make_plots', False)
        save_path = kwargs.get('save_path')  # path to save plots
        projs = make_proj(center.sample, images)
        calc_gain(center, projs, plot, save_path)

    center.actions.register(__name__, ACTION_CALC_GAIN, handle_calc_gain)


def get_gain_com(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for channel, gain in channels.items():
        job = job_list[JOB_MAP[channel]]
        detector = DETECTOR_MAP[channel]
        gain = str(gain.gain)
        commands.append(command.gain_com(job, detector, gain))
    return commands


def calc_gain(center, projs, plot=True, save_path=''):
    """Calculate gain values for the well."""
    config = center.config
    gain_conf = dict(config[CONF_PLUGINS][CONF_GAIN])
    objective = gain_conf.get(OBJECTIVE)
    if objective == END_10X:
        init_gain = resource_filename(PACKAGE, 'data/10x_gain.yml')
    elif objective == END_40X:
        init_gain = resource_filename(PACKAGE, 'data/40x_gain.yml')
    elif objective == END_63X:
        init_gain = resource_filename(PACKAGE, 'data/63x_gain.yml')
    if CONF_CHANNELS not in gain_conf:
        init_gain = load_config_file(init_gain)
        gain_conf[CONF_CHANNELS] = init_gain[CONF_CHANNELS]
    init_gain = [
        Channel(channel[CONF_CHANNEL], gain)
        for channel in gain_conf[CONF_CHANNELS]
        for gain in channel[CONF_INIT_GAIN]]

    gains = _calc_gain(projs, init_gain, plot=plot, save_path=save_path)
    _LOGGER.info('Calculated gains: %s', gains)
    return gains


def _power_func(inp, alpha, beta):
    """Return the value of function of inp, alpha and beta."""
    return alpha * inp**beta


def _check_upward(points):
    """Return a function that checks if points move upward."""
    def wrapped(point):
        """Return True if trend is upward.

        The calculation is done for a point with neighbouring points.
        """
        idx, item = point
        valid = item.valid and item.box <= 600
        prev = next_ = True
        if idx > 0:
            prev = item.box >= points[idx - 1].box
        if idx < len(points) - 1:
            next_ = item.box <= points[idx + 1].box
        return valid and (prev or next_)
    return wrapped


def _create_plot(path, x_data, y_data, coeffs, label):
    """Plot and save plot to path."""
    plt.ioff()
    plt.clf()
    plt.yscale('log')
    plt.xscale('log')
    plt.plot(
        x_data, y_data, 'bo',
        x_data, _power_func(x_data, *coeffs), 'g-', label=label)
    plt.savefig(path)


def _calc_gain(projs, init_gain, plot=True, save_path=''):
    """Calculate gain values for the well.

    Do the actual math.
    """
    # pylint: disable=too-many-locals
    box_vs_gain = defaultdict(list)

    for c_id, proj in projs.items():
        channel = init_gain[c_id]
        hist_data = pd.DataFrame({
            BOX: list(range(len(proj.histogram[0]))),
            COUNT: proj.histogram[0]})
        # Find the max box holding pixels
        box_max_count = hist_data[
            (hist_data[COUNT] > 0) &
            (hist_data[BOX] > 0)][BOX].iloc[-1]
        # Select only histo data where count is > 0 and 255 > box > 0.
        # Only use values in interval 10-100 and
        # > (max box holding pixels - 175).
        roi = hist_data[
            (hist_data[COUNT] > 0) & (hist_data[BOX] > 0) &
            (hist_data[BOX] < 255) & (hist_data[COUNT] >= 10) &
            (hist_data[COUNT] <= 100) &
            (hist_data[BOX] > (box_max_count - 175))]
        if roi.shape[0] < 3:
            continue
        x_data = roi[COUNT].astype(float).values
        y_data = roi[BOX].astype(float).values
        coeffs, _ = curve_fit(_power_func, x_data, y_data, p0=(1000, -1))
        if plot:
            _save_path = '{}{}.ome.png'.format(
                save_path, CHANNEL_ID.format(c_id))
            _create_plot(
                _save_path, hist_data[COUNT], hist_data[BOX], coeffs,
                'count-box')
        # Find box value where count is close to zero.
        # Store that box value and it's corresponding gain value.
        # Store boolean saying if second slope coefficient is negative.
        box_vs_gain[channel.name].append(Data._make((
            _power_func(COUNT_CLOSE_TO_ZERO, *coeffs),
            channel.gain, coeffs[1] < 0)))

    gains = {}
    for channel, points in box_vs_gain.items():
        # Sort points with ascending gain, to allow grouping.
        points = sorted(points, key=lambda item: item.gain)
        long_group = []
        for key, group in groupby(enumerate(points), _check_upward(points)):
            # Find the group with the most points and use that below.
            stored_group = list(group)
            if key and len(stored_group) > len(long_group):
                long_group = stored_group

        # Curve fit the longest group with power function.
        # Plot the points and the fit.
        # Return the calculated gains at bin 255, using fit function.
        if len(long_group) < 3:
            gains[channel] = NA
            continue
        coeffs, _ = curve_fit(
            _power_func, [p[1].box for p in long_group],
            [p[1].gain for p in long_group], p0=(1, 1))
        if plot:
            _save_path = '{}{}.png'.format(save_path, channel)
            _create_plot(
                _save_path, [p.box for p in points],
                [p.gain for p in points], coeffs, 'box-gain')
        gains[channel] = _power_func(255, *coeffs)

    return gains


def sanitize_gain(config, channel, gain):
    """Make sure all channels have a reasonable gain value."""
    gain_conf = config[CONF_PLUGINS][CONF_GAIN]
    objective = gain_conf.get(OBJECTIVE)
    if gain == NA:
        gain = GAIN_DEFAULT[objective][channel]
    gain = int(gain)
    # Round gain values to multiples of 10 and maxout at limits.
    gain = int(min(round(gain, -1), GAIN_MAX[objective][channel]))
    # Add gain offset to blue and red channel.
    if channel == BLUE:
        gain += GAIN_OFFSET_BLUE
    if channel == RED:
        gain += GAIN_OFFSET_RED
    return gain


def distribute_gain(center, gain_dict, template=None):
    """Collate gain values and distribute them to the wells."""
    # pylint: disable=too-many-locals
    config = center.config
    fields_x = config.get(FIELDS_X, DEFAULT_FIELDS_X)
    fields_y = config.get(FIELDS_Y, DEFAULT_FIELDS_Y)
    for gain_well, channels in gain_dict.items():
        for channel, gain in channels.items():
            gain = sanitize_gain(config, channel, gain)
            if template:
                # Add template class with functions and options, later.
                tmpl = template[gain_well][TEMPLATE]
                tmpl = Template(tmpl) if tmpl else Template('{{ gain }}')
                try:
                    gain = int(tmpl.render(gain=gain))
                except ValueError:
                    _LOGGER.error('Failed to render template')
                wells = [
                    well_name for well_name, settings in template.items()
                    if settings[GAIN_FROM_WELL] == gain_well]
                for well_name in wells:
                    well_x = attribute('--{}'.format(well_name), 'U')
                    well_y = attribute('--{}'.format(well_name), 'V')
                    center.sample.set_gain(well_x, well_y, channel, gain)
                    well = center.sample.get_well(well_x, well_y)
                    add_fields(well, fields_x, fields_y)
            else:
                well_x = attribute('--{}'.format(gain_well), 'U')
                well_y = attribute('--{}'.format(gain_well), 'V')
                center.sample.set_gain(well_x, well_y, channel, gain)
                well = center.sample.get_well(well_x, well_y)
                add_fields(well, fields_x, fields_y)


def save_gain(save_dir, saved_gains):
    """Save a csv file with gain values per image channel."""
    header = [WELL, GREEN, BLUE, YELLOW, RED]
    path = os.path.normpath(
        os.path.join(save_dir, 'output_gains.csv'))
    write_csv(path, saved_gains, header)


def get_com(center, job, job_list):
    """Get command."""
    config = center.config
    gain_conf = config[CONF_PLUGINS][CONF_GAIN]
    # Lists for storing command strings.
    com_list = []
    end_com_list = []
    # FIXME: CHECK GAINS AND RUN JOBS SMART  pylint: disable=fixme
    # Ie use one job for multiple wells where the gain is the same
    # or similar.
    for well in center.sample.all_wells():
        if well.img_ok or not well.channels:
            # Only get commands for wells that are not imaged ok and
            # wells that have channels with gain set.
            continue
        end_com = []
        com = get_gain_com([], well.channels, job_list)
        for field in list(well.fields.values()):
            com.append(command.cam_com(
                job, well.x, well.y, field.x, field.y, field.dx, field.dy))
            end_com = [
                CAM, WELL_NAME.format(well.x, well.y),
                JOB_ID.format(gain_conf.get(FIRST_JOB, 2) + 2),
                FIELD_NAME.format(field.x, field.y)]
        # Store the commands in lists.
        com_list.append(com)
        end_com_list.append(end_com)
    return com_list, end_com_list


def get_init_com(center, job, template=None):
    """Get command for gain analysis."""
    # pylint: disable=too-many-locals
    objective = center.config[CONF_PLUGINS][CONF_GAIN].get(OBJECTIVE)
    fields_x = center.config.get(FIELDS_X, DEFAULT_FIELDS_X)
    fields_y = center.config.get(FIELDS_Y, DEFAULT_FIELDS_Y)
    wells = []
    if template:
        # Selected wells from template file.
        for well_name, row in template.items():
            if 'true' in row[GAIN_SCAN]:
                wells.append(well_name)
    else:
        # All wells.
        for ucoord in range(attribute(
                '--{}'.format(center.config.get(LAST_WELL, DEFAULT_LAST_WELL)),
                'U') + 1):
            for vcoord in range(attribute(
                    '--{}'.format(
                        center.config.get(LAST_WELL, DEFAULT_LAST_WELL)),
                    'V') + 1):
                wells.append(WELL_NAME.format(ucoord, vcoord))
    # Lists and strings for storing command strings.
    com_list = []
    end_com_list = []
    end_com = []
    # Selected objective gain job cam command in wells.
    for well_name in sorted(wells):
        well_x = attribute('--{}'.format(well_name), 'U')
        well_y = attribute('--{}'.format(well_name), 'V')
        well = center.sample.set_well(well_x, well_y)
        add_fields(well, fields_x, fields_y)
        com = []
        for field in center.sample.all_fields(well_x, well_y):
            if not field.gain_field:
                continue
            com.append(command.cam_com(
                job, well.x, well.y, field.x, field.y, field.dx, field.dy))
            end_com = [
                CAM, well, JOB_ID.format(2),
                FIELD_NAME.format(field.x, field.y)]
        com_list.append(com)
        end_com_list.append(end_com)

    # Join the list of lists of command lists into a list of a command
    # list if dry a objective is used.
    if objective == END_10X or objective == END_40X:
        com_list = [c for commands in com_list for c in commands]
        com_list = [com_list]
        end_com_list = [end_com_list[-1]]
    return com_list, end_com_list


def handle_imgs(center, images, first_job_id=2):
    """Handle acquired images, do renaming, make max projections."""
    _LOGGER.info('Handling images...')
    new_paths = []

    def add_image_on_event(center, event):
        """Add image to list."""
        new_paths.append(event.image.path)

    remove_handler = center.bus.register(SampleEvent, add_image_on_event)
    for image_path in images:
        center.actions.call(
            'camacq.plugins.rename_image', ACTION_RENAME_IMAGE,
            path=image_path, first_job_id=first_job_id)
    remove_handler()
    return list(set(new_paths))


def handle_stage1(center, event):
    """Handle saved image during stage 1."""
    _LOGGER.info('Handling image during stage 1...')
    image_path = event.path
    if not image_path:
        return
    field_name = FIELD_NAME.format(event.field_x, event.field_y)
    # This means only ever one well at a time.
    if (field_name !=
            DEFAULT_LAST_FIELD_GAIN or
            event.channel_id != DEFAULT_LAST_SEQ_GAIN):
        return
    image = center.sample.get_image(image_path)
    well_name = WELL_NAME.format(image.well_x, image.well_y)
    well = center.sample.get_well(image.well_x, image.well_y)
    new_paths = handle_imgs(center, list(
        well.images.keys()), DEFAULT_JOB_ID_GAIN)
    if not new_paths:
        return
    # Make a max proj per channel.
    projs = make_proj(center.sample, new_paths)
    imaging_dir = center.config.get(IMAGING_DIR, '')
    plate = center.sample.get_plate()
    save_path = os.path.normpath(os.path.join(
        imaging_dir, 'gains', plate.name, well_name, well_name))
    _LOGGER.info('Calculating gain settings for well: %s', well_name)
    gains = calc_gain(center, save_path, projs)
    gain_dict = {WELL_NAME.format(image.well_x, image.well_y): gains}
    _LOGGER.debug('Gain dict: %s', gain_dict)
    if SAVED_GAINS not in center.data:
        center.data[SAVED_GAINS] = defaultdict(dict)
    center.data[SAVED_GAINS].update(gain_dict)
    _LOGGER.debug('%s: %s', SAVED_GAINS, center.data[SAVED_GAINS])
    save_gain(imaging_dir, center.data[SAVED_GAINS])
    distribute_gain(
        center, gain_dict, template=center.data[GAIN].get(TEMPLATE))
    _LOGGER.debug('Sample: %s', center.sample)


def handle_stage2(center, event):
    """Handle saved image during stage 2."""
    _LOGGER.info('Handling image during stage 2...')
    gain_conf = center.config[CONF_PLUGINS][CONF_GAIN]
    image_path = event.path
    if not image_path:
        return
    well = center.sample.get_well(event.well_x, event.well_y)
    if not well:
        return
    field_name = FIELD_NAME.format(event.field_x, event.field_y)
    field = well.fields.get(field_name)
    if not field:
        return
    well.fields[field_name] = field._replace(img_ok=True)
    handle_imgs(
        center, list(field.images.keys()), gain_conf[FIRST_JOB])


def stop(center):
    """Handle event that should stop the microscope."""
    for remove_listener in center.data[GAIN][LISTENERS]:
        remove_listener()
    center.data[GAIN][LISTENERS].clear()
    store = {'scan_finished': False}  # python 2 doesn't support nonlocal

    def check_scan_finished(center, event):
        """Check that scan is finished."""
        store['scan_finished'] = True

    center.data[GAIN][LISTENERS].append(center.bus.register(
        StopCommandEvent, check_scan_finished))
    center.actions.call('camacq.api', ACTION_STOP_IMAGING)
    begin = time.time()
    while not store['scan_finished']:
        # Wait for scanfinished reply with timeout.
        if time.time() - begin > 20.0:
            break
        time.sleep(0.5)
    time.sleep(1)  # Wait for it to come to complete stop.


def stop_end_stage1(center, event):
    """Handle event that should end stage1 after stop."""
    _LOGGER.info('Handling stop event at end stage 1...')
    stop(center)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage2))
    job_list, _, pattern = center.data[GAIN][JOB_INFO]
    com_data = get_com(center, pattern, job_list)
    todo = [
        (send_com_and_start, com, end_com, stop_mid_stage2)
        for com, end_com in zip(com_data[0], com_data[1])]
    todo.pop()
    center.data[GAIN][COMMANDS].extendleft([(
        send_com_and_start, com_data[0][-1],
        com_data[1][-1], stop_end_stage2)])
    center.data[GAIN][COMMANDS].extendleft(reversed(todo))
    call = center.data[GAIN][COMMANDS].popleft()
    center.data[GAIN][LISTENERS].append(call_saved(call))


def stop_mid_stage2(center, event):
    """Handle event that should continue with stage2 after stop."""
    _LOGGER.info('Handling stop event during stage 2...')
    stop(center)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage2))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(call_saved(call))


def stop_end_stage2(center, event):
    """Handle event that should end stage2 after stop."""
    _LOGGER.info('Handling stop event at end stage 2...')
    stop(center)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage1))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(call_saved(call))


def send_com_and_start(center, commands, stop_data, handler):
    """Add commands to outgoing queue for the CAM server."""
    def stop_test(event):
        """Test if stop should be done."""
        if all(test in event.rel_path for test in stop_data):
            return True
        return False

    remove_listener = center.bus.register(
        ImageEvent, handler_factory(center, handler, stop_test))

    center.actions.call(
        'camacq.api', ACTION_SEND, command=command.del_com())
    time.sleep(2)
    send(center, commands)
    time.sleep(2)
    center.actions.call('camacq.api', ACTION_START_IMAGING)
    # Wait for it to change objective and start.
    time.sleep(7)
    center.actions.call(
        'camacq.api', ACTION_SEND, command=command.camstart_com())

    return remove_listener
