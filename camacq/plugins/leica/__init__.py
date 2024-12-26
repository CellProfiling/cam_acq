"""Leica microscope API specific modules."""

import asyncio
import logging
import tempfile
from functools import partial

import voluptuous as vol
from async_timeout import timeout as async_timeout
from leicacam.async_cam import AsyncCAM
from leicacam.cam import bytes_as_dict, check_messages, tuples_as_bytes
from leicaimage import attribute, attribute_as_str

from camacq.const import CAMACQ_STOP_EVENT
from camacq.helper import ensure_dict
from camacq.plugins.api import (
    Api,
    CommandEvent,
    ImageEvent,
    StartCommandEvent,
    StopCommandEvent,
    register_api,
)

from .command import start, stop
from .helper import find_image_path, get_field, get_imgs
from .sample import setup_module as sample_setup_module

_LOGGER = logging.getLogger(__name__)

CONF_HOST = "host"
CONF_IMAGING_DIR = "imaging_dir"
CONF_LEICA = "leica"
CONF_PORT = "port"
JOB_ID = "--E{:02d}"
LEICA_COMMAND_EVENT = "leica_command_event"
LEICA_START_COMMAND_EVENT = "leica_start_command_event"
LEICA_STOP_COMMAND_EVENT = "leica_stop_command_event"
LEICA_IMAGE_EVENT = "leica_image_event"
REL_IMAGE_PATH = "relpath"
SCAN_FINISHED = "scanfinished"
SCAN_STARTED = "scanstart"
START_STOP_DELAY = 2.0

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        ensure_dict,
        {
            vol.Optional(CONF_HOST, default="localhost"): vol.Coerce(str),
            vol.Optional(CONF_PORT, default=8895): vol.Coerce(int),
            # pylint: disable=no-value-for-parameter
            vol.Optional(CONF_IMAGING_DIR, default=tempfile.gettempdir()): vol.IsDir(),
        },
    )
)


