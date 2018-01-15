"""Hold events."""
import logging
from builtins import object  # pylint: disable=redefined-builtin
from collections import defaultdict
from functools import partial

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Event(object):
    """A base event.

    Parameters
    ----------
    data : dict
        The data of the event.

    Attributes
    ----------
    data : dict
        Return the data of the event.
    """

    __slots__ = ('data', )

    def __init__(self, data=None):
        """Set up event."""
        self.data = data or {}

    def __repr__(self):
        """Return the representation."""
        return "<{}: {}>".format(type(self).__name__, self.data)


class SampleEvent(Event):
    """An event produced by a sample change event."""

    __slots__ = ()

    @property
    def sample(self):
        """:Sample instance: Return the sample instance of the event."""
        return self.data.get('sample')


class PlateEvent(SampleEvent):
    """An event produced by a sample plate change event."""

    __slots__ = ()

    @property
    def plate(self):
        """:Plate instance: Return the plate instance of the event."""
        return self.data.get('plate')

    @property
    def plate_name(self):
        """:str: Return the name of the plate."""
        return self.plate.name


class WellEvent(PlateEvent):
    """An event produced by a sample well change event."""

    __slots__ = ()

    @property
    def well(self):
        """:Well instance: Return the well of the event."""
        return self.data.get('well')

    @property
    def well_x(self):
        """:int: Return the well x coordinate of the event."""
        return self.well.x

    @property
    def well_y(self):
        """:int: Return the well y coordinate of the event."""
        return self.well.y

    @property
    def well_img_ok(self):
        """:bool: Return if the well has all images acquired ok."""
        return self.well.img_ok

    @property
    def well_name(self):
        """:str: Return the name of the well."""
        return self.well.name


class FieldEvent(WellEvent):
    """An event produced by a sample field change event."""

    __slots__ = ()

    @property
    def field(self):
        """:Field instance: Return the field of the event."""
        return self.data.get('field')

    @property
    def field_x(self):
        """:int: Return the field x coordinate of the event."""
        return self.field.x

    @property
    def field_y(self):
        """:int: Return the field y coordinate of the event."""
        return self.field.y

    @property
    def field_dx(self):
        """:int: Return the field dx pixel coordinate of an ROI."""
        return self.field.dx

    @property
    def field_dy(self):
        """:int: Return the field dy pixel coordinate of an ROI."""
        return self.field.dy

    @property
    def gain_field(self):
        """:bool: Return if field is a field marked for a gain job."""
        return self.field.gain_field

    @property
    def field_img_ok(self):
        """:bool: Return if the field has all images acquired ok."""
        return self.field.img_ok

    @property
    def field_name(self):
        """:str: Return the name of the field."""
        return self.field.name


class ChannelEvent(WellEvent):
    """An event produced by a sample channel change event."""

    __slots__ = ()

    @property
    def channel(self):
        """:Channel instance: Return the channel of the event."""
        return self.data.get('channel')

    @property
    def channel_name(self):
        """:str: Return the channel name of the event."""
        return self.channel.name


class SampleImageEvent(Event):
    """An event produced by a sample image removed event."""

    __slots__ = ()

    @property
    def image(self):
        """:Image instance: Return the image instance of the event."""
        return self.data.get('image')

    @property
    def path(self):
        """:str: Return the absolute path to the image."""
        return self.image.path

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.image.well_x

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.image.well_y

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.image.field_x

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.image.field_y

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return self.image.channel_id


class ImageRemovedEvent(SampleImageEvent):
    """An event produced by a sample image removed event."""

    __slots__ = ()


class CamAcqStartEvent(Event):
    """An event fired when camacq has started."""

    __slots__ = ()


class CamAcqStopEvent(Event):
    """An event fired when camacq is about to stop."""

    __slots__ = ()

    @property
    def exit_code(self):
        """:int: Return the plate instance of the event."""
        return self.data.get('exit_code')


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
        self._registry = defaultdict(list)

    @property
    def event_types(self):
        """:list: Return all registered event types."""
        return [event_type for event_type in self._registry]

    def _register_handler(self, event_class, handler):
        """Register handler to fire for events of type event_class."""
        self._registry[event_class].append(handler)

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
        self._register_handler(event_type, handler)

        def remove():
            """Remove registered event handler."""
            self._registry.pop(event_type, None)

        return remove

    def notify(self, event):
        """Notify handlers that an event has fired.

        Parameters
        ----------
        event : Event instance
            An instance of Event or an instance of subclass of Event.
        """
        _LOGGER.debug(event)
        # Inspired by https://goo.gl/VEPG3n
        for event_class in event.__class__.__mro__:
            for handler in self._registry.get(event_class, []):
                handler(event)
