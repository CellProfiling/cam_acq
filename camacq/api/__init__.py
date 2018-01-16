"""Microscope API specific modules."""
from builtins import object  # pylint: disable=redefined-builtin

from camacq.event import Event
from camacq.helper import FeatureParent, setup_all_modules

ACTION_SEND = 'send'
ACTION_START_IMAGING = 'start_imaging',
ACTION_STOP_IMAGING = 'stop_imaging',

ACTION_TO_METHOD = {
    ACTION_SEND: 'send',
    ACTION_START_IMAGING: 'start_imaging',
    ACTION_STOP_IMAGING: 'stop_imaging',
}


def send(center, commands, api_name=None):
    """Send each command in commands.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    commands : list
        List of commands to send.
    api_name : str
        Name of API.

    Example
    -------
    ::

        send(center, [[('cmd', 'deletelist')], [('cmd', 'startscan')]])
    """
    for cmd in commands:
        center.actions.call(
            'camacq.api', ACTION_SEND, child_name=api_name, command=cmd)


def setup_package(center, config):
    """Set up the microscope API package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    parent = FeatureParent()
    setup_all_modules(center, config, __name__, add_child=parent.add_child)

    def handle_action(**kwargs):
        """Handle action call to send a command to an api of a child.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to the
            child method when an action is called.
        """
        action_id = kwargs.pop('action_id')
        method = ACTION_TO_METHOD[action_id]
        child_name = kwargs.pop('child_name', None)
        if child_name:
            children = [parent.children.get(child_name)]
        else:
            children = list(parent.children.values())
        for child in children:
            getattr(child, method)(**kwargs)

    for action in ACTION_TO_METHOD:
        center.actions.register(__name__, action, handle_action)


class Api(object):
    """Represent the microscope API."""

    def send(self, command):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send, should be a JSON string.
        """
        raise NotImplementedError()

    def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        raise NotImplementedError()

    def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        raise NotImplementedError()


# pylint: disable=too-few-public-methods
class CommandEvent(Event):
    """An event received from the API.

    Notify with this event when a command is received via API.
    """

    __slots__ = ()

    @property
    def command(self):
        """:str: Return the JSON command string."""
        return None


class StartCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging starts via API.
    """

    __slots__ = ()


class StopCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging stops via API.
    """

    __slots__ = ()


class ImageEvent(Event):
    """An event received from the API.

    Notify with this event when an image is saved via API.
    """

    __slots__ = ()

    @property
    def path(self):
        """:str: Return the absolute path to the image."""
        return None

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return None

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return None

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return None

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return None

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return None

    @property
    def plate_name(self):
        """:str: Return plate name of the image."""
        return None
