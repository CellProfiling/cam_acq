"""Handle default gain feedback plugin."""
import logging
import os
import time
from collections import defaultdict, deque, namedtuple
from itertools import groupby

import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import Template
from matrixscreener.experiment import attribute, attributes
from pkg_resources import resource_filename
from scipy.optimize import curve_fit

from camacq.bootstrap import PACKAGE
from camacq.command import cam_com, gain_com
from camacq.config import load_config_file
from camacq.const import (DEFAULT_FIELDS_X, DEFAULT_FIELDS_Y,
                          FIELD_NAME, FIELDS_X, FIELDS_Y,
                          FIRST_JOB, IMAGING_DIR,
                          JOB_ID, LAST_WELL, WELL,
                          WELL_NAME, WELL_NAME_CHANNEL)
from camacq.control import ImageEvent
from camacq.helper import (find_image_path, format_new_name, get_field,
                           get_imgs, get_well, read_csv, send_com_and_start,
                           write_csv)
from camacq.image import make_proj
from camacq.plate import Channel

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
SCAN_FINISHED = 'scanfinished'

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


def setup_module(center, config):
    """Setup default actions module."""
    # pylint: disable=too-many-locals
    stage1 = STAGE1_DEFAULT
    stage2 = STAGE2_DEFAULT
    flow_map = {
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
    for attr, settings in flow_map.iteritems():
        if config.get(attr):
            stage1 = settings.get(STAGE1, stage1)
            stage2 = settings.get(STAGE2, stage2) if not \
                config[GAIN].get(GAIN_ONLY) else flow_map[GAIN_ONLY][STAGE2]
            if JOB_INFO in settings:
                job_info = settings[JOB_INFO]
            if INPUT_GAIN == attr:
                gain_dict = read_csv(config[GAIN][INPUT_GAIN], WELL)

    job_list, pattern_g, pattern = job_info
    center.data[GAIN] = {}
    center.data[GAIN][JOB_INFO] = job_info
    if config[GAIN].get(TEMPLATE_FILE) is None:
        template = None
    else:
        template = read_csv(config[GAIN][TEMPLATE_FILE], WELL)
        config[LAST_WELL] = sorted(template.keys())[-1]
    center.data[GAIN][TEMPLATE] = template

    if config[GAIN].get(INPUT_GAIN):
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
        for commands, end_com in zip(com_data[0], com_data[1]):
            center.data[GAIN][COMMANDS].append((
                send_com_and_start, commands, end_com, stop_end_stage1))
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(center.call_saved(call))


def get_gain_com(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for channel, gain in channels.iteritems():
        job = job_list[JOB_MAP[channel]]
        detector = DETECTOR_MAP[channel]
        gain = str(gain.gain)
        commands.append(gain_com(exp=job, num=detector, value=gain))
    return commands


def calc_gain(config, imgp, projs, plot=True):
    """Calculate gain values for the well."""
    objective = config[GAIN].get(OBJECTIVE)
    if objective == END_10X:
        init_gain = resource_filename(PACKAGE, 'data/10x_gain.yml')
    elif objective == END_40X:
        init_gain = resource_filename(PACKAGE, 'data/40x_gain.yml')
    elif objective == END_63X:
        init_gain = resource_filename(PACKAGE, 'data/63x_gain.yml')
    if not config[GAIN].get(CONF_CHANNELS):
        init_gain = load_config_file(init_gain)
        config[GAIN][CONF_CHANNELS] = init_gain[CONF_CHANNELS]
    _LOGGER.info('Calculating gain...')
    init_gain = [
        Channel(channel[CONF_CHANNEL], gain)
        for channel in config[GAIN][CONF_CHANNELS]
        for gain in channel[CONF_INIT_GAIN]]

    return _calc_gain(imgp, init_gain, projs, plot=plot)


def _power_func(inp, alpha, beta):
    """Return the value of function of inp, alpha and beta."""
    return alpha * inp**beta


def _check_upward(points):
    """Return a function that checks if points move upward."""
    def wrapped(point):
        """Return True if trend for point and neighbouring points is upward."""
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


def _calc_gain(imgp, init_gain, projs, plot=True):
    """Calculate gain values for the well.

    Do the actual math.
    """
    # pylint: disable=too-many-locals
    img_attr = attributes(imgp)
    wellp = get_well(imgp)
    box_vs_gain = defaultdict(list)

    _LOGGER.info('WELL_PATH: %s', wellp)
    for c_id, proj in projs.iteritems():
        channel = init_gain[int(c_id)]
        hist_data = pd.DataFrame({
            BOX: range(len(proj.histogram[0])),
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
        save_path = os.path.normpath(os.path.join(
            wellp, (WELL_NAME_CHANNEL + '.ome.png').format(
                img_attr.u, img_attr.v, int(c_id))))
        if plot:
            _create_plot(
                save_path, hist_data[COUNT], hist_data[BOX], coeffs,
                'count-box')
        # Find box value where count is close to zero.
        # Store that box value and it's corresponding gain value.
        # Store boolean saying if second slope coefficient is negative.
        box_vs_gain[channel.channel].append(Data._make((
            _power_func(COUNT_CLOSE_TO_ZERO, *coeffs),
            channel.gain, coeffs[1] < 0)))

    gains = {}
    for channel, points in box_vs_gain.iteritems():
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
        save_path = os.path.normpath(os.path.join(
            wellp, ('{}.png').format(channel)))
        if plot:
            _create_plot(
                save_path, [p.box for p in points],
                [p.gain for p in points], coeffs, 'box-gain')
        gains[channel] = _power_func(255, *coeffs)

    return {WELL_NAME.format(img_attr.u, img_attr.v): gains}


def sanitize_gain(config, channel, gain):
    """Make sure all channels have a reasonable gain value."""
    objective = config[GAIN].get(OBJECTIVE)
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
    config = center.config
    fields_x = config.get(FIELDS_X, DEFAULT_FIELDS_X)
    fields_y = config.get(FIELDS_Y, DEFAULT_FIELDS_Y)
    for gain_well, channels in gain_dict.iteritems():
        for channel, gain in channels.iteritems():
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
                    well for well, settings in template.iteritems()
                    if settings[GAIN_FROM_WELL] == gain_well]
                for well in wells:
                    center.plate.set_gain(well, channel, gain)
                    center.plate.wells[well].set_fields(fields_x, fields_y)
            else:
                center.plate.set_gain(gain_well, channel, gain)
                center.plate.wells[gain_well].set_fields(fields_x, fields_y)


def save_gain(save_dir, saved_gains):
    """Save a csv file with gain values per image channel."""
    header = [WELL, GREEN, BLUE, YELLOW, RED]
    path = os.path.normpath(
        os.path.join(save_dir, 'output_gains.csv'))
    write_csv(path, saved_gains, header)


def get_com(center, job, job_list):
    """Get command."""
    config = center.config
    # Lists for storing command strings.
    com_list = []
    end_com_list = []
    # FIXME: CHECK GAINS AND RUN JOBS SMART  pylint: disable=fixme
    # Ie use one job for multiple wells where the gain is the same
    # or similar.
    for well in center.plate.wells.values():
        if well.img_ok or not well.channels:
            # Only get commands for wells that are not imaged ok and
            # wells that have channels with gain set.
            continue
        end_com = []
        com = get_gain_com([], well.channels, job_list)
        for field in well.fields.values():
            com.append(cam_com(
                job, well.U, well.V, field.X, field.Y, field.dX,
                field.dY))
            end_com = [
                CAM, WELL_NAME.format(well.U, well.V),
                JOB_ID.format(config[GAIN].get(FIRST_JOB, 2) + 2),
                FIELD_NAME.format(field.X, field.Y)]
        # Store the commands in lists.
        com_list.append(com)
        end_com_list.append(end_com)
    return com_list, end_com_list


def get_init_com(center, job, template=None):
    """Get command for gain analysis."""
    # pylint: disable=too-many-locals
    objective = center.config[GAIN].get(OBJECTIVE)
    fields_x = center.config.get(FIELDS_X, DEFAULT_FIELDS_X)
    fields_y = center.config.get(FIELDS_Y, DEFAULT_FIELDS_Y)
    wells = []
    if template:
        # Selected wells from template file.
        for well, row in template.iteritems():
            if 'true' in row[GAIN_SCAN]:
                wells.append(well)
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
    for well in sorted(wells):
        center.plate.set_well(well)
        center.plate.wells[well].set_fields(fields_x, fields_y)
        com = []
        for field in center.plate.wells[well].fields.values():
            if not field.gain_field:
                continue
            com.append(cam_com(
                job, center.plate.wells[well].U, center.plate.wells[well].V,
                field.X, field.Y, field.dX, field.dY))
            end_com = [
                CAM, well, JOB_ID.format(2),
                FIELD_NAME.format(field.X, field.Y)]
        com_list.append(com)
        end_com_list.append(end_com)

    # Join the list of lists of command lists into a list of a command
    # list if dry a objective is used.
    if objective == END_10X or objective == END_40X:
        com_list = [c for commands in com_list for c in commands]
        com_list = [com_list]
        end_com_list = [end_com_list[-1]]
    return com_list, end_com_list


def rename_imgs(imgp, f_job):
    """Rename image and return new name."""
    if attribute(imgp, 'E') == f_job:
        new_name = format_new_name(imgp)
    elif (attribute(imgp, 'E') == f_job + 1 and
          attribute(imgp, 'C') == 0):
        new_name = format_new_name(imgp, new_attr={'C': '01'})
    elif (attribute(imgp, 'E') == f_job + 1 and
          attribute(imgp, 'C') == 1):
        new_name = format_new_name(imgp, new_attr={'C': '02'})
    elif attribute(imgp, 'E') == f_job + 2:
        new_name = format_new_name(imgp, new_attr={'C': '03'})
    else:
        return None
    if os.path.exists(new_name):
        os.remove(new_name)
    os.rename(imgp, new_name)
    return new_name


def handle_imgs(path, job_id, f_job=2):
    """Handle acquired images, do renaming, make max projections."""
    # Get all image paths in well or field, depending on path and
    # job_id variable.
    imgs = get_imgs(path, search=JOB_ID.format(job_id))
    new_paths = []
    _LOGGER.info('Handling images...')
    for imgp in imgs:
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        new_name = rename_imgs(imgp, f_job)
        _LOGGER.debug('NEW NAME: %s', new_name)
        if new_name:
            new_paths.append(new_name)
    if not new_paths:
        return
    # Make a max proj per channel.
    projs = make_proj(new_paths)
    return projs


def handle_stage1(center, event):
    """Handle saved image during stage 1."""
    _LOGGER.info('Handling image during stage 1...')
    imgp = find_image_path(event.rel_path, center.config[IMAGING_DIR])
    if not imgp:
        return
    _LOGGER.debug('IMAGE PATH: %s', imgp)
    img_attr = attributes(imgp)
    # This means only ever one well at a time.
    if (FIELD_NAME.format(img_attr.x, img_attr.y) !=
            DEFAULT_LAST_FIELD_GAIN or
            img_attr.c != DEFAULT_LAST_SEQ_GAIN):
        return
    wellp = get_well(imgp)
    projs = handle_imgs(wellp, DEFAULT_JOB_ID_GAIN)
    if not projs:
        return
    gain_dict = calc_gain(center.config, imgp, projs)
    _LOGGER.debug('Gain dict: %s', gain_dict)
    if SAVED_GAINS not in center.data:
        center.data[SAVED_GAINS] = defaultdict(dict)
    center.data[SAVED_GAINS].update(gain_dict)
    _LOGGER.debug('%s: %s', SAVED_GAINS, center.data[SAVED_GAINS])
    save_gain(
        center.config[IMAGING_DIR], center.data[SAVED_GAINS])
    distribute_gain(
        center, gain_dict, template=center.data[GAIN].get(TEMPLATE))
    _LOGGER.debug('Plate: %s', center.plate)


def handle_stage2(center, event):
    """Handle saved image during stage 2."""
    _LOGGER.info('Handling image during stage 2...')
    imgp = find_image_path(event.rel_path, center.config[IMAGING_DIR])
    if not imgp:
        return
    img_attr = attributes(imgp)
    well = center.plate.wells.get(WELL_NAME.format(img_attr.u, img_attr.v))
    if not well:
        return
    field = well.fields.get(FIELD_NAME.format(img_attr.x, img_attr.y))
    if not field:
        return
    well.fields[FIELD_NAME.format(
        img_attr.x, img_attr.y)] = field._replace(
            img_ok=True)
    fieldp = get_field(imgp)
    handle_imgs(fieldp, attribute(imgp, 'E'), f_job=center.config[FIRST_JOB])


def stop(center):
    """Handle event that should stop the microscope."""
    for remove_listener in center.data[GAIN][LISTENERS]:
        remove_listener()
    reply = center.cam.stop_scan()
    _LOGGER.debug('STOP SCAN: %s', reply)
    begin = time.time()
    while not reply or SCAN_FINISHED not in reply[-1].values():
        reply = center.cam.receive()
        _LOGGER.debug('SCAN FINISHED reply: %s', reply)
        if time.time() - begin > 20.0:
            break
    time.sleep(1)  # Wait for it to come to complete stop.


def stop_end_stage1(center, event):
    """Handle event that should end stage1 after stop."""
    # pylint:disable=unused-argument
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
    center.data[GAIN][LISTENERS].append(center.call_saved(call))


def stop_mid_stage2(center, event):
    """Handle event that should continue with stage2 after stop."""
    # pylint:disable=unused-argument
    _LOGGER.info('Handling stop event during stage 2...')
    stop(center)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage2))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(center.call_saved(call))


def stop_end_stage2(center, event):
    """Handle event that should end stage2 after stop."""
    # pylint:disable=unused-argument
    _LOGGER.info('Handling stop event at end stage 2...')
    stop(center)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage1))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(center.call_saved(call))
