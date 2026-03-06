"""Control the microscope."""

import asyncio
import logging

from async_timeout import timeout as async_timeout
import voluptuous as vol

from camacq.event import Event, EventBus
from camacq.exceptions import CamAcqError, MissingActionError, MissingActionTypeError
from camacq.const import ACTION_TIMEOUT, CAMACQ_START_EVENT, CAMACQ_STOP_EVENT
from camacq.helper import register_signals
from camacq.plugins.sample import Samples
from camacq.util import dotdict

_LOGGER = logging.getLogger(__name__)


class Center:
    """Represent a control center for the microscope.

    Parameters
    ----------
    loop : asyncio.EventLoop
        The event loop.

    Attributes
    ----------
    loop : asyncio.EventLoop
        Return the event loop.
    bus : EventBus instance
        Return the EventBus instance.
    samples : Samples instance
        Return the Samples instance that holds all the Sample instances.
    actions : ActionsRegistry instance
        Return the ActionsRegistry instance.
    data : dict
        Return dict that stores data from other modules than control.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, loop=None):
        """Set up instance."""
        self.loop = loop or asyncio.get_event_loop()
        self.loop.set_exception_handler(loop_exception_handler)
        self.bus = EventBus(self)
        self.actions = ActionsRegistry(self)
        self.samples = Samples()
        self.data = {}
        self._exit_code = 0
        self._stopped = None
        self._pending_tasks = []
        self._track_tasks = False

    def __repr__(self):
        """Return the representation."""
        return "<Center>"

    async def end(self, code):
        """Prepare app for exit.

        Parameters
        ----------
        code : int
            Exit code to return when the app exits.
        """
        _LOGGER.info("Stopping camacq")
        self._track_tasks = True
        await self.bus.notify(CamAcqStopEvent({"exit_code": code}))
        self._exit_code = code
        await self.wait_for()
        if self._stopped is not None:
            self._stopped.set()
        else:
            self.loop.stop()

    async def start(self):
        """Start the app."""
        _LOGGER.info("Starting camacq")
        await self.bus.notify(CamAcqStartEvent())
        self._stopped = asyncio.Event()
        register_signals(self)
        await self._stopped.wait()
        return self._exit_code

    def add_executor_job(self, func, *args):
        """Schedule a function to be run in the thread pool.

        Return a task.
        """
        task = self.loop.run_in_executor(None, func, *args)

        if self._track_tasks:
            self._pending_tasks.append(task)

        return task

    def create_task(self, coro):
        """Schedule a coroutine on the event loop.

        Return a task.
        """
        task = asyncio.create_task(coro)

        if self._track_tasks:
            self._pending_tasks.append(task)

        return task

    async def wait_for(self):
        """Wait for all pending tasks."""
        await asyncio.sleep(0)
        while self._pending_tasks:
            _LOGGER.debug("Waiting for pending tasks")
            pending = [task for task in self._pending_tasks if not task.done()]
            self._pending_tasks.clear()
            if pending:
                await asyncio.wait(pending)
            else:
                await asyncio.sleep(0)


class ActionsRegistry:
    """Manage all registered actions."""

    def __init__(self, center):
        """Set up instance."""
        self._actions = {}
        self._center = center

    def __getattr__(self, action_type):
        """Return registered actions for an action type."""
        try:
            return self._actions[action_type]
        except KeyError as exc:
            raise MissingActionTypeError(action_type) from exc

    @property
    def actions(self):
        """:dict: Return dict of ActionTypes with all registered actions."""
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
        if not asyncio.iscoroutinefunction(action_func):
            _LOGGER.error(
                "Action handler function %s is not a coroutine function", action_func
            )
            return
        if action_type not in self._actions:
            self._actions[action_type] = ActionType()
        _LOGGER.debug("Registering action %s.%s", action_type, action_id)
        self._actions[action_type][action_id] = Action(
            action_type, action_id, action_func, schema
        )

    async def call(self, action_type, action_id, **kwargs):
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
        if (
            action_type not in self._actions
            or action_id not in self._actions[action_type]
        ):
            _LOGGER.error(
                "No action registered for type %s or id %s", action_type, action_id
            )
            return

        action = self._actions[action_type][action_id]

        await action(**kwargs)


class ActionType(dotdict):
    """Represent an action type."""

    def __getattr__(self, action_id):
        """Return registered action for an action id."""
        try:
            return self[action_id]
        except KeyError as exc:
            raise MissingActionError(action_id) from exc


class Action:
    """Represent an action."""

    # pylint: disable=too-few-public-methods

    def __init__(self, action_type, action_id, func, schema):
        """Set up the instance."""
        self.action_type = action_type
        self.action_id = action_id
        self.func = func
        self.schema = schema

    async def __call__(self, **kwargs):
        """Call action."""
        silent = kwargs.get("silent", False)
        try:
            kwargs = self.schema(kwargs)
        except vol.Invalid as exc:
            _LOGGER.log(
                logging.DEBUG if silent else logging.ERROR,
                "Invalid action call parameters %s: %s for action: %s.%s",
                kwargs,
                exc,
                self.action_type,
                self.action_id,
            )
            return
        _LOGGER.log(
            logging.DEBUG if silent else logging.INFO,
            "Calling action %s.%s: %s",
            self.action_type,
            self.action_id,
            kwargs,
        )
        try:
            async with async_timeout(ACTION_TIMEOUT):
                await self.func(action_id=self.action_id, **kwargs)
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Action %s.%s. timed out after %s seconds",
                self.action_type,
                self.action_id,
                ACTION_TIMEOUT,
            )
        except CamAcqError as exc:
            _LOGGER.error(
                "Failed to call action %s.%s: %s", self.action_type, self.action_id, exc
            )
            raise


def loop_exception_handler(loop, context):
    """Handle exceptions inside the event loop."""
    kwargs = {}
    exc = context.get("exception")
    if exc:
        kwargs["exc_info"] = exc

    _LOGGER.error("Error running job: %s", context["message"], **kwargs)


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
        return self.data.get("exit_code")
