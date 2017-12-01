"""Control the microscope."""
import logging
import socket
import sys
import time
from collections import deque
from functools import partial
from importlib import import_module

from matrixscreener.cam import CAM

from camacq.const import HOST, PORT
from camacq.plate import Plate

_LOGGER = logging.getLogger(__name__)
REL_IMAGE_PATH = 'relpath'


class Event(object):
    """Event class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data, event_type):
        """Set up the event."""
        self.center = center
        self.data = data
        self.event_type = event_type

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.data)


class CommandEvent(Event):
    """CommandEvent class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up command event."""
        super(CommandEvent, self).__init__(center, data, 'command_event')


class ImageEvent(Event):
    """ImageEvent class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up the image event."""
        super(ImageEvent, self).__init__(center, data, 'image_event')
        self.rel_path = data.get(REL_IMAGE_PATH, '')


class DummyEvent(object):  # pylint: disable=too-few-public-methods
    """DummyEvent class."""


def dummy_handler(event):  # pylint: disable=unused-argument
    """Handle dummy event."""
    pass


class EventBus(object):
    """EventBus class."""

    def __init__(self, center):
        """Set up instance."""
        self.center = center
        self._event = import_module('zope.event')
        self.handler = import_module('zope.event.classhandler')
        # Limitation in zope requires at least one item in registry to avoid
        # adding another dispatch function to the list of subscribers.
        self.handler.handler(DummyEvent, dummy_handler)

    def register(self, event_type, handler):
        """Register an event listener and return a function to remove it."""
        handler = partial(handler, self.center)
        self.handler.handler(event_type, handler)

        def remove():
            """Remove registered event handler."""
            self.handler.registry.pop(event_type, None)

        return remove

    def _clear(self):
        """Remove all registered listeners except dummy."""
        for listener in self.handler.registry:
            if isinstance(listener, DummyEvent):
                continue
            self.handler.registry.pop(listener, None)

    def notify(self, event):
        """Notify listenerns of event."""
        _LOGGER.debug(event)
        self._event.notify(event)


class ActionsRegistry(object):
    """ActionsRegistry class."""

    def __init__(self):
        """Set up instance."""
        self._actions = {}

    @property
    def actions(self):
        """Return a dict of dicts with all registered actions."""
        return self._actions

    def register(self, action_id, action_type, action_func):
        """Register an action."""
        if action_type not in self._actions:
            self._actions[action_type] = {}
        self._actions[action_type][action_id] = action_func


class Center(object):
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
        self.data = {}  # dict to store data from modules outside control
        self.do_now = deque()  # Functions to call asap.
        self.bus = EventBus(self)
        self.actions = ActionsRegistry()
        self.exit_code = None
        self.plate = Plate()

    def end(self, code):
        """Prepare app for exit."""
        _LOGGER.info('Stopping camacq')
        self.exit_code = code

    def start(self):
        """Run, send commands and receive replies.

        Register functions event bus style that are called on event.
        An event is a reply from the server.
        """
        try:
            _LOGGER.info('Starting camacq')
            if not self.do_now:
                _LOGGER.info('Nothing to do')
                self.end(0)
                return
            while True:
                if self.finished:
                    _LOGGER.info('Experiment finished!')
                    self.end(0)
                    break
                if not self.do_now:
                    self._receive()
                    time.sleep(0.02)  # Short sleep to not burn 100% CPU.
                    continue
                call = self.do_now.popleft()
                replies = self.call_saved(call)
                if replies:
                    self._receive(replies)
        except KeyboardInterrupt:
            self.end(0)

    @property
    def finished(self):
        """Return True if no real listeners are registered on the event bus."""
        return not any(
            listener for listener in self.bus.handler.registry
            if not isinstance(listener, DummyEvent))

    @staticmethod
    def call_saved(call):
        """Call a saved call of a tuple with func and args."""
        func = call[0]
        if len(call) > 1:
            args = call[1:]
        else:
            args = ()
        _LOGGER.debug('Calling: %s(%s)', func, args)
        return func(*args)

    def _receive(self, replies=None):
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
                self.bus.notify(ImageEvent(self, reply))
            else:
                self.bus.notify(CommandEvent(self, reply))
