"""Test Leica API."""
import os
import socket
from collections import OrderedDict

import pytest
from mock import MagicMock, patch

from camacq import api as base_api
from camacq.api.leica import (LeicaApi, LeicaImageEvent,
                              LeicaStartCommandEvent, LeicaStopCommandEvent,
                              setup_package)

# pylint: disable=redefined-outer-name, len-as-condition


@pytest.fixture
def client():
    """Return a mock client."""
    return MagicMock()


@pytest.fixture
def api(center, client):
    """Return a leica api instance."""
    config = {'api': {'leica': {}}}
    center.config = config
    mock_api = LeicaApi(center, client)

    def setup_mock_api_package(center, config, add_child=None):
        """Set up a mock api package."""
        add_child('test_api', mock_api)

    with patch('camacq.api.leica.setup_package') as leica_setup:
        leica_setup.side_effect = setup_mock_api_package
        base_api.setup_package(center, {'api': {'leica': {}}})
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
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        yield mock_socket


def test_setup_bad_socket(center, caplog, mock_socket):
    """Test setup leica api package with bad host or port."""
    mock_socket.connect.side_effect = socket.error()
    config = {'api': {'leica': {}}}
    setup_package(center, config)
    assert 'Connecting to server localhost failed:' in caplog.text


def test_send(api):
    """Test the leica api send method."""
    cmd_string = '/cmd:startscan'
    cmd_tuples = [('cmd', 'startscan')]
    event_string = '/inf:scanstart'
    start_event_tuples = [('inf', 'scanstart')]
    api.client.wait_for.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register('start_command_event', mock_handler)

    api.send(cmd_string)
    replies = api.run_job()

    assert len(api.client.send.mock_calls) == 1
    _, args, _ = api.client.send.mock_calls[0]
    assert args[0] == cmd_tuples

    replies = api.run_job()
    api.receive(replies)

    assert len(api.client.wait_for.mock_calls) == 1
    _, _, kwargs = api.client.wait_for.mock_calls[0]
    cmd, value = cmd_tuples[0]
    assert kwargs == dict(cmd=cmd, value=value, timeout=0.2)
    assert len(mock_handler.mock_calls) == 0

    api.receive([OrderedDict(start_event_tuples)])

    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == event_string


def test_start_imaging(api):
    """Test the leica api start imaging method."""
    event_string = '/inf:scanstart'
    cmd_tuples = [('cmd', 'startscan')]
    start_event_tuples = [('inf', 'scanstart')]
    api.client.start_scan.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register('start_command_event', mock_handler)

    api.start_imaging()
    replies = api.run_job()
    api.receive(replies)

    assert len(api.client.start_scan.mock_calls) == 1
    assert len(mock_handler.mock_calls) == 0

    api.receive([OrderedDict(start_event_tuples)])

    assert len(mock_handler.mock_calls) == 1
    _, args, _ = mock_handler.mock_calls[0]
    # The first argument is Center, the seconds is the event.
    event = args[1]
    assert isinstance(event, LeicaStartCommandEvent)
    assert event.command == event_string


def test_stop_imaging(api):
    """Test the leica api stop imaging method."""
    event_string = '/inf:scanfinished'
    stop_event_tuples = [('inf', 'scanfinished')]
    cmd_tuples = [('cmd', 'stopscan')]
    api.client.stop_scan.return_value = OrderedDict(cmd_tuples)
    mock_handler = MagicMock()
    api.center.bus.register('stop_command_event', mock_handler)

    api.stop_imaging()
    replies = api.run_job()
    api.receive(replies)

    assert len(api.client.stop_scan.mock_calls) == 1

    api.receive([OrderedDict(stop_event_tuples)])

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
    config = {'api': {'leica': {'imaging_dir': root_path}}}
    api.center.config = config
    image_path = os.path.join(root_path, image_path)
    get_imgs.return_value = [image_path]
    mock_handler = MagicMock()
    api.center.bus.register('image_event', mock_handler)

    api.receive([OrderedDict(cmd_tuples)])

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
