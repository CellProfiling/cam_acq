"""Microscope API specific modules."""
from camacq.event import Event
from camacq.helper import FeatureParent, setup_all_modules

ACTION_API_SEND = 'api_send'

ACTION_TO_METHOD = {
    ACTION_API_SEND: 'send',
}


def send(center, commands, api_name=None):
    """Send each command in commands.

    Parameters
    ----------
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
            'camacq.api', ACTION_API_SEND, child_name=api_name, command=cmd)


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
            children = parent.children.values()
        for child in children:
            getattr(child, method)(**kwargs)

    center.actions.register(__name__, ACTION_API_SEND, handle_action)


class Api(object):
    """Represent the microscope API."""

    # pylint: disable=too-few-public-methods

    def send(self, command):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send, should be a JSON string.

        Returns
        -------
        str
            Return a JSON string with a list of replies from the API.
        """
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
