"""Hold events."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from camacq.const import BASE_EVENT

if TYPE_CHECKING:
    from camacq.control import Center

_LOGGER = logging.getLogger(__name__)

EventHandler = Callable[["Center", "Event"], Any]


class Event:
    """A base event.

    Parameters
    ----------
    data : dict, optional
        The data of the event.

    """

    __slots__ = {"data": "Return the data of the event."}

    event_type: ClassVar[str] = BASE_EVENT

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Set up event."""
        self.data: dict[str, Any] = data or {}

    def __repr__(self) -> str:
        """Return the representation."""
        return f"{type(self).__name__}(data={self.data})"


class EventBus:
    """Representation of an eventbus.

    Parameters
    ----------
    center : Center instance
        The Center instance.

    """

    def __init__(self, center: Center) -> None:
        """Set up instance."""
        self._center = center
        self._registry: dict[str, list[EventHandler]] = {}

    @property
    def event_types(self) -> list[str]:
        """:list: Return all registered event types."""
        return list(self._registry.keys())

    def _register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register handler to fire for events of type event_class."""
        handlers = self._registry.setdefault(event_type, [])
        handlers.append(handler)

    def register(self, event_type: str, handler: EventHandler) -> Callable[[], None]:
        """Register event handler and return a function to remove it.

        An event can be a message from the microscope API or an
        internal event.

        Parameters
        ----------
        event_type : str
            A string representing the type of event.
        handler : callable
            A coroutine function that should accept two parameters, center and
            event. The first parameter is the Center instance, the
            second parameter is the Event instance that has fired.

        Returns
        -------
        callable
            Return a function to remove the registered handler.

        """
        _LOGGER.debug("Registering event handler for event type %s", event_type)
        self._register_handler(event_type, handler)

        def remove() -> None:
            """Remove registered event handler."""
            handlers = self._registry[event_type]
            try:
                handlers.remove(handler)
            except ValueError:
                _LOGGER.warning("Handler %s already removed from bus", handler)

        return remove

    async def notify(self, event: Event) -> None:
        """Notify handlers that an event has fired.

        Parameters
        ----------
        event : Event instance
            An instance of Event or an instance of subclass of Event.

        """
        _LOGGER.debug("Notifying event %s", event)
        # Inspired by https://goo.gl/VEPG3n
        registry = self._registry
        for event_class in event.__class__.__mro__:
            # Handle base objects for Python 3.
            if event_class.__name__ == "object":
                continue
            event_type = getattr(event_class, "event_type", None)
            if event_type is None:
                continue
            for handler in registry.get(event_type, []):
                await handler(self._center, event)  # await in sequential order


def match_event(event: Event, **event_data: Any) -> bool:
    """Return True if event attributes match event_data."""
    if not event_data or all(
        val == getattr(event, key, None) for key, val in event_data.items()
    ):
        return True

    return False
