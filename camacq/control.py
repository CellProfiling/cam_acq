"""Control the microscope."""
import logging
import socket
import sys
import time
from collections import defaultdict, deque

import zope.event as eventbus
import zope.event.classhandler as event_handler
from matrixscreener.cam import CAM
from matrixscreener.experiment import attribute, attributes

from camacq.command import camstart_com, del_com
from camacq.const import (END_10X, END_40X, END_63X, FIELD_NAME, FIELDS_X,
                          FIELDS_Y, FIRST_JOB, GAIN_ONLY, HOST, IMAGING_DIR,
                          INPUT_GAIN, LAST_FIELD, OBJECTIVE, PORT, WELL,
                          WELL_NAME)
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
    _LOGGER.info('Handling image event during stage 1...')
    bases, wells = get_csvs(event)
    if not bases:
        return
    gain_dict = event.center.gains.calc_gain(bases, wells)
    if not gain_dict:
        return
    _LOGGER.debug('GAIN DICT: %s', gain_dict)
    event.center.saved_gains.update(gain_dict)
    _LOGGER.debug('SAVED_GAINS: %s', event.center.saved_gains)
    save_gain(event.center.config[IMAGING_DIR], event.center.saved_gains)
    event.center.gains.distribute_gain(gain_dict)
    _LOGGER.debug('WELLMAP: %s', event.center.gains)


def handle_stage2(event):
    """Handle events during stage 2."""
    _LOGGER.info('Handling image event during stage 2...')
    imgp = find_image_path(event.rel_path, event.center.config[IMAGING_DIR])
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
        fieldp, event.center.config[IMAGING_DIR], attribute(imgp, 'E'),
        f_job=event.center.config[FIRST_JOB], img_save=False,
        histo_save=False)


def handle_stop(event):
    """Handle event that should stop the microscope."""
    # Limitation in zope requires at least one item in registry to avoid
    # adding another dispatch function to the list of subscribers.
    event.center.registry[ImageEvent] = []
    reply = event.center.cam.stop_scan()
    _LOGGER.debug('STOP SCAN: %s', reply)
    begin = time.time()
    while not reply or SCAN_FINISHED not in reply[-1].values():
        reply = event.center.cam.receive()
        _LOGGER.debug('SCAN FINISHED reply: %s', reply)
        if time.time() - begin > 20.0:
            break
    time.sleep(1)  # Wait for it to come to complete stop.


def handle_stop_end_stage1(event):
    """Handle event that should end stage1 after stop."""
    _LOGGER.info('Handling stop event at end stage 1...')
    handle_stop(event)
    event_handler.handler(ImageEvent, handle_stage2)
    com_data = event.center.gains.get_com()
    todo = [
        event.center.create_job(
            event.center.send_com, (com, end_com, handle_stop_mid_stage2))
        for com, end_com in zip(com_data['com'], com_data['end_com'])]
    todo.pop()
    event.center.do_later.extendleft([event.center.create_job(
        event.center.send_com,
        (com_data['com'][-1], com_data['end_com'][-1],
         handle_stop_end_stage2))])
    event.center.do_later.extendleft(reversed(todo))
    event.center.do_now.append(event.center.do_later.popleft())


def handle_stop_mid_stage2(event):
    """Handle event that should continue with stage2 after stop."""
    _LOGGER.info('Handling stop event during stage 2...')
    handle_stop(event)
    event_handler.handler(ImageEvent, handle_stage2)
    if event.center.do_later:
        event.center.do_now.append(event.center.do_later.popleft())


def handle_stop_end_stage2(event):
    """Handle event that should end stage2 after stop."""
    _LOGGER.info('Handling stop event at end stage 2...')
    handle_stop(event)
    event_handler.handler(ImageEvent, handle_stage1)
    if event.center.do_later:
        event.center.do_now.append(event.center.do_later.popleft())
    imgp = find_image_path(event.rel_path, event.center.config[IMAGING_DIR])
    if not imgp:
        return
    if all(well.img_ok for well in event.center.gains.wells.values()):
        event.center.finished = True


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

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.reply)


