"""Microscope API specific modules."""
from camacq.bootstrap import setup_all_modules
from camacq.helper import FeatureParent

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

        send(api, [[('cmd', 'deletelist')], [('cmd', 'startscan')]])
    """
    for cmd in commands:
        center.actions.call(
            'camacq.api', ACTION_API_SEND, child_name=api_name, command=cmd)


def setup_package(center, config):
    """Set up the microscope API package."""
    parent = FeatureParent()
    setup_all_modules(center, config, __name__, add_child=parent.add_child)

    def handle_action(**kwargs):
        """Handle the action call to send a command to an api of a child."""
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