async def setup_module(center, config):
    """Set up Leica api package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    await sample_setup_module(center, config)
    conf = config[CONF_LEICA]
    host = conf[CONF_HOST]
    port = conf[CONF_PORT]
    cam = AsyncCAM(host, port, loop=center.loop)
    try:
        await cam.connect()
    except OSError as exc:
        _LOGGER.error("Connecting to server %s failed: %s", host, exc)
        return
    api = LeicaApi(center, conf, cam)
    register_api(center, api)
    # Start task that calls receive on the socket to the microscope
    task = center.create_task(api.start_listen())

    async def stop_listen(center, event):
        """Stop the task that listens to the client socket."""
        task.cancel()
        await task
        api.client.close()

    center.bus.register(CAMACQ_STOP_EVENT, stop_listen)


class LeicaApi(Api):
    """Represent the Leica API."""

    def __init__(self, center, config, client):
        """Set up the Leica API."""
        self.center = center
        self.client = client
        self.config = config
        self._last_image_path = None

    @property
    def name(self):
        """Return the name of the API."""
        return __name__

    async def start_listen(self):
        """Receive from the microscope socket."""
        try:
            while True:
                reply = await self.client.receive()
                self.center.create_task(self.receive(reply))
        except asyncio.CancelledError:
            _LOGGER.debug("Stopped listening for messages from CAM")

    async def receive(self, replies):
        """Receive replies from CAM server and fire an event per reply.

        Parameters
        ----------
        replies : list
            A list of replies from the CAM server.
        """
        # if reply check reply and call correct listener
        # parse reply and create Event
        # await event notify in sequential order
        # reply must be an iterable
        if not isinstance(replies, list):
            replies = [replies]
        for reply in replies:
            if not reply or not isinstance(reply, dict):
                continue
            if REL_IMAGE_PATH in reply:
                imaging_dir = self.config[CONF_IMAGING_DIR]
                rel_path = reply[REL_IMAGE_PATH]
                if rel_path == self._last_image_path:
                    # guard against duplicate image events from the microscope
                    _LOGGER.debug("Duplicate image reply received: %s", rel_path)
                    continue
                self._last_image_path = rel_path
                image_path = find_image_path(rel_path, imaging_dir)
                field_path = await self.center.add_executor_job(get_field, image_path)
                image_paths = await self.center.add_executor_job(
                    partial(
                        get_imgs,
                        field_path,
                        search=JOB_ID.format(attribute(image_path, "E")),
                    )
                )
                for path in image_paths:
                    # await in sequential order
                    await self.center.bus.notify(LeicaImageEvent({"path": path}))
            elif SCAN_STARTED in list(reply.values()):
                await self.center.bus.notify(LeicaStartCommandEvent(reply))
            elif SCAN_FINISHED in list(reply.values()):
                await self.center.bus.notify(LeicaStopCommandEvent(reply))
            else:
                await self.center.bus.notify(LeicaCommandEvent(reply))

    async def send(self, command, **kwargs):
        """Send a command to the Leica API.

        Parameters
        ----------
        command : list of tuples or string
            The command to send.
        """
        block = kwargs.get("block", True)

        if isinstance(command, str):
            command = bytes_as_dict(command.encode())
            command = list(command.items())
        cmd, value = command[0]  # use the first cmd and value to wait for
        cmd_sent = self.center.loop.create_future()

        async def receive_reply(center, event):
            """Indicate that reply has been received."""
            if check_messages([event.data], cmd, value=value):
                if not cmd_sent.done():
                    cmd_sent.set_result(True)

        remove = self.center.bus.register(LEICA_COMMAND_EVENT, receive_reply)
        cmd_sent.add_done_callback(lambda x: remove())

        await self.client.send(command)

        if not block:
            return cmd_sent
        return await cmd_sent

    async def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        await self._start_stop_imaging(start(), LEICA_START_COMMAND_EVENT, SCAN_STARTED)
        # A delay is needed after starting.
        await asyncio.sleep(START_STOP_DELAY)

    async def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        # A delay is needed before and after stopping.
        await asyncio.sleep(START_STOP_DELAY)
        await self._start_stop_imaging(stop(), LEICA_STOP_COMMAND_EVENT, SCAN_FINISHED)
        await asyncio.sleep(START_STOP_DELAY)

    async def _start_stop_imaging(self, cmd, event, ack_cmd):
        """Send a command to the microscope to start or stop the imaging."""
        cmd_sent = self.center.loop.create_future()

        async def receive_reply(center, event):
            """Indicate that reply has been received."""
            if not cmd_sent.done():
                cmd_sent.set_result(True)

        remove = self.center.bus.register(event, receive_reply)
        cmd_sent.add_done_callback(lambda x: remove())

        trigger_cmd_sent = await self.send(cmd, block=False)
        _LOGGER.info("Waiting for %s message for 10 seconds", ack_cmd)
        try:
            async with async_timeout(10.0):
                await asyncio.wait([cmd_sent, trigger_cmd_sent])
        except asyncio.TimeoutError:
            _LOGGER.info("No acknowledgement event received, continuing anyway")


# pylint: disable=too-few-public-methods
class LeicaCommandEvent(CommandEvent):
    """Leica CommandEvent class."""

    __slots__ = ()

    event_type = LEICA_COMMAND_EVENT

    @property
    def command(self):
        """Return the command string."""
        return tuples_as_bytes(list(self.data.items())).decode()


class LeicaStartCommandEvent(StartCommandEvent, LeicaCommandEvent):
    """Leica StartCommandEvent class."""

    __slots__ = ()

    event_type = LEICA_START_COMMAND_EVENT


class LeicaStopCommandEvent(StopCommandEvent, LeicaCommandEvent):
    """Leica StopCommandEvent class."""

    __slots__ = ()

    event_type = LEICA_STOP_COMMAND_EVENT


class LeicaImageEvent(ImageEvent):
    """Leica ImageEvent class."""

    __slots__ = ()

    event_type = LEICA_IMAGE_EVENT

    @property
    def path(self):
        """:str: Return absolute path to the image."""
        return self.data.get("path", "")

    @property
    def well_x(self):
        """:int: Return x coordinate of the well of the image."""
        return attribute(self.path, "U")

    @property
    def well_y(self):
        """:int: Return y coordinate of the well of the image."""
        return attribute(self.path, "V")

    @property
    def field_x(self):
        """:int: Return x coordinate of the well of the image."""
        return attribute(self.path, "X")

    @property
    def field_y(self):
        """:int: Return y coordinate of the well of the image."""
        return attribute(self.path, "Y")

    @property
    def z_slice_id(self):
        """:int: Return z index of the image."""
        return attribute(self.path, "Z")

    @property
    def channel_id(self):
        """:int: Return channel id of the image."""
        return attribute(self.path, "C")

    @property
    def job_id(self):
        """:int: Return job id of the image."""
        return attribute(self.path, "E")

    @property
    def plate_name(self):
        """:str: Return plate name of the image."""
        return attribute_as_str(self.path, "S")
