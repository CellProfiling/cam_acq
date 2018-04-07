"""Test Leica API."""
from collections import OrderedDict

import pytest
from mock import MagicMock

from camacq.api.leica import LeicaApi, LeicaStartCommandEvent

# pylint: disable=redefined-outer-name


@pytest.fixture
def client():
    """Return a mock client."""
    return MagicMock()


@pytest.fixture
def api(center, client):
    """Return a leica api instance."""
    return LeicaApi(center, client)


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
    assert isinstance(args[1], LeicaStartCommandEvent)
    assert args[1].command == cmd_string
