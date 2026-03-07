"""Control the microscope."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
import inspect
import logging
from typing import Any, ParamSpec, TypeVar

import voluptuous as vol

from camacq.const import ACTION_TIMEOUT, CAMACQ_START_EVENT, CAMACQ_STOP_EVENT
from camacq.event import Event, EventBus
from camacq.exceptions import CamAcqError, MissingActionError, MissingActionTypeError
from camacq.helper import register_signals
from camacq.plugins.sample import Samples
from camacq.util import dotdict

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")
_P = ParamSpec("_P")


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

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Set up instance."""
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.loop.set_exception_handler(loop_exception_handler)
        self.bus = EventBus(self)
        self.actions: ActionsRegistry = ActionsRegistry(self)
        self.samples: Samples = Samples()
        self.data: dict[str, Any] = {}
        self._exit_code = 0
        self._stopped: asyncio.Event | None = None
        self._pending_tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
        self._track_tasks = False

    def __repr__(self) -> str:
        """Return the representation."""
        return "<Center>"

    async def end(self, code: int) -> None:
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

    async def start(self) -> int:
        """Start the app."""
        _LOGGER.info("Starting camacq")
        await self.bus.notify(CamAcqStartEvent())
        self._stopped = asyncio.Event()
        register_signals(self)
        await self._stopped.wait()
        return self._exit_code

    def add_executor_job(
        self, func: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs
    ) -> asyncio.Future[_T]:
        """Schedule a function to be run in the thread pool.

        Return a task.
        """
        task = self.loop.run_in_executor(None, func, *args)

        if self._track_tasks:
            self._pending_tasks.append(task)

        return task

    def create_task(self, coro: Coroutine[Any, Any, _T]) -> asyncio.Task[_T]:
        """Schedule a coroutine on the event loop.

        Return a task.
        """
        task = asyncio.create_task(coro)

        if self._track_tasks:
            self._pending_tasks.append(task)

        return task

    async def wait_for(self) -> None:
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


ActionFunc = Callable[..., Awaitable[None]]


class ActionsRegistry:
    """Manage all registered actions."""

    def __init__(self, center: Center) -> None:
        """Set up instance."""
        self._actions: dict[str, ActionType] = {}
        self._center = center

    def __getattr__(self, action_type: str) -> ActionType:
        """Return registered actions for an action type."""
        try:
            return self._actions[action_type]
        except KeyError as exc:
            raise MissingActionTypeError(action_type) from exc

    @property
    def actions(self) -> dict[str, ActionType]:
        """:dict: Return dict of ActionTypes with all registered actions."""
        return self._actions

    def register(
        self,
        action_type: str,
        action_id: str,
        action_func: ActionFunc,
        schema: vol.Schema | Any,
    ) -> None:
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
        if not inspect.iscoroutinefunction(action_func):
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

    async def call(self, action_type: str, action_id: str, **kwargs: Any) -> None:
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

    def __getattr__(self, action_id: str) -> Action:  # type: ignore[override]
        """Return registered action for an action id."""
        try:
            return self[action_id]
        except KeyError as exc:
            raise MissingActionError(action_id) from exc


class Action:
    """Represent an action."""

    def __init__(
        self,
        action_type: str,
        action_id: str,
        func: ActionFunc,
        schema: vol.Schema | Any,
    ) -> None:
        """Set up the instance."""
        self.action_type = action_type
        self.action_id = action_id
        self.func = func
        self.schema = schema

    async def __call__(self, **kwargs: Any) -> None:
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
            async with asyncio.timeout(ACTION_TIMEOUT):
                await self.func(action_id=self.action_id, **kwargs)
        except TimeoutError:
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


def loop_exception_handler(
    loop: asyncio.AbstractEventLoop, context: dict[str, Any]
) -> None:
    """Handle exceptions inside the event loop."""
    kwargs: dict[str, Any] = {}
    exc = context.get("exception")
    if exc:
        kwargs["exc_info"] = exc

    _LOGGER.error("Error running job: %s", context["message"], **kwargs)


class CamAcqStartEvent(Event):
    """An event fired when camacq has started."""

    __slots__ = ()

    event_type = CAMACQ_START_EVENT


class CamAcqStopEvent(Event):
    """An event fired when camacq is about to stop."""

    __slots__ = ()

    event_type = CAMACQ_STOP_EVENT

    @property
    def exit_code(self) -> int | None:
        """:int: Return the plate instance of the event."""
        return self.data.get("exit_code")
