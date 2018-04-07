"""Leica microscope API specific modules."""
import logging
import socket
import threading
import time

from leicacam.cam import CAM, bytes_as_dict, tuples_as_bytes
from leicaexperiment import attribute, attribute_as_str

from camacq.api import (Api, CommandEvent, ImageEvent, StartCommandEvent,
                        StopCommandEvent)
from camacq.api.leica.helper import find_image_path, get_field, get_imgs
from camacq.const import HOST, IMAGING_DIR, JOB_ID, PORT

_LOGGER = logging.getLogger(__name__)

REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
# FIXME: Check exactly what string is sent from the api. pylint: disable=fixme
SCAN_STARTED = 'startscan'


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
    host = config.get(HOST, 'localhost')
    try:
        cam = CAM(
            host, config.get(PORT, 8895))
    except socket.error as exc:
        _LOGGER.error(
            'Connecting to server %s failed: %s', host, exc)
        return
    cam.delay = 0.2
    api = LeicaApi(center, cam)
    add_child(__name__, api)
    # Start thread that calls receive on the socket to the microscope
    center.threads.append(api)
    api.start()


class LeicaApi(Api, threading.Thread):
    """Represent the Leica API."""

    def __init__(self, center, client):
        """Set up the Leica API."""
        super(LeicaApi, self).__init__()
        self.center = center
        self.client = client
        self.stop_thread = threading.Event()

    # TODO: Check what events are reported by CAM server. pylint: disable=fixme
    # Make sure that all images get reported eventually.
    def _receive(self, replies=None):
        """Receive replies from CAM server and fire an event per reply.

        Parameters
        ----------
        replies : list
            A list of replies from the CAM server.
        """
        if replies is None:
            replies = self.client.receive()
        # if reply check reply and call or register correct listener
        # parse reply and create Event
        # reply must be an iterable
        for reply in replies:
            if not reply:
                continue
            if REL_IMAGE_PATH in reply:
                rel_path = reply[REL_IMAGE_PATH]
                image_path = find_image_path(
                    rel_path, self.center.config[IMAGING_DIR])
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
        self.client.send(command)
        replies = [self.client.wait_for(cmd=cmd, value=value, timeout=0.3)]
        self._receive(replies)

    def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        replies = [self.client.start_scan()]
        self._receive(replies)

    def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        replies = [self.client.stop_scan()]
        self._receive(replies)

    def run(self):
        """Thread loop that receive from the microscope socket."""
        while True:
            if self.stop_thread.is_set():
                break
            self._receive()
            time.sleep(0.020)  # Short sleep to not burn 100% CPU.


# pylint: disable=too-few-public-methods
class LeicaCommandEvent(CommandEvent):
    """Leica CommandEvent class."""

    __slots__ = ()

    @property
    def command(self):
        """Return the command string."""
        return tuples_as_bytes(list(self.data.items())).decode()


class LeicaStartCommandEvent(StartCommandEvent, LeicaCommandEvent):
    """Leica StartCommandEvent class."""

    __slots__ = ()


class LeicaStopCommandEvent(StopCommandEvent, LeicaCommandEvent):
    """Leica StopCommandEvent class."""

    __slots__ = ()


class LeicaImageEvent(ImageEvent):
    """Leica ImageEvent class."""

    __slots__ = ()

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
