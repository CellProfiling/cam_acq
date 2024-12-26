"""Test config."""

import camacq.config as config_util


def test_ensure_config(tmp_path):
    """Test that a default config can be created."""
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    config_path = config_util.ensure_config_exists(config_dir)
    assert config_path == config_dir / "config.yml"
