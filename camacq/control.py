"""Control the microscope."""
import logging
import time
from collections import defaultdict, deque

import zope.event as eventbus
import zope.event.classhandler as event_handler
from matrixscreener.cam import CAM
from matrixscreener.experiment import attribute, attributes

from camacq.command import camstart_com, del_com
from camacq.const import (END_10X, END_40X, END_63X, FIELD_NAME, GAIN_ONLY,
                          INPUT_GAIN, WELL, WELL_NAME)
from camacq.gain import GainMap
from camacq.helper import (find_image_path, get_csvs, get_field, handle_imgs,
                           read_csv, save_gain, send)

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
REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
STAGE1 = 'stage1'
STAGE2 = 'stage2'


def handle_stage1(event):
    """Handle events during stage 1."""
    _LOGGER.info('Stage1')
    _LOGGER.debug('REPLY: %s', event.reply)
    csv_result = get_csvs(event)
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
    event.center.subscribers.remove(handle_stop)  # Might not be reachable?
    reply = event.center.cam.stop_scan()
    _LOGGER.debug('STOP SCAN: %s', reply)
    begin = time.time()
    while not reply or SCAN_FINISHED not in reply[-1].values():
        reply = event.center.cam.receive()
        _LOGGER.debug('SCAN FINISHED reply: %s', reply)
        if time.time() - begin > 20.0:
            break
    time.sleep(1)  # Wait for it to come to complete stop.
    imgp = find_image_path(event.rel_path, event.center.args.imaging_dir)
    if not imgp:
        return
    img_attr = attributes(imgp)
    if (WELL_NAME.format(img_attr.U, img_attr.V) ==
            event.center.args.last_well and
            FIELD_NAME.format(img_attr.X, img_attr.Y) ==
            event.center.last_field):
        event.center.finished = True


def handle_stop_end_stage1(event):
    """Handle event that should end stage1 after stop."""
    handle_stop(event)
    if handle_stage1 in event.center.registry.get(ImageEvent, []):
        event.center.registry[ImageEvent].remove(handle_stage1)
    event_handler.handler(ImageEvent, handle_stage2)
    com_data = event.center.gains.get_com(
        event.center.args.x_fields, event.center.args.y_fields)
    todo = deque(
        (event.center.send_com, (com, end_com, handle_stop_mid_stage2))
        for com, end_com in zip(com_data['com'], com_data['end_com']))
    todo.pop()
    todo.append((
        event.center.send_com,
        (com_data['com'][-1], com_data['end_com'][-1],
         handle_stop_end_stage2)))
    event.center.do_later = todo.extend(event.center.do_later)
    event.center.do_now.append(event.center.do_later.popleft())


def handle_stop_mid_stage2(event):
    """Handle event that should continue with stage2 after stop."""
    handle_stop(event)
    if handle_stage2 not in event.center.registry.get(ImageEvent, []):
        event_handler.handler(ImageEvent, handle_stage2)
    if event.center.do_later:
        event.center.do_now.append(event.center.do_later.popleft())


def handle_stop_end_stage2(event):
    """Handle event that should end stage2 after stop."""
    handle_stop(event)
    if handle_stage2 in event.center.registry.get(ImageEvent, []):
        event.center.registry[ImageEvent].remove(handle_stage2)
    event_handler.handler(ImageEvent, handle_stage1)
    if event.center.do_later:
        event.center.do_now.append(event.center.do_later.popleft())


def handler_factory(handler, test):
    """Create new handler that should call another handler if test is True."""
    def handle_logic(event):
        """Forward event to handler if test is True."""
        if test(event):
            handler(event)
    return handle_logic


class Event(object):
    """Event class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, reply):
        """Set up the event."""
        self.center = center
        self.reply = reply


class ImageEvent(Event):
    """ImageEvent class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, reply):
        """Set up the image event."""
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
        self.do_now = deque()  # Functions to call asap.
        self.do_later = deque()  # Functions to call at specific events.
        # Use registry for specific recurring events.
        self.registry = event_handler.registry
        # Use subscribers for functions that should be able to unsubscribe.
        self.subscribers = eventbus.subscribers
        # Fix lazy init
        self.gains = None
        self.exit_code = None
        self.finished = False

    def start(self):
        """Run, send commands and receive replies.

        Register functions event bus style that are called on event.
        An event is a reply from the server.
        """
        self.control()
        try:
            while True:
                if self.finished:
                    _LOGGER.info('Experiment finished!')
                    break
                if not self.do_now:
                    self.receive()
                    time.sleep(0.02)  # Short sleep to not burn 100% CPU.
                    continue
                func, args, kwargs = self.do_now.popleft()
                _LOGGER.debug('Calling: %s(%s, %s)', func, args, kwargs)
                replies = func(*args, **kwargs)
                if replies:
                    self.receive(replies)
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

    def fill_queue(self, func, args=None, kwargs=None, queue=None):
        """Add a function to a deque.

        Append the function 'func', a tuple of arguments 'args' and a dict
        of keyword arguments 'kwargs', as a tuple to the deque.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        if queue is None:
            queue = self.do_now
        queue.append((func, args, kwargs))

    def send_com(self, commands, stop_data, handler):
        """Add commands to outgoing queue for the CAM server."""
        def stop_test(event):
            """Test if stop should be done."""
            if all(test in event.rel_path for test in stop_data):
                return True

        self.subscribers.append(handler_factory(handler, stop_test))

        def send_start_commands(coms):
            """Send all commands needed to start microscope and run com."""
            self.fill_queue(self.cam.send, (del_com(), ))
            self.fill_queue(time.sleep, (2, ))
            self.fill_queue(send, (self.cam, coms))
            self.fill_queue(time.sleep, (2, ))
            self.fill_queue(self.cam.start_scan)
            # Wait for it to change objective and start.
            self.fill_queue(time.sleep, (7, ))
            self.fill_queue(self.cam.send, (camstart_com(), ))

        # Append a tuple with function, args (tuple) and kwargs (dict).
        self.fill_queue(send_start_commands, (commands, ))

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
            event_handler.handler(ImageEvent, handle_stage1)
        elif stage2:
            event_handler.handler(ImageEvent, handle_stage2)

        if stage1 or stage2:
            for commands, end_com in zip(com_data['com'], com_data['end_com']):
                self.fill_queue(
                    self.send_com, (commands, end_com, handle_stop_end_stage1),
                    queue=self.do_later)
            self.do_now.append(self.do_later.popleft())
