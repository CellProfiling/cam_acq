"""Control the microscope."""
import logging
import time
from builtins import object  # pylint: disable=redefined-builtin
from collections import namedtuple

import voluptuous as vol
from future import standard_library

from camacq.event import Event, EventBus
from camacq.const import CAMACQ_START_EVENT, CAMACQ_STOP_EVENT
from camacq.sample import Sample

standard_library.install_aliases()

_LOGGER = logging.getLogger(__name__)


Action = namedtuple('Action', 'func, schema')


class ActionsRegistry(object):
    """Manage all registered actions."""

    def __init__(self):
        """Set up instance."""
        self._actions = {}

    @property
    def actions(self):
        """:dict: Return dict of dicts with all registered actions."""
        return self._actions

    def register(self, action_type, action_id, action_func, schema):
        """Register an action.

        Register actions per module.

        Parameters
        ----------
        action_type : str
            The name of the action_type to register the action under.
        action_id : str
            The id of the action to register.
        action_func : callable
            The function that should be called for the action.
        action_func : voluptuous schema
            The voluptuous schema that should validate the parameters
            of the action call.
        """
        if action_type not in self._actions:
            self._actions[action_type] = {}
        _LOGGER.info(
            'Registering action %s.%s', action_type, action_id)
        self._actions[action_type][action_id] = Action(action_func, schema)

    def call(self, action_type, action_id, **kwargs):
        """Call an action with optional kwargs.

        Parameters
        ----------
        action_type : str
            The name of the module where the action is registered.
        action_id : str
            The id of the action to call.
        **kwargs
            Arbitrary keyword arguments. These will be passed to the action
            function when an action is called.
        """
        if (action_type not in self._actions or
                action_id not in self._actions[action_type]):
            _LOGGER.error(
                'No action registered for type %s or id %s',
                action_type, action_id)
            return
        action = self._actions[action_type][action_id]
        try:
            kwargs = action.schema(kwargs)
        except vol.Invalid as exc:
            _LOGGER.error('Invalid action call parameters: %s', exc)
            return
        _LOGGER.info(
            'Calling action %s.%s: %s', action_type, action_id, kwargs)
        action.func(action_id=action_id, **kwargs)


class Center(object):
    """Represent a control center for the microscope.

    Parameters
    ----------
    config : dict
        The config dict.

    Attributes
    ----------
    config : dict
        Return the config dict.
    bus : EventBus instance
        Return the EventBus instance.
    sample : Sample instance
        Return the Sample instance.
    actions : ActionsRegistry instance
        Return the ActionsRegistry instance.
    data : dict
        Return dict that stores data from other modules than control.
    exit_code : int
        Return the exit code for the app.
    """

    def __init__(self, config):
        """Set up instance."""
        self.config = config
        self.bus = EventBus(self)
        self.sample = Sample(self.bus)
        self.actions = ActionsRegistry()
        self.data = {}
        self.exit_code = 0

    def __repr__(self):
        """Return the representation."""
        return "<Center: config: {}>".format(self.config)

    @property
    def finished(self):
        """:bool: Return True if nothing is registered on the bus."""
        return not self.bus.event_types

    def end(self, code):
        """Prepare app for exit.

        Parameters
        ----------
        code : int
            Exit code to return when the app exits.
        """
        _LOGGER.info('Stopping camacq')
        self.bus.notify(CamAcqStopEvent({'exit_code': code}))
        self.exit_code = code

    def start(self):
        """Start the app."""
        try:
            _LOGGER.info('Starting camacq')
            self.bus.notify(CamAcqStartEvent())
            while True:
                if self.finished:
                    _LOGGER.info('Experiment finished!')
                    self.end(0)
                    break
                time.sleep(1)  # Short sleep to not burn 100% CPU.
        except KeyboardInterrupt:
            self.end(0)


# pylint: disable=too-few-public-methods
class CamAcqStartEvent(Event):
    """An event fired when camacq has started."""

    __slots__ = ()

    event_type = CAMACQ_START_EVENT


class CamAcqStopEvent(Event):
    """An event fired when camacq is about to stop."""

    __slots__ = ()

    event_type = CAMACQ_STOP_EVENT

    @property
    def exit_code(self):
        """:int: Return the plate instance of the event."""
        return self.data.get('exit_code')
