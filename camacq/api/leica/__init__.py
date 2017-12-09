"""Leica microscope API specific modules."""
import json
import logging
import socket
import threading
import time
from collections import OrderedDict

from matrixscreener.cam import CAM

from camacq.api import Api
from camacq.api.leica.helper import find_image_path
from camacq.const import HOST, IMAGING_DIR, PORT
from camacq.control import (CommandEvent, ImageEvent, StartCommandEvent,
                            StopCommandEvent)

_LOGGER = logging.getLogger(__name__)

REL_IMAGE_PATH = 'relpath'
SCAN_FINISHED = 'scanfinished'
# FIXME: Check exactly what string is sent from the api. pylint: disable=fixme
SCAN_STARTED = 'startscan'


def setup_package(center, config, add_child=None):
    """Set up Leica api package."""
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
        self._center = center
        self.client = client
        self.stop_thread = threading.Event()

    def _receive(self, replies=None):
        """Receive replies from CAM server and notify an event."""
        if replies is None:
            replies = self.client.receive()
        if replies is None:
            return
        # if reply check reply and call or register correct listener
        # parse reply and create Event
        # reply must be an iterable
        for reply in replies:
            if REL_IMAGE_PATH in reply:
                self._center.bus.notify(LeicaImageEvent(self._center, reply))
            elif SCAN_STARTED in reply.items():
                self._center.bus.notify(
                    LeicaStartCommandEvent(self._center, reply))
            elif SCAN_FINISHED in reply.values():
                self._center.bus.notify(
                    LeicaStopCommandEvent(self._center, reply))
            else:
                self._center.bus.notify(LeicaCommandEvent(self._center, reply))

    def send(self, command=None):
        """Send a command to the Leica API.

        Parameters
        ----------
        command : str
            The command to send, should be a JSON string.
        """
        command = json.loads(command, object_pairs_hook=OrderedDict)
        replies = self.client.send(command.items())
        if replies:
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

    @property
    def command(self):
        """Return the JSON command string."""
        return json.dumps(self.data)


class LeicaStartCommandEvent(StartCommandEvent, LeicaCommandEvent):
    """Leica StartCommandEvent class."""


class LeicaStopCommandEvent(StopCommandEvent, LeicaCommandEvent):
    """Leica StopCommandEvent class."""


class LeicaImageEvent(ImageEvent):
    """Leica ImageEvent class."""

    @property
    def path(self):
        """Return the absolute path to the image."""
        rel_path = self.data.get(REL_IMAGE_PATH, '')
        return find_image_path(rel_path, self.center.config[IMAGING_DIR])