class CommandEvent(Event):
    """CommandEvent class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, reply):
        """Set up command event."""
        super(CommandEvent, self).__init__(center, reply)


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

    def __init__(self, config):
        """Set up instance."""
        self.config = config
        host = self.config.get(HOST, 'localhost')
        try:
            self.cam = CAM(
                host, self.config.get(PORT, 8895))
        except socket.error as exc:
            _LOGGER.error(
                'Connecting to server %s failed: %s', host, exc)
            sys.exit(1)
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

    def end(self, code):
        """Prepare app for exit."""
        _LOGGER.info('Stopping camacq')
        self.exit_code = code

    def start(self):
        """Run, send commands and receive replies.

        Register functions event bus style that are called on event.
        An event is a reply from the server.
        """
        _LOGGER.info('Starting camacq')
        self.control()
        if not self.do_now:
            _LOGGER.info('Nothing to do')
            self.end(0)
            return
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
            self.end(0)

    @staticmethod
    def notify(event):
        """Notify subscribers of event."""
        _LOGGER.debug(event)
        eventbus.notify(event)

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
            if REL_IMAGE_PATH in reply:
                self.notify(ImageEvent(self, reply))
            else:
                self.notify(CommandEvent(self, reply))

    @staticmethod
    def create_job(func, args=None, kwargs=None):
        """Add a function to a deque.

        Append the function 'func', a tuple of arguments 'args' and a dict
        of keyword arguments 'kwargs', as a tuple to the deque.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        return (func, args, kwargs)

    def send_com(self, commands, stop_data, handler):
        """Add commands to outgoing queue for the CAM server."""
        def stop_test(event):
            """Test if stop should be done."""
            if all(test in event.rel_path for test in stop_data):
                return True

        event_handler.handler(ImageEvent, handler_factory(handler, stop_test))

        def send_start_commands(coms):
            """Send all commands needed to start microscope and run com."""
            self.do_now.append(self.create_job(self.cam.send, (del_com(), )))
            self.do_now.append(self.create_job(time.sleep, (2, )))
            self.do_now.append(self.create_job(send, (self.cam, coms)))
            self.do_now.append(self.create_job(time.sleep, (2, )))
            self.do_now.append(self.create_job(self.cam.start_scan))
            # Wait for it to change objective and start.
            self.do_now.append(self.create_job(time.sleep, (7, )))
            self.do_now.append(self.create_job(
                self.cam.send, (camstart_com(), )))

        # Append a tuple with function, args (tuple) and kwargs (dict).
        self.do_now.append(self.create_job(send_start_commands, (commands, )))

    def control(self):
        """Control the flow."""
        # Booleans etc to control flow.
        stage1 = STAGE1_DEFAULT
        stage2 = STAGE2_DEFAULT
        gain_dict = defaultdict(dict)
        flow_map = {
            OBJECTIVE: {
                END_10X: {
                    JOB_INFO: (JOB_10X, PATTERN_G_10X, PATTERN_10X)},
                END_40X: {
                    JOB_INFO: (JOB_40X, PATTERN_G_40X, PATTERN_40X)},
                END_63X: {
                    JOB_INFO: (JOB_63X, PATTERN_G_63X, PATTERN_63X)},
            },
            GAIN_ONLY: {
                STAGE2: False,
            },
            INPUT_GAIN: {
                STAGE1: False,
            },
        }
        for attr, settings in flow_map.iteritems():
            if self.config.get(attr):
                stage1 = settings.get(STAGE1, stage1)
                stage2 = settings.get(STAGE2, stage2) if not \
                    self.config.get(GAIN_ONLY) else flow_map[GAIN_ONLY][STAGE2]
                if self.config[attr] in settings:
                    job_info = settings[self.config[attr]][JOB_INFO]
                if INPUT_GAIN == attr:
                    gain_dict = read_csv(self.config[INPUT_GAIN], WELL)

        self.config[LAST_FIELD] = FIELD_NAME.format(
            self.config.get(FIELDS_X, 2) - 1, self.config.get(FIELDS_Y, 2) - 1)

        # make GainMap object, fix lazy init later
        self.gains = GainMap(self.config, job_info)

        if self.config.get(INPUT_GAIN):
            self.gains.distribute_gain(gain_dict)
            com_data = self.gains.get_com()
        else:
            com_data = self.gains.get_init_com()

        if stage1:
            event_handler.handler(ImageEvent, handle_stage1)
        elif stage2:
            event_handler.handler(ImageEvent, handle_stage2)

        if stage1 or stage2:
            for commands, end_com in zip(com_data['com'], com_data['end_com']):
                self.do_later.append(self.create_job(
                    self.send_com, (
                        commands, end_com, handle_stop_end_stage1)))
            self.do_now.append(self.do_later.popleft())
