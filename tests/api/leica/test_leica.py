"""Test Leica API."""
import asyncio
import os
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import asynctest
import pytest
from leicacam.async_cam import AsyncCAM

from camacq import api as base_api
from camacq.api.leica import (LEICA_COMMAND_EVENT, LEICA_START_COMMAND_EVENT,
                              LEICA_STOP_COMMAND_EVENT, LeicaApi,
                              LeicaCommandEvent, LeicaImageEvent,
                              LeicaStartCommandEvent, LeicaStopCommandEvent,
                              setup_package)

# pylint: disable=redefined-outer-name, len-as-condition
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


@pytest.fixture
def api(center):
    """Return a leica api instance."""
    config = {'api': {'leica': {}}}
    client = asynctest.Mock(AsyncCAM(loop=center.loop))
    mock_api = LeicaApi(center, config, client)

    def register_mock_api(center, config):
        """Register a mock api package."""
        base_api.register_api(center, 'test_api', mock_api)

    with asynctest.patch('camacq.api.leica.setup_package') as leica_setup:
        leica_setup.side_effect = register_mock_api
        center.loop.run_until_complete(
            base_api.setup_package(center, {'api': {'leica': {}}}))
        yield mock_api


@pytest.fixture
def get_imgs():
    """Mock leica helper get_imgs."""
    with patch('camacq.api.leica.get_imgs') as mock_get_imgs:
        yield mock_get_imgs


@pytest.fixture
def mock_socket():
    """Mock a socket."""
    with patch('socket.socket') as mock_socket_class:
        _mock_socket = MagicMock()
        mock_socket_class.return_value = _mock_socket
        yield _mock_socket


async def test_setup_bad_socket(center, caplog, api):
    """Test setup leica api package with bad host or port."""
    api.client.connect.side_effect = OSError()
    config = {'api': {'leica': {}}}
    await setup_package(center, config)
    assert 'Connecting to server localhost failed:' in caplog.text


async def test_send(api):
    """Test the leica api send method."""
    cmd_string = '/cmd:deletelist'
    cmd_tuples = [('cmd', 'deletelist')]
    api.client.receive.return_value = OrderedDict(cmd_tuples)
    api.client.send.return_value = api.receive([OrderedDict(cmd_tuples)])
    mock_handler = asynctest.CoroutineMock()
    api.center.bus.register(LEICA_COMMAND_EVENT, mock_handler)

    await api.send(cmd_string)

    assert len(api.client.send.mock_calls) == 1
    _, args, _ = api.client.send.mock_calls[0]
    assert args[0] == cmd_tuples
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaCommandEvent)
    assert event.command == cmd_string


async def test_start_imaging(api):
    """Test the leica api start imaging method."""
    event_string = '/inf:scanstart'
    cmd_tuples = [('cmd', 'startscan')]
    start_event_tuples = [('inf', 'scanstart')]
    api.client.send.return_value = api.receive([
        OrderedDict(cmd_tuples), OrderedDict(start_event_tuples)])
    mock_handler = asynctest.CoroutineMock()
    api.center.bus.register(LEICA_START_COMMAND_EVENT, mock_handler)

    await api.start_imaging()

    assert len(api.client.send.mock_calls) == 1
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == event_string


async def test_stop_imaging(api):
    """Test the leica api stop imaging method."""
    event_string = '/inf:scanfinished'
    stop_event_tuples = [('inf', 'scanfinished')]
    cmd_tuples = [('cmd', 'stopscan')]
    api.client.send.return_value = api.receive([
        OrderedDict(cmd_tuples), OrderedDict(stop_event_tuples)])
    mock_handler = asynctest.CoroutineMock()
    api.center.bus.register(LEICA_STOP_COMMAND_EVENT, mock_handler)

    await api.stop_imaging()

    assert len(api.client.send.mock_calls) == 1
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the second is the event.
    event = args[1]
    assert isinstance(event, LeicaStopCommandEvent)
    assert event.command == event_string


async def test_receive(api, get_imgs):
    """Test the leica api receive method."""
    image_path = (
        'subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/'
        'field--X01--Y01/image--L0000--S00--U00--V00--J15--E04--O01'
        '--X01--Y01--T0000--Z00--C00.ome.tif')
    cmd_tuples = [(
        'relpath',
        'subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X01--Y01'
        '/image--L0000--S00--U00--V00--J15--E04--O01'
        '--X01--Y01--T0000--Z00--C00.ome.tif')]
    field_path = (
        'subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X01--Y01')
    root_path = '/root'
    config = {'api': {'leica': {'imaging_dir': root_path}}}
    api.config = config
    image_path = os.path.join(root_path, image_path)
    get_imgs.return_value = [image_path]
    mock_handler = asynctest.CoroutineMock()
    api.center.bus.register('image_event', mock_handler)

    await api.receive([OrderedDict(cmd_tuples)])

    assert len(get_imgs.mock_calls) == 1
    _, args, kwargs = get_imgs.mock_calls[0]
    assert args[0] == os.path.join(root_path, field_path)
    assert kwargs == dict(search='--E04')
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaImageEvent)
    assert event.path == image_path
    assert event.job_id == 4
    assert event.plate_name == '00'


async def test_start_listen(center, caplog):
    """Test start listen for incoming messages."""
    config = {'api': {'leica': {}}}
    cmd_tuples = [('cmd', 'deletelist')]

    async def mock_receive():
        """Mock receive."""
        await asyncio.sleep(0)
        return [OrderedDict(cmd_tuples)]

    mock_handler = asynctest.CoroutineMock()
    center.bus.register(LEICA_COMMAND_EVENT, mock_handler)

    with patch('camacq.api.leica.AsyncCAM') as mock_cam_class:
        mock_cam_class.return_value = mock_cam = asynctest.Mock(
            AsyncCAM(loop=center.loop))
        mock_cam.receive.return_value = mock_receive()
        await setup_package(center, config)
        await center.wait_for()
        await center.end(0)

    mock_cam.receive.assert_awaited()
    assert len(mock_handler.mock_calls) == 1
