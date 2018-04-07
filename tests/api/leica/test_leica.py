"""Test Leica API."""
import os
import socket
from collections import OrderedDict

import pytest
from mock import MagicMock, patch

from camacq.api.leica import (LeicaApi, LeicaImageEvent,
                              LeicaStartCommandEvent, LeicaStopCommandEvent,
                              setup_package)

# pylint: disable=redefined-outer-name


@pytest.fixture
def client():
    """Return a mock client."""
    return MagicMock()


@pytest.fixture
def api(center, client):
    """Return a leica api instance."""
    return LeicaApi(center, client)


@pytest.fixture
def get_imgs():
    """Mock leica helper get_imgs."""
    with patch('camacq.api.leica.get_imgs') as mock_get_imgs:
        yield mock_get_imgs


@pytest.fixture
def mock_socket():
    """Mock a socket."""
    with patch('socket.socket') as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        yield mock_socket


def test_setup_bad_socket(center, caplog, mock_socket):
    """Test setup leica api package with bad host or port."""
    mock_socket.connect.side_effect = socket.error()
    setup_package(center, {})
    assert 'Connecting to server localhost failed:' in caplog.text


def test_send(api):
    """Test the leica api send method."""
    cmd_string = '/cmd:startscan'
    cmd_tuples = [('cmd', 'startscan')]
    api.client.wait_for.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register(LeicaStartCommandEvent, mock_handler)

    api.send(cmd_string)

    assert len(api.client.send.mock_calls) == 1
    _, args, _ = api.client.send.mock_calls[0]
    assert args[0] == cmd_tuples
    assert len(api.client.wait_for.mock_calls) == 1
    _, _, kwargs = api.client.wait_for.mock_calls[0]
    cmd, value = cmd_tuples[0]
    assert kwargs == dict(cmd=cmd, value=value, timeout=0.3)
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == cmd_string


def test_start_imaging(api):
    """Test the leica api start imaging method."""
    cmd_string = '/cmd:startscan'
    cmd_tuples = [('cmd', 'startscan')]
    api.client.start_scan.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register(LeicaStartCommandEvent, mock_handler)

    api.start_imaging()

    assert len(api.client.start_scan.mock_calls) == 1
    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == cmd_string


def test_stop_imaging(api):
    """Test the leica api stop imaging method."""
    event_string = '/scanfinished:scanfinished'
    stop_event_tuples = [('scanfinished', 'scanfinished')]
    cmd_tuples = [('cmd', 'stopscan')]
    api.client.stop_scan.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register(LeicaStopCommandEvent, mock_handler)

    api.stop_imaging()

    assert len(api.client.stop_scan.mock_calls) == 1

    # pylint: disable=fixme
    # FIXME: Check exactly what is returned from the server when scan finishes.

    api.client.receive.return_value = [OrderedDict(stop_event_tuples)]

    api.receive()

    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaStopCommandEvent)
    assert event.command == event_string


def test_receive(api, get_imgs):
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
    api.center.config['imaging_dir'] = root_path
    image_path = os.path.join(root_path, image_path)
    api.client.receive.return_value = [OrderedDict(cmd_tuples)]
    get_imgs.return_value = [image_path]
    mock_handler = MagicMock()
    api.center.bus.register(LeicaImageEvent, mock_handler)

    api.receive()

    assert len(api.client.receive.mock_calls) == 1
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
