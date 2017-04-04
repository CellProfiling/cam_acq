"""Test config."""
import os
import tempfile

import pytest

import camacq.config as config_util

# pylint: disable=redefined-outer-name


@pytest.fixture
def config_dir():
    """Return a path to temporary dir."""
    temp_dir = tempfile.gettempdir()
    yield temp_dir
    config_path = os.path.join(temp_dir, 'config.yml')
    if not os.path.isfile(config_path):
        return
    os.remove(config_path)


def test_ensure_config(config_dir):
    """Test that a default config can be created."""
    config_path = config_util.ensure_config_exists(config_dir)
    assert config_path == os.path.join(config_dir, 'config.yml')
