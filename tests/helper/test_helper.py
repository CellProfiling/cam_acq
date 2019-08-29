"""Test helper module."""
import asynctest
import pytest

from camacq import helper

# pylint: disable=redefined-outer-name
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


@pytest.fixture
def mock_leica_setup():
    """Mock setup package."""
    with asynctest.patch("camacq.api.leica.setup_package") as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_gain_setup():
    """Mock setup module."""
    with asynctest.patch("camacq.plugins.gain.setup_module") as mock_setup:
        yield mock_setup


async def test_setup_modules_package(center, mock_leica_setup):
    """Test setup_all_modules."""
    config = {"api": {"leica": {}}}
    await helper.setup_all_modules(center, config, "camacq.api")
    assert len(mock_leica_setup.mock_calls) == 1
    _, args, _ = mock_leica_setup.mock_calls[0]
    assert args == (center, config)


async def test_setup_modules_module(center, mock_gain_setup):
    """Test setup_all_modules camacq package."""
    config = {"plugins": {"gain": {}}}
    await helper.setup_all_modules(center, config, "camacq")
    assert len(mock_gain_setup.mock_calls) == 1
    _, args, kwargs = mock_gain_setup.mock_calls[0]
    assert args == (center, config)
    assert kwargs == {}
