"""Control the microscope."""
import logging
import time

from camacq.event import CamAcqStartEvent, CamAcqStopEvent, EventBus
from camacq.sample import Sample

_LOGGER = logging.getLogger(__name__)


class ActionsRegistry(object):
    """Manage all registered actions."""

    def __init__(self):
        """Set up instance."""
        self._actions = {}

    @property
    def actions(self):
        """:dict: Return dict of dicts with all registered actions."""
        return self._actions

    def register(self, module, action_id, action_func):
        """Register an action.

        Register actions per module.

        Parameters
        ----------
        module : str
            The name of the module to register the action under.
        action_id : str
            The id of the action to register.
        action_func : callable
            The function that should be called for the action.
        """
        if module not in self._actions:
            self._actions[module] = {}
        self._actions[module][action_id] = action_func

    def call(self, module, action_id, **kwargs):
        """Call an action with optional kwargs.

        Parameters
        ----------
        module : str
            The name of the module where the action is registered.
        action_id : str
            The id of the action to call.
        **kwargs
            Arbitrary keyword arguments. These will be passed to the action
            function when an action is called.
        """
        if (module not in self._actions or
                action_id not in self._actions[module]):
            _LOGGER.error(
                'No action registered for module %s or action id %s',
                module, action_id)
            return
        action_func = self._actions[module][action_id]
        action_func(action_id=action_id, **kwargs)


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
    threads : list
        Return a list of child threads for the app.
    """

    def __init__(self, config):
        """Set up instance."""
        self.config = config
        self.bus = EventBus(self)
        self.sample = Sample(self.bus)
        self.actions = ActionsRegistry()
        self.data = {}
        self.exit_code = 0
        self.threads = []

    @property
    def finished(self):
        """:bool: Return True if handlers are registered on the bus."""
        return not self.bus.handlers

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
        for thread in self.threads:
            thread.stop_thread.set()
            thread.join(30)

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
