"""Leica microscope API specific modules."""
import logging
import socket
import threading
import time
from collections import deque
from functools import partial

from leicacam.cam import CAM, bytes_as_dict, tuples_as_bytes
from leicaexperiment import attribute, attribute_as_str

from camacq.api import (CONF_API, Api, CommandEvent, ImageEvent,
                        StartCommandEvent, StopCommandEvent)
from camacq.api.leica.helper import find_image_path, get_field, get_imgs
from camacq.const import (CAMACQ_STOP_EVENT, CONF_HOST, CONF_PORT, IMAGING_DIR,
                          JOB_ID)

_LOGGER = logging.getLogger(__name__)

CONF_LEICA = 'leica'
REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
SCAN_STARTED = 'scanstart'


def setup_package(center, config, add_child=None):
    """Set up Leica api package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    add_child : callable
        A function that registers the child with the parent package.
    """
    conf = config[CONF_API][CONF_LEICA]
    host = conf.get(CONF_HOST, 'localhost')
    port = conf.get(CONF_PORT, 8895)
    try:
        cam = CAM(host, port)
    except socket.error as exc:
        _LOGGER.error(
            'Connecting to server %s failed: %s', host, exc)
        return
    cam.delay = 0.2
    api = LeicaApi(center, cam)
    add_child(__name__, api)
    # Start thread that calls receive on the socket to the microscope
    api.start()

    def stop_thread(center, event):
        """Stop the thread."""
        api.stop_thread.set()

    center.bus.register(CAMACQ_STOP_EVENT, stop_thread)


class LeicaApi(Api, threading.Thread):
    """Represent the Leica API."""

    def __init__(self, center, client):
        """Set up the Leica API."""
        super(LeicaApi, self).__init__()
        self.center = center
        self.client = client
        self.stop_thread = threading.Event()
        self.queue = deque()

    # TODO: Check what events are reported by CAM server. pylint: disable=fixme
    # Make sure that all images get reported eventually.
    def receive(self, replies):
        """Receive replies from CAM server and fire an event per reply.

        Parameters
        ----------
        replies : list
            A list of replies from the CAM server.
        """
        # if reply check reply and call correct listener
        # parse reply and create Event
        # reply must be an iterable
        conf = self.center.config[CONF_API][CONF_LEICA]
        imaging_dir = conf.get(IMAGING_DIR, '')
        if not isinstance(replies, list):
            replies = [replies]
        for reply in replies:
            if not reply or not isinstance(reply, dict):
                continue
            if REL_IMAGE_PATH in reply:
                rel_path = reply[REL_IMAGE_PATH]
                image_path = find_image_path(rel_path, imaging_dir)
                field_path = get_field(image_path)
                image_paths = get_imgs(
                    field_path,
                    search=JOB_ID.format(attribute(image_path, 'E')))
                for path in image_paths:
                    self.center.bus.notify(LeicaImageEvent({'path': path}))
            elif SCAN_STARTED in list(reply.values()):
                self.center.bus.notify(
                    LeicaStartCommandEvent(reply))
            elif SCAN_FINISHED in list(reply.values()):
                self.center.bus.notify(
                    LeicaStopCommandEvent(reply))
            else:
                self.center.bus.notify(LeicaCommandEvent(reply))

    def send(self, command):
        """Send a command to the Leica API.

        Parameters
        ----------
        command : list of tuples or string
            The command to send.
        """
        if isinstance(command, str):
            command = bytes_as_dict(command.encode())
            command = list(command.items())
        cmd, value = command[0]  # use the first cmd and value to wait for
        self.add_job(self.client.send, command)
        self.add_job(partial(
            self.client.wait_for, cmd=cmd, value=value, timeout=0.2))

    def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        self.add_job(self.client.start_scan)

    def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        self.add_job(self.client.stop_scan)
        self.add_job(partial(
            self.client.wait_for, cmd='inf', value=SCAN_FINISHED, timeout=0.2))

    def run(self):
        """Thread loop that receive from the microscope socket."""
        while True:
            if self.stop_thread.is_set():
                break
            replies = self.run_job()
            if replies:
                self.receive(replies)
            if self.queue:
                continue
            replies = self.client.receive()
            self.receive(replies)
            time.sleep(0.050)  # Short sleep to not burn 100% CPU.

    def add_job(self, func, *args):
        """Add job to the queue.

        Parameters
        ----------
        func : callable
            A target function to call.
        args : tuple
            A tuple of optional arguments.
        """
        job = func, args
        self.queue.append(job)

    def run_job(self, job=None):
        """Run job either passed in or off the queue.

        Parameters
        ----------
        job : tuple
            An optional tuple of target function and arguments.

        Returns
        -------
        Any
            Return the return value of the target function call.
        """
        if job is None:
            if not self.queue:
                return None
            job = self.queue.popleft()
        func, args = job
        return func(*args)


# pylint: disable=too-few-public-methods
class LeicaCommandEvent(CommandEvent):
    """Leica CommandEvent class."""

    __slots__ = ()

    event_type = 'leica_command_event'

    @property
    def command(self):
        """Return the command string."""
        return tuples_as_bytes(list(self.data.items())).decode()


class LeicaStartCommandEvent(StartCommandEvent, LeicaCommandEvent):
    """Leica StartCommandEvent class."""

    __slots__ = ()

    event_type = 'leica_start_command_event'


class LeicaStopCommandEvent(StopCommandEvent, LeicaCommandEvent):
    """Leica StopCommandEvent class."""

    __slots__ = ()

    event_type = 'leica_stop_command_event'


class LeicaImageEvent(ImageEvent):
    """Leica ImageEvent class."""

    __slots__ = ()

    event_type = 'leica_image_event'

    @property
    def path(self):
        """:str: Return absolute path to the image."""
        return self.data.get('path', '')

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return attribute(self.path, 'U')

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return attribute(self.path, 'V')

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return attribute(self.path, 'X')

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return attribute(self.path, 'Y')

    @property
    def z_slice(self):
        """:int: Return z index of the image."""
        return attribute(self.path, 'Z')

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return attribute(self.path, 'C')

    @property
    def job_id(self):
        """:int: Return job id of the image."""
        return attribute(self.path, 'E')

    @property
    def plate_name(self):
        """:str: Return plate name of the image."""
        return attribute_as_str(self.path, 'S')
