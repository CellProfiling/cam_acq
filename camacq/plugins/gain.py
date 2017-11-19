"""Handle default gain feedback plugin."""
import logging
import os
import re
import subprocess
import sys
import time
from collections import defaultdict, deque

from jinja2 import Template
from matrixscreener.experiment import attribute, attributes, glob
from pkg_resources import resource_filename

from camacq.bootstrap import PACKAGE
from camacq.command import cam_com, gain_com
from camacq.const import (BLUE, DEFAULT_FIELDS_X, DEFAULT_FIELDS_Y, END_10X,
                          END_40X, END_63X, FIELD_NAME, FIELDS_X, FIELDS_Y,
                          FIRST_JOB, GAIN_ONLY, GREEN, IMAGING_DIR, INIT_GAIN,
                          INPUT_GAIN, JOB_ID, LAST_WELL, RED,
                          TEMPLATE_FILE, WELL, WELL_NAME, WELL_NAME_CHANNEL,
                          YELLOW)
from camacq.control import ImageEvent
from camacq.helper import (find_image_path, format_new_name, get_field,
                           get_imgs, get_well, read_csv, save_histogram,
                           send_com_and_start, write_csv)
from camacq.image import make_proj

_LOGGER = logging.getLogger(__name__)
DEFAULT_JOB_ID_GAIN = 2
DEFAULT_LAST_FIELD_GAIN = 'X01--Y01'
DEFAULT_LAST_SEQ_GAIN = 31
DEFAULT_LAST_WELL = 'U11--V07'
MAX_PROJS = 'maxprojs'
SAVED_GAINS = 'saved_gains'
SCAN_FINISHED = 'scanfinished'

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
GAIN_SCAN = 'gain_scan'
GAIN_FROM_WELL = 'gain_from_well'
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
OBJECTIVE = 'objective'
LISTENERS = 'listeners'
COMMANDS = 'commands'


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


def process_output(well, output, well_map):
    """Process output from the R script."""
    channels = output.split()
    for index, gain in enumerate(channels):
        well_map[well].update({CHANNELS[index]: gain})
    return well_map


def get_gain_com(commands, channels, job_list):
    """Return a list of command lists to set gain for all channels."""
    for channel, gain in channels.iteritems():
        job = job_list[JOB_MAP[channel]]
        detector = DETECTOR_MAP[channel]
        gain = str(gain.gain)
        commands.append(gain_com(exp=job, num=detector, value=gain))
    return commands


def calc_gain(config, bases, wells):
    """Run R scripts and calculate gain values for the wells."""
    # Get a unique set of filebases from the csv paths.
    objective = config[GAIN].get(OBJECTIVE)
    gain_dict = defaultdict(dict)
    filebases = sorted(set(bases))
    # Get a unique set of names of the experiment wells.
    fin_wells = sorted(set(wells))
    r_script = resource_filename(PACKAGE, 'data/gain.r')
    if objective == END_10X:
        init_gain = resource_filename(PACKAGE, 'data/10x_gain.csv')
    elif objective == END_40X:
        init_gain = resource_filename(PACKAGE, 'data/40x_gain.csv')
    elif objective == END_63X:
        init_gain = resource_filename(PACKAGE, 'data/63x_gain.csv')
    if config[GAIN].get(INIT_GAIN):
        init_gain = config[GAIN][INIT_GAIN]
    for fbase, well in zip(filebases, fin_wells):
        _LOGGER.info('WELL: %s', well)
        try:
            _LOGGER.info('Starting R...')
            r_output = subprocess.check_output([
                'Rscript', r_script, config.get(IMAGING_DIR), fbase,
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


def handle_imgs(path, imdir, job_id, f_job=2, img_save=True, histo_save=True):
    """Handle acquired images, do renaming, make max projections."""
    # pylint: disable=too-many-arguments
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
    if not new_paths or not img_save and not histo_save:
        return
    new_dir = os.path.normpath(os.path.join(imdir, MAX_PROJS))
    if img_save and not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if img_save:
        _LOGGER.info('Saving images...')
    if histo_save:
        _LOGGER.info('Calculating histograms...')
    # Make a max proj per channel.
    for c_id, proj in make_proj(new_paths).iteritems():
        if img_save:
            save_path = format_new_name(proj.path, root=new_dir,
                                        new_attr={'C': c_id})
            # Save meta data and image max proj.
            proj.save(save_path)
        if histo_save:
            img_attr = attributes(proj.path)
            save_path = os.path.normpath(os.path.join(
                imdir, (WELL_NAME_CHANNEL + '.ome.csv').format(
                    img_attr.u, img_attr.v, int(c_id))))
            save_histogram(save_path, proj)


def get_csvs(event):
    """Find correct csv files and get their base names."""
    # empty lists for keeping csv file base path names
    # and corresponding well names
    fbs = []
    wells = []
    imgp = find_image_path(event.rel_path, event.center.config[IMAGING_DIR])
    if not imgp:
        return fbs, wells
    _LOGGER.debug('IMAGE PATH: %s', imgp)
    img_attr = attributes(imgp)
    # This means only ever one well at a time.
    if (FIELD_NAME.format(img_attr.x, img_attr.y) ==
            DEFAULT_LAST_FIELD_GAIN and
            img_attr.c == DEFAULT_LAST_SEQ_GAIN):
        wellp = get_well(imgp)
        handle_imgs(wellp, wellp, DEFAULT_JOB_ID_GAIN, img_save=False)
        # get all CSVs in well at wellp
        csvs = glob(
            os.path.join(os.path.normpath(wellp), '*.ome.csv'))
        for csvp in csvs:
            csv_attr = attributes(csvp)
            # Get the filebase from the csv path.
            fbs.append(re.sub(r'C\d\d.+$', '', csvp))
            #  Get the well from the csv path.
            well_name = WELL_NAME.format(csv_attr.u, csv_attr.v)
            wells.append(well_name)
    return fbs, wells


def handle_stage1(center, event):
    """Handle saved image during stage 1."""
    _LOGGER.info('Handling image during stage 1...')
    bases, wells = get_csvs(event)
    if not bases:
        return
    gain_dict = calc_gain(center.config, bases, wells)
    if not gain_dict:
        return
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
    handle_imgs(
        fieldp, center.config[IMAGING_DIR], attribute(imgp, 'E'),
        f_job=center.config[FIRST_JOB], img_save=False, histo_save=False)


def stop(center, event):  # pylint: disable=unused-argument
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
    _LOGGER.info('Handling stop event at end stage 1...')
    stop(center, event)
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
    _LOGGER.info('Handling stop event during stage 2...')
    stop(center, event)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage2))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(center.call_saved(call))


def stop_end_stage2(center, event):
    """Handle event that should end stage2 after stop."""
    _LOGGER.info('Handling stop event at end stage 2...')
    stop(center, event)
    center.data[GAIN][LISTENERS].append(center.bus.register(
        ImageEvent, handle_stage1))
    if center.data[GAIN][COMMANDS]:
        call = center.data[GAIN][COMMANDS].popleft()
        center.data[GAIN][LISTENERS].append(center.call_saved(call))
