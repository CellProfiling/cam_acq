"""Control the microscope."""
import logging
import os
import re
import time
from collections import defaultdict, deque

import zope.event as eventbus
from matrixscreener.cam import CAM
from matrixscreener.experiment import attribute, attributes, glob

from camacq.command import camstart_com, del_com
from camacq.const import (END_10X, END_40X, END_63X, FIELD_NAME, GAIN_ONLY,
                          INPUT_GAIN, JOB_ID, WELL, WELL_NAME,
                          WELL_NAME_CHANNEL)
from camacq.gain import GainMap
from camacq.helper import (find_image_path, format_new_name, get_field,
                           get_imgs, get_well, read_csv, rename_imgs,
                           save_gain, save_histogram, send)
from camacq.image import make_proj

_LOGGER = logging.getLogger(__name__)

# #RFE:0 Assign job vars by config file, trello:UiavT7yP
# #RFE:10 Assign job vars by parsing the xml/lrp-files, trello:d7eWnJC5
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
MAX_PROJS = 'maxprojs'
DEFAULT_LAST_FIELD_GAIN = 'X01--Y01'
DEFAULT_LAST_SEQ_GAIN = 31
DEFAULT_JOB_ID_GAIN = 2
REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
STAGE1 = 'stage1'
STAGE2 = 'stage2'


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
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if img_save:
        _LOGGER.info('Saving images...')
    if histo_save:
        _LOGGER.info('Calculating histograms')
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


def handle_stage1(event):
    """Handle events during stage 1."""
    _LOGGER.info('Stage1')
    _LOGGER.debug('REPLY: %s', event.reply)
    csv_result = event.center.get_csvs(event.rel_path)
    # remove empty dict passed to calc_gain?
    gain_dict = event.center.gains.calc_gain(csv_result, defaultdict(dict))
    _LOGGER.debug('GAIN DICT: %s', gain_dict)
    event.center.saved_gains.update(gain_dict)
    if not event.center.saved_gains:
        return
    _LOGGER.debug('SAVED_GAINS: %s', event.center.saved_gains)
    save_gain(event.center.args.imaging_dir, event.center.saved_gains)
    event.center.gains.distribute_gain(gain_dict)


def handle_stage2(event):
    """Handle events during stage 2."""
    _LOGGER.info('Stage2')
    imgp = find_image_path(event.rel_path, event.center.args.imaging_dir)
    if not imgp:
        return
    img_attr = attributes(imgp)
    well = event.center.gains.wells.get(
        WELL_NAME.format(img_attr.u, img_attr.v))
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
        fieldp, event.center.args.imaging_dir, attribute(imgp, 'E'),
        f_job=event.center.args.first_job, img_save=False, histo_save=False)


def handle_stop(event):
    """Handle event that should stop the microscope."""
    # FIX: Set img_ok to True here instead of other place.
    event.center.subscribers.remove(handle_stop)  # Might not be reachable?
    if handle_stage1 in event.center.registry.get(ImageEvent, []):
        event.center.registry[ImageEvent].remove(handle_stage1)
        eventbus.classhandler.handler(ImageEvent, handle_stage2)
        com_data = event.center.gains.get_com(
            event.center.args.x_fields, event.center.args.y_fields)
        event.center.send_com(com_data['com'], com_data['end_com'])
    elif handle_stage2 in event.center.registry.get(ImageEvent, []):
        event.center.registry[ImageEvent].remove(handle_stage2)
        eventbus.classhandler.handler(ImageEvent, handle_stage1)
    reply = event.center.cam.stop_scan()
    _LOGGER.debug('STOP SCAN: %s', reply)
    begin = time.time()
    while not reply or SCAN_FINISHED not in reply[-1].values():
        reply = event.center.cam.receive()
        _LOGGER.debug('SCAN FINISHED reply: %s', reply)
        if time.time() - begin > 20.0:
            break
    time.sleep(1)  # Wait for it to come to complete stop.


def handler_factory(handler, test):
    """Create new handler that should call another handler if test is True."""
    def handle_logic(event):
        """Handle event that should do logistics."""
        if test(event):
            handler(event)
    return handle_logic


class Event(object):
    """Event class."""

    def __init__(self, center, reply):
        self.center = center
        self.reply = reply


class ImageEvent(Event):
    """ImageEvent class"""

    def __init__(self, center, reply):
        super(ImageEvent, self).__init__(center, reply)
        self.rel_path = reply.get(REL_IMAGE_PATH, '')


