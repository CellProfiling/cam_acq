"""Control the microscope."""
import logging
import time
from functools import partial
from importlib import import_module

from camacq.plate import Plate

_LOGGER = logging.getLogger(__name__)


class Event(object):
    """A base event class."""

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up the event."""
        self.center = center
        self.data = data
        self.event_type = 'base_event'

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.data)


class CommandEvent(Event):
    """An event received from the API.

    Notify with this event when a command is received via API.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up command event."""
        super(CommandEvent, self).__init__(center, data)
        self.event_type = 'command_event'

    @property
    def command(self):
        """Return the JSON command string."""
        return None


class StartCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging starts via API.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up start command event."""
        super(StartCommandEvent, self).__init__(center, data)
        self.event_type = 'start_command_event'


class StopCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging stops via API.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up stop command event."""
        super(StopCommandEvent, self).__init__(center, data)
        self.event_type = 'stop_command_event'


class ImageEvent(Event):
    """An event received from the API.

    Notify with this event when an image is saved via API.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, center, data):
        """Set up the image event."""
        super(ImageEvent, self).__init__(center, data)
        self.event_type = 'image_event'

    @property
    def path(self):
        """Return the absolute path to the image."""
        return None


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
        """Register an event listener and return a function to remove it.

        An event is a message from the microscope API.
        """
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
        """Notify listeners of event."""
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

    def register(self, package, action_id, action_func):
        """Register an action.

        Register actions per package, ie api, plugins etc.
        """
        if package not in self._actions:
            self._actions[package] = {}
        self._actions[package][action_id] = action_func

    def call(self, package, action_id, **kwargs):
        """Call an action with optional kwargs."""
        if (package not in self._actions or
                action_id not in self._actions[package]):
            _LOGGER.error(
                'No action registered for package %s or action id %s',
                package, action_id)
            return
        action_func = self._actions[package][action_id]
        action_func(action_id=action_id, **kwargs)


class Center(object):
    """Represent a control center for the microscope."""

    def __init__(self, config):
        """Set up instance."""
        self.config = config
        self.data = {}  # dict to store data from modules outside control
        self.bus = EventBus(self)
        self.actions = ActionsRegistry()
        self.exit_code = None
        self.plate = Plate()
        self.threads = []

    def end(self, code):
        """Prepare app for exit."""
        _LOGGER.info('Stopping camacq')
        self.exit_code = code
        for thread in self.threads:
            thread.stop_thread.set()
            thread.join(30)

    def start(self):
        """Start the app."""
        try:
            _LOGGER.info('Starting camacq')
            while True:
                if self.finished:
                    _LOGGER.info('Experiment finished!')
                    self.end(0)
                    break
                time.sleep(1)  # Short sleep to not burn 100% CPU.
        except KeyboardInterrupt:
            self.end(0)

    @property
    def finished(self):
        """Return True if no real listeners are registered on the event bus."""
        return not any(
            listener for listener in self.bus.handler.registry
            if not isinstance(listener, DummyEvent))
