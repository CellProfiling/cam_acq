"""Test helper module."""
import asynctest
import pytest

from camacq import helper

# pylint: disable=redefined-outer-name
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


@pytest.fixture
def mock_gain_setup():
    """Mock setup module."""
    with asynctest.patch("camacq.plugins.gain.setup_module") as mock_setup:
        yield mock_setup


async def test_setup_one_module(center, mock_gain_setup):
    """Test set up one module."""
    config = {"plugins": {"gain": {}}}
    gain_module = helper.get_module("camacq.plugins", "gain")
    await helper.setup_one_module(center, config, gain_module)
    assert len(mock_gain_setup.mock_calls) == 1
    _, args, kwargs = mock_gain_setup.mock_calls[0]
    assert args == (center, config)
    assert kwargs == {}


async def test_missing_setup(center, caplog):
    """Test missing setup function."""
    const_module = helper.get_module("camacq", "const")
    await helper.setup_one_module(center, {}, const_module)
    assert "Missing setup_module function in module const" in caplog.text


async def test_many_module_matches(center):
    """Test many module matches."""
    with pytest.raises(ValueError):
        helper.get_module("camacq.plugins", "")
