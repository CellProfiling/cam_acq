"""Leica microscope API specific modules."""
import asyncio
import logging
from functools import partial

from async_timeout import timeout as async_timeout
from leicacam.async_cam import AsyncCAM
from leicacam.cam import bytes_as_dict, check_messages, tuples_as_bytes
from leicaexperiment import attribute, attribute_as_str

from camacq.api import (
    CONF_API,
    Api,
    CommandEvent,
    ImageEvent,
    StartCommandEvent,
    StopCommandEvent,
    register_api,
)
from camacq.api.leica.command import start, stop
from camacq.api.leica.helper import find_image_path, get_field, get_imgs
from camacq.const import CAMACQ_STOP_EVENT, CONF_HOST, CONF_PORT, IMAGING_DIR, JOB_ID

_LOGGER = logging.getLogger(__name__)

CONF_LEICA = "leica"
LEICA_COMMAND_EVENT = "leica_command_event"
LEICA_START_COMMAND_EVENT = "leica_start_command_event"
LEICA_STOP_COMMAND_EVENT = "leica_stop_command_event"
LEICA_IMAGE_EVENT = "leica_image_event"
REL_IMAGE_PATH = "relpath"
SCAN_FINISHED = "scanfinished"
SCAN_STARTED = "scanstart"


async def setup_package(center, config):
    """Set up Leica api package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    conf = config[CONF_API][CONF_LEICA]
    host = conf.get(CONF_HOST, "localhost")
    port = conf.get(CONF_PORT, 8895)
    cam = AsyncCAM(host, port, loop=center.loop)
    try:
        await cam.connect()
    except OSError as exc:
        _LOGGER.error("Connecting to server %s failed: %s", host, exc)
        return
    api = LeicaApi(center, config, cam)
    register_api(center, __name__, api)
    # Start task that calls receive on the socket to the microscope
    task = center.create_task(api.start_listen())

    async def stop_listen(center, event):
        """Stop the task that listens to the client socket."""
        task.cancel()

    center.bus.register(CAMACQ_STOP_EVENT, stop_listen)


class LeicaApi(Api):
    """Represent the Leica API."""

    def __init__(self, center, config, client):
        """Set up the Leica API."""
        self.center = center
        self.client = client
        self.config = config

    async def start_listen(self):
        """Receive from the microscope socket."""
        try:
            while True:
                reply = await self.client.receive()
                await self.receive(reply)
        except asyncio.CancelledError:
            _LOGGER.debug("Stopped listening for messages from CAM")

    # TODO: Check what events are reported by CAM server. pylint: disable=fixme
    # Make sure that all images get reported eventually.
    async def receive(self, replies):
        """Receive replies from CAM server and fire an event per reply.

        Parameters
        ----------
        replies : list
            A list of replies from the CAM server.
        """
        # if reply check reply and call correct listener
        # parse reply and create Event
        # reply must be an iterable
        if not isinstance(replies, list):
            replies = [replies]
        for reply in replies:
            if not reply or not isinstance(reply, dict):
                continue
            if REL_IMAGE_PATH in reply:
                conf = self.config[CONF_API][CONF_LEICA]
                imaging_dir = conf.get(IMAGING_DIR, "")
                rel_path = reply[REL_IMAGE_PATH]
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
                    self.center.bus.notify(LeicaImageEvent({"path": path}))
            elif SCAN_STARTED in list(reply.values()):
                self.center.bus.notify(LeicaStartCommandEvent(reply))
            elif SCAN_FINISHED in list(reply.values()):
                self.center.bus.notify(LeicaStopCommandEvent(reply))
            else:
                self.center.bus.notify(LeicaCommandEvent(reply))

    async def send(self, command):
        """Send a command to the Leica API.

        Parameters
        ----------
        command : list of tuples or string
            The command to send.
        """
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
                remove()

        remove = self.center.bus.register(LEICA_COMMAND_EVENT, receive_reply)
        await self.client.send(command)
        await cmd_sent

    async def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        cmd_sent = self.center.loop.create_future()

        async def receive_reply(center, event):
            """Indicate that reply has been received."""
            if not cmd_sent.done():
                cmd_sent.set_result(True)
            remove()

        remove = self.center.bus.register(LEICA_START_COMMAND_EVENT, receive_reply)

        await self.send(start())
        _LOGGER.info("Waiting for %s message for 10 seconds", SCAN_STARTED)
        try:
            async with async_timeout(10.0):
                await cmd_sent
        except asyncio.TimeoutError:
            _LOGGER.info("No start event received, continuing anyway")

    async def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        cmd_sent = self.center.loop.create_future()

        async def receive_reply(center, event):
            """Indicate that reply has been received."""
            if not cmd_sent.done():
                cmd_sent.set_result(True)
            remove()

        remove = self.center.bus.register(LEICA_STOP_COMMAND_EVENT, receive_reply)

        await self.send(stop())
        _LOGGER.info("Waiting for %s message for 10 seconds", SCAN_FINISHED)
        try:
            async with async_timeout(10.0):
                await cmd_sent
        except asyncio.TimeoutError:
            _LOGGER.info("No stop event received, continuing anyway")


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
    def z_slice(self):
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
