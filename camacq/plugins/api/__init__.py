"""Microscope API specific modules."""

import asyncio
import json
import logging

import voluptuous as vol

from camacq.const import (
    COMMAND_EVENT,
    IMAGE_EVENT,
    START_COMMAND_EVENT,
    STOP_COMMAND_EVENT,
)
from camacq.event import Event
from camacq.helper import BASE_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)

COMMAND_VALIDATOR = vol.Any([(str, str)], vol.Coerce(str))


def validate_commands(value):
    """Validate a template string via JSON."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError as exc:
            raise vol.Invalid(f"Invalid commands: {value}") from exc
    else:
        schema = vol.Schema([COMMAND_VALIDATOR])
        return schema(value)


ACTION_SEND = "send"
ACTION_SEND_MANY = "send_many"
ACTION_START_IMAGING = "start_imaging"
ACTION_STOP_IMAGING = "stop_imaging"
CONF_API = "api"
DATA_API = "api"

SEND_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend(
    {"api_name": vol.Coerce(str), "command": COMMAND_VALIDATOR}
)

SEND_MANY_ACTION_SCHEMA = BASE_ACTION_SCHEMA.extend({"commands": validate_commands})

START_IMAGING_ACTION_SCHEMA = STOP_IMAGING_ACTION_SCHEMA = BASE_ACTION_SCHEMA

ACTION_TO_METHOD = {
    ACTION_SEND: {"method": "send", "schema": SEND_ACTION_SCHEMA},
    ACTION_SEND_MANY: {"method": "send_many", "schema": SEND_MANY_ACTION_SCHEMA},
    ACTION_START_IMAGING: {
        "method": "start_imaging",
        "schema": START_IMAGING_ACTION_SCHEMA,
    },
    ACTION_STOP_IMAGING: {
        "method": "stop_imaging",
        "schema": STOP_IMAGING_ACTION_SCHEMA,
    },
}


def register_api(center, api):
    """Register api."""
    api_store = center.data.setdefault(DATA_API, {})
    api_store[api.name] = api


async def setup_module(center, config):
    """Set up the microscope API package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    api_store = center.data.setdefault(DATA_API, {})

    async def handle_action(**kwargs):
        """Handle action call to send a command to an api.

        Parameters
        ----------
        **kwargs
            Arbitrary keyword arguments. These will be passed to the
            api method when an action is called.
        """
        action_id = kwargs.pop("action_id")
        method = ACTION_TO_METHOD[action_id]["method"]
        api_name = kwargs.pop("api_name", None)
        if api_name:
            apis = [api_store[api_name]]
        else:
            apis = list(api_store.values())
        tasks = []
        for api in apis:
            _LOGGER.debug("Handle API %s action %s: %s", api.name, action_id, kwargs)
            tasks.append(center.create_task(getattr(api, method)(**kwargs)))
        if tasks:
            await asyncio.wait(tasks)

    for action_id, options in ACTION_TO_METHOD.items():
        schema = options["schema"]
        center.actions.register("command", action_id, handle_action, schema)


class Api:
    """Represent the microscope API."""

    @property
    def name(self):
        """Return the name of the API."""
        raise NotImplementedError()

    async def send(self, command, **kwargs):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send.
        """
        raise NotImplementedError()

    async def send_many(self, commands, **kwargs):
        """Send multiple commands to the microscope API.

        Parameters
        ----------
        commands : list
            A list of commands to send.
        """
        for cmd in commands:
            # It's important that each task is done before we start the next.
            await self.send(cmd, **kwargs)

    async def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        raise NotImplementedError()

    async def stop_imaging(self):
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
        """:str: Return absolute path to the image."""
        return self.data.get("path")

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.data.get("well_x")

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.data.get("well_y")

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return self.data.get("field_x")

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return self.data.get("field_y")

    @property
    def z_slice_id(self):
        """:int: Return z index of the image."""
        return self.data.get("z_slice_id")

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return self.data.get("channel_id")

    @property
    def plate_name(self):
        """:str: Return plate name of the image."""
        return self.data.get("plate_name")

    def __repr__(self):
        """Return the representation."""
        data = {
            "plate_name": self.plate_name,
            "well_x": self.well_x,
            "well_y": self.well_y,
            "field_x": self.field_x,
            "field_y": self.field_y,
            "z_slice_id": self.z_slice_id,
            "channel_id": self.channel_id,
        }
        return f"{type(self).__name__}(data={data})"
