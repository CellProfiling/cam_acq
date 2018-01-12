"""Test helper module."""
from mock import patch

from camacq import helper


def test_setup_modules_api(center, caplog):
    """Test setup_all_modules."""
    config = {'api': {'leica': None}}
    parent = helper.FeatureParent()
    with patch('camacq.api.leica.CAM'):
        helper.setup_all_modules(
            center, config, 'camacq.api', add_child=parent.add_child)
    assert 'Setting up camacq.api.leica package' in caplog.text


def test_setup_modules_plugins(center, caplog):
    """Test setup_all_modules plugins package."""
    config = {'plugins': {'gain': {}}}
    helper.setup_all_modules(center, config, 'camacq.plugins')
    assert 'Setting up camacq.plugins.gain module' in caplog.text
    assert 'No objective selected' in caplog.text


def test_setup_modules_camacq(center, caplog):
    """Test setup_all_modules camacq package."""
    config = {'sample': {}}
    helper.setup_all_modules(center, config, 'camacq')
    assert 'Setting up camacq.sample module' in caplog.text
    assert 'Setting up sample' in caplog.text