class Control(object):
    """Represent a control center for the microscope."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, args):
        """Set up instance."""
        self.args = args
        self.cam = CAM(self.args.host)
        self.cam.delay = 0.2
        # dicts of lists to store wells with gain values for
        # the four channels.
        self.saved_gains = defaultdict(dict)
        self.todo_deq = deque()
        # Use registry for specific recurring events.
        self.registry = eventbus.classhandler.registry
        # USe subscribers for functions that should be able to unsubscribe.
        self.subscribers = eventbus.subscribers
        # Fix lazy init
        self.gains = None
        self.exit_code = None

    def start(self):
        """Run, send commands and receive replies.

        Register functions event bus style that are called on event.
        An event is a reply from the server.
        """
        self.control()
        try:
            while True:
                # check for gain_ok in wells
                # get gain coms for not gain_ok in wells
                # add coms to deque in wells
                # add coms from all deques to main deque
                # send all coms from main deque
                if not self.todo_deq:
                    self.receive()
                    time.sleep(0.02)  # Short sleep to not burn 100% CPU.
                    continue
                func, args, kwargs = self.todo_deq.popleft()
                replies = func(*args, **kwargs)
                self.receive(replies)
            # break when finished
            _LOGGER.info('Experiment finished!')
        except KeyboardInterrupt:
            _LOGGER.info('Stopping camacq')
            self.exit_code = 0

    def receive(self, replies=None):
        """Receive replies from CAM server and notify an event."""
        if replies is None:
            replies = self.cam.receive()
        if replies is None:
            return
        # if reply check reply and call or register correct listener
        # parse reply and create Event
        # reply must be an iterable
        for reply in replies:
            eventbus.notify(ImageEvent(self, reply))

    def get_csvs(self, img_ref):
        """Find correct csv files and get their base names."""
        # empty lists for keeping csv file base path names
        # and corresponding well names
        fbs = []
        wells = []
        imgp = find_image_path(img_ref, self.args.imaging_dir)
        _LOGGER.debug('IMAGE PATH: %s', imgp)
        if not imgp:
            return {}
        img_attr = attributes(imgp)
        # This means only ever one well at a time.
        if (FIELD_NAME.format(img_attr.X, img_attr.Y) ==
                DEFAULT_LAST_FIELD_GAIN and
                img_attr.c == DEFAULT_LAST_SEQ_GAIN):
            if (self.args.end_63x or
                    WELL_NAME.format(img_attr.U, img_attr.V) ==
                    self.args.last_well):
                _LOGGER.debug('Stop scan after gain in well: %s',
                              self.cam.stop_scan())
            wellp = get_well(imgp)
            handle_imgs(wellp, wellp, DEFAULT_JOB_ID_GAIN, img_save=False)
            # get all CSVs in well at wellp
            csvs = glob(os.path.join(os.path.normpath(wellp), '*.ome.csv'))
            for csvp in csvs:
                csv_attr = attributes(csvp)
                # Get the filebase from the csv path.
                fbs.append(re.sub(r'C\d\d.+$', '', csvp))
                #  Get the well from the csv path.
                well_name = WELL_NAME.format(csv_attr.U, csv_attr.V)
                wells.append(well_name)
        return {'bases': fbs, 'wells': wells}

    def send_com(self, com_list, end_com_list):
        """Send commands to the CAM server."""
        com_deq = deque(zip(com_list, end_com_list))
        first_com, stop_data = com_deq.popleft()

        def stop_test(event):
            """Test if stop should be done."""
            if all(test in event.rel_path for test in stop_data):
                return True

        self.subscribers.append(handler_factory(handle_stop, stop_test))

        # Create listener for stop event and stage1 that should unsub
        # handle_stage1 and sub handle_stage2 and call send_com.
        # Create listener for stop event and stage2 that should unsub
        # handle_stage2 and sub handle_stage1 and popleft from com_deq and run
        # send_start_commands which will send new commands.

        def send_start_commands(com):
            """Send all commands needed to start microscope and run com."""
            # Send CAM list for the gain job to the server during stage1.
            # Send gain change command to server in the four channels
            # during stage2.
            # Send CAM list for the experiment jobs to server (stage2).
            _LOGGER.debug('Delete list: %s', del_com())
            _LOGGER.debug('Delete list reply: %s', self.cam.send(del_com()))
            time.sleep(2)
            send(self.cam, com)
            time.sleep(2)
            # Start scan.
            _LOGGER.debug('Start scan: %s', self.cam.start_scan())
            time.sleep(7)  # Wait for it to change objective and start.
            # Start CAM scan.
            _LOGGER.debug('Start CAM scan: %s', camstart_com())
            _LOGGER.debug('Start CAM scan reply: %s',
                          self.cam.send(camstart_com()))
            _LOGGER.info('Waiting for images...')

        # Append a tuple with function, args (tuple) and kwargs (dict).
        self.todo_deq.append((send_start_commands, (first_com, )))

    def control(self):
        """Control the flow."""
        # Booleans etc to control flow.
        stage1 = STAGE1_DEFAULT
        stage2 = STAGE2_DEFAULT
        gain_dict = defaultdict(dict)
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
            if getattr(self.args, attr, None):
                stage1 = settings.get(STAGE1, stage1)
                stage2 = settings.get(STAGE2, stage2) if not \
                    self.args.gain_only else flow_map[GAIN_ONLY][STAGE2]
                if JOB_INFO in settings:
                    job_info = settings[JOB_INFO]
                if INPUT_GAIN in attr:
                    gain_dict = read_csv(self.args.input_gain, WELL)

        # make GainMap object, fix lazy init later
        self.gains = GainMap(self.args, job_info)

        if self.args.input_gain:
            self.gains.distribute_gain(gain_dict)
            com_data = self.gains.get_com(
                self.args.x_fields, self.args.y_fields)
        else:
            com_data = self.gains.get_init_com()

        if stage1:
            eventbus.classhandler.handler(ImageEvent, handle_stage1)
        elif stage2:
            eventbus.classhandler.handler(ImageEvent, handle_stage2)

        if stage1 or stage2:
            self.send_com(com_data['com'], com_data['end_com'])
