"""Microscope API specific modules."""
import json
from builtins import object  # pylint: disable=redefined-builtin

import voluptuous as vol

from camacq.const import (COMMAND_EVENT, IMAGE_EVENT, START_COMMAND_EVENT,
                          STOP_COMMAND_EVENT)
from camacq.event import Event
from camacq.helper import BASE_ACTION_SCHEMA, FeatureParent, setup_all_modules


def validate_commands(value):
    """Validate a template string via JSON."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            raise vol.Invalid('Invalid commands: {}'.format(value))
    else:
        schema = vol.Schema([vol.Coerce(str)])
        return schema(value)


ACTION_SEND = 'send'
ACTION_SEND_MANY = 'send_many'
ACTION_START_IMAGING = 'start_imaging'
ACTION_STOP_IMAGING = 'stop_imaging'
CONF_API = 'api'

SEND_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    'command': vol.Coerce(str),
})

SEND_MANY_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({
    'commands': validate_commands,
})

START_IMAGING_ACTION_SCHEMA = STOP_IMAGING_ACTION_SCHEMA = BASE_ACTION_SCHEMA

ACTION_TO_METHOD = {
    ACTION_SEND: {'method': 'send', 'schema': SEND_ACTION_SCHEMA},
    ACTION_SEND_MANY: {
        'method': 'send_many', 'schema': SEND_MANY_ACTION_SCHEMA},
    ACTION_START_IMAGING: {
        'method': 'start_imaging', 'schema': START_IMAGING_ACTION_SCHEMA},
    ACTION_STOP_IMAGING: {
        'method': 'stop_imaging', 'schema': STOP_IMAGING_ACTION_SCHEMA},
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

        >>> send(center, [[('cmd', 'deletelist')], [('cmd', 'startscan')]])

        >>> send(center, ['/cmd:deletelist', '/cmd:startscan'])
    """
    for cmd in commands:
        center.actions.call(
            'command', ACTION_SEND, child_name=api_name, command=cmd)


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
        method = ACTION_TO_METHOD[action_id]['method']
        child_name = kwargs.pop('child_name', None)
        if child_name:
            children = [parent.children.get(child_name)]
        else:
            children = list(parent.children.values())
        for child in children:
            getattr(child, method)(**kwargs)

    for action_id, options in ACTION_TO_METHOD.items():
        schema = options['schema']
        center.actions.register('command', action_id, handle_action, schema)


class Api(object):
    """Represent the microscope API."""

    def send(self, command):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send.
        """
        raise NotImplementedError()

    def send_many(self, commands):
        """Send multiple commands to the microscope API.

        Parameters
        ----------
        commands : list
            A list of commands to send.
        """
        for cmd in commands:
            self.send(cmd)

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

    event_type = COMMAND_EVENT

    @property
    def command(self):
        """:str: Return the command string."""
        return None


class StartCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging starts via API.
    """

    __slots__ = ()

    event_type = START_COMMAND_EVENT


class StopCommandEvent(CommandEvent):
    """An event received from the API.

    Notify with this event when imaging stops via API.
    """

    __slots__ = ()

    event_type = STOP_COMMAND_EVENT


class ImageEvent(Event):
    """An event received from the API.

    Notify with this event when an image is saved via API.
    """

    __slots__ = ()

    event_type = IMAGE_EVENT

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

    def __repr__(self):
        """Return the representation."""
        return ("<{}: plate_name {}: well_x {}: well_y {}: field_x {}: "
                "field_y {}: channel_id {}>".format(
                    type(self).__name__, self.plate_name, self.well_x,
                    self.well_y, self.field_x, self.field_y, self.channel_id))
