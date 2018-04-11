"""Test helper module."""
import pytest
from mock import patch

from camacq import helper

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_leica_setup():
    """Mock setup package."""
    with patch('camacq.api.leica.setup_package') as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_sample_setup():
    """Mock setup module."""
    with patch('camacq.sample.setup_module') as mock_setup:
        yield mock_setup


def test_setup_modules_api(center, mock_leica_setup):
    """Test setup_all_modules."""
    config = {'api': {'leica': {}}}
    parent = helper.FeatureParent()
    helper.setup_all_modules(
        center, config, 'camacq.api', add_child=parent.add_child)
    assert len(mock_leica_setup.mock_calls) == 1
    _, args, kwargs = mock_leica_setup.mock_calls[0]
    assert args == (center, config)
    assert kwargs == dict(add_child=parent.add_child)


def test_setup_modules_camacq(center, mock_sample_setup):
    """Test setup_all_modules camacq package."""
    config = {'sample': {}}
    helper.setup_all_modules(center, config, 'camacq')
    assert len(mock_sample_setup.mock_calls) == 1
    _, args, kwargs = mock_sample_setup.mock_calls[0]
    assert args == (center, config)
    assert kwargs == {}
