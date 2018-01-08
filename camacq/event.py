"""Hold events."""
import logging
from functools import partial
from importlib import import_module

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Event(object):
    """A base event.

    Parameters
    ----------
    data : any object
        The data instance of the event.

    Attributes
    ----------
    data : any object
        Return the data of the event.
    """

    __slots__ = ('data', )

    def __init__(self, data):
        """Set up event."""
        self.data = data

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.data)


class SampleEvent(Event):
    """An event produced by a sample change event."""

    __slots__ = ()


class PlateEvent(SampleEvent):
    """An event produced by a sample plate change event."""

    __slots__ = ()


class WellEvent(PlateEvent):
    """An event produced by a sample well change event."""

    __slots__ = ()


class FieldEvent(WellEvent):
    """An event produced by a sample field change event."""

    __slots__ = ()


class ChannelEvent(WellEvent):
    """An event produced by a sample channel change event."""

    __slots__ = ()


class SampleImageEvent(Event):
    """An event produced by a sample image change event."""

    __slots__ = ()


class DummyEvent(Event):
    """Represent a dummy event."""

    __slots__ = ()


def dummy_handler(event):
    """Handle dummy event."""
    pass


class EventBus(object):
    """Representation of an eventbus.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    """

    def __init__(self, center):
        """Set up instance."""
        self._center = center
        self._event = import_module('zope.event')
        self._handler = import_module('zope.event.classhandler')
        # Limitation in zope requires at least one item in registry to
        # avoid adding another dispatch function to the list of
        # subscribers.
        self._handler.handler(DummyEvent, dummy_handler)

    @property
    def handlers(self):
        """:list: Return all registered handlers."""
        return [handler for handler in self._handler.registry
                if not isinstance(handler, DummyEvent)]

    def register(self, event_type, handler):
        """Register event handler and return a function to remove it.

        An event can be a message from the microscope API or an
        internal event.

        Parameters
        ----------
        event_type : Event class
            A class of Event or subclass of Event.
        handler : callable
            A function that should accept two parameters, center and
            event. The first parameter is the Center instance, the
            second parameter is the Event instance that has fired.

        Returns
        -------
        callable
            Return a function to remove the registered handler.
        """
        handler = partial(handler, self._center)
        self._handler.handler(event_type, handler)

        def remove():
            """Remove registered event handler."""
            self._handler.registry.pop(event_type, None)

        return remove

    def _clear(self):
        """Remove all registered handlers except dummy."""
        for handler in self._handler.registry:
            if isinstance(handler, DummyEvent):
                continue
            self._handler.registry.pop(handler, None)

    def notify(self, event):
        """Notify handlers that an event has fired.

        Parameters
        ----------
        event : Event instance
            An instance of Event or an instance of subclass of Event.
        """
        _LOGGER.debug(event)
        self._event.notify(event)
