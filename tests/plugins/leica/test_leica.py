"""Test Leica API."""

import asyncio
from collections import OrderedDict
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from leicacam.async_cam import AsyncCAM

from camacq import plugins
from camacq.plugins import api as base_api
from camacq.plugins.leica import (
    LEICA_COMMAND_EVENT,
    LEICA_START_COMMAND_EVENT,
    LEICA_STOP_COMMAND_EVENT,
    LeicaApi,
    LeicaCommandEvent,
    LeicaImageEvent,
    LeicaStartCommandEvent,
    LeicaStopCommandEvent,
)

# pylint: disable=redefined-outer-name


@pytest.fixture
async def api(center):
    """Return a leica api instance."""
    leica_conf = {"host": "localhost", "port": 8895, "imaging_dir": "/tmp"}
    config = {"leica": leica_conf}
    client = Mock(AsyncCAM(loop=center.loop))
    mock_api = LeicaApi(center, leica_conf, client)

    async def register_mock_api(center, config):
        """Register a mock api package."""
        base_api.register_api(center, mock_api)

    with patch("camacq.plugins.leica.setup_module") as leica_setup, patch(
        "camacq.plugins.leica.START_STOP_DELAY", 0.0
    ):
        leica_setup.side_effect = register_mock_api
        await base_api.setup_module(center, config)
        yield mock_api


@pytest.fixture
def get_imgs():
    """Mock leica helper get_imgs."""
    with patch("camacq.plugins.leica.get_imgs") as mock_get_imgs:
        yield mock_get_imgs


async def test_setup_bad_socket(center, caplog):
    """Test setup leica api package with bad host or port."""
    config = {"leica": {}}
    with patch("camacq.plugins.leica.AsyncCAM.connect", side_effect=OSError()):
        await plugins.setup_module(center, config)
    assert "Connecting to server localhost failed:" in caplog.text


async def test_send(api):
    """Test the leica api send method."""
    cmd_string = "/cmd:deletelist"
    cmd_tuples = [("cmd", "deletelist")]

    async def mock_send(commands):
        """Mock client send."""
        await api.receive([OrderedDict(cmd_tuples)])

    api.client.receive.return_value = OrderedDict(cmd_tuples)
    api.client.send.side_effect = mock_send
    mock_handler = AsyncMock()
    api.center.bus.register(LEICA_COMMAND_EVENT, mock_handler)

    await api.send(cmd_string)

    assert api.client.send.call_count == 1
    _, args, _ = api.client.send.mock_calls[0]
    assert args[0] == cmd_tuples
    assert mock_handler.call_count == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaCommandEvent)
    assert event.command == cmd_string


async def test_start_imaging(api):
    """Test the leica api start imaging method."""
    event_string = "/inf:scanstart"
    cmd_tuples = [("cmd", "startscan")]
    start_event_tuples = [("inf", "scanstart")]

    async def mock_send(commands):
        """Mock client send."""
        await api.receive([OrderedDict(cmd_tuples), OrderedDict(start_event_tuples)])

    api.client.send.side_effect = mock_send
    mock_handler = AsyncMock()
    api.center.bus.register(LEICA_START_COMMAND_EVENT, mock_handler)

    await api.start_imaging()

    assert api.client.send.call_count == 1
    assert mock_handler.call_count == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == event_string


async def test_stop_imaging(api):
    """Test the leica api stop imaging method."""
    event_string = "/inf:scanfinished"
    stop_event_tuples = [("inf", "scanfinished")]
    cmd_tuples = [("cmd", "stopscan")]

    async def mock_send(commands):
        """Mock client send."""
        await api.receive([OrderedDict(cmd_tuples), OrderedDict(stop_event_tuples)])

    api.client.send.side_effect = mock_send
    mock_handler = AsyncMock()
    api.center.bus.register(LEICA_STOP_COMMAND_EVENT, mock_handler)

    await api.stop_imaging()

    assert api.client.send.call_count == 1
    assert mock_handler.call_count == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaStopCommandEvent)
    assert event.command == event_string


async def test_receive(api, get_imgs):
    """Test the leica api receive method."""
    image_path = (
        "subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/"
        "field--X01--Y01/image--L0000--S00--U00--V00--J15--E04--O01"
        "--X01--Y01--T0000--Z00--C00.ome.tif"
    )
    cmd_tuples = [
        (
            "relpath",
            "subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X01--Y01"
            "/image--L0000--S00--U00--V00--J15--E04--O01"
            "--X01--Y01--T0000--Z00--C00.ome.tif",
        )
    ]
    field_path = "subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X01--Y01"
    root_path = "/root"
    leica_config = {"imaging_dir": root_path}
    api.config = leica_config
    image_path = str(Path(root_path) / image_path)
    get_imgs.return_value = [image_path]
    mock_handler = AsyncMock()
    api.center.bus.register("image_event", mock_handler)

    await api.receive([OrderedDict(cmd_tuples)])

    assert get_imgs.call_count == 1
    _, args, kwargs = get_imgs.mock_calls[0]
    assert args[0] == str(Path(root_path) / field_path)
    assert kwargs == {"search": "--E04"}
    assert mock_handler.call_count == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaImageEvent)
    assert event.path == image_path
    assert event.job_id == 4
    assert event.plate_name == "00"


async def test_start_listen(center, caplog):
    """Test start listen for incoming messages."""
    config = {"leica": {}}
    cmd_tuples = [("cmd", "deletelist")]
    commands = [OrderedDict(cmd_tuples)]

    async def mock_receive():
        """Mock receive."""
        await asyncio.sleep(0)
        if commands:
            return [commands.pop()]
        raise asyncio.CancelledError

    mock_handler = AsyncMock()
    center.bus.register(LEICA_COMMAND_EVENT, mock_handler)

    with patch("camacq.plugins.leica.AsyncCAM", autospec=True) as mock_cam_class:
        mock_cam = mock_cam_class.return_value
        mock_cam.receive.side_effect = mock_receive
        await plugins.setup_module(center, config)
        await center.wait_for()
        await center.end(0)

    mock_cam.receive.assert_awaited()
    assert mock_handler.call_count == 1
