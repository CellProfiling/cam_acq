"""Handle the config file."""

from importlib import resources
import logging
import os
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

_LOGGER = logging.getLogger(__name__)

CONFIG_DIR_NAME = ".camacq"
YAML_CONFIG_FILE = "config.yml"
DEFAULT_CONFIG_TEMPLATE = "data/config.yml"


def get_default_config_dir():
    """Get the default configuration directory based on OS.

    Returns
    -------
    str
        Return the path to the configuration directory.
    """
    data_dir = os.getenv("APPDATA") if os.name == "nt" else Path.home()
    return (Path(data_dir) / CONFIG_DIR_NAME).resolve()


def find_config_file(config_dir):
    """Find the configuration file in the configuration directory.

    Parameters
    ----------
    config_dir : pathlib.Path
        The path to the configuration directory.

    Returns
    -------
    pathlib.Path
        Return path to the configuration file if found, None if not
        found.
    """
    config_path = config_dir / YAML_CONFIG_FILE

    return config_path if config_path.is_file() else None


def load_config_file(path):
    """Parse a YAML configuration file.

    Parameters
    ----------
    path : pathlib.Path
        The path to the configuration YAML file.

    Returns
    -------
    dict
        Return a dict with the configuration contents.
    """
    yaml = YAML()
    try:
        with open(path, "r", encoding="utf-8") as yml_file:
            cfg = yaml.load(yml_file)
    except YAMLError as exc:
        _LOGGER.error("Error reading YAML configuration file %s", path)
        raise YAMLError(exc) from exc
    if not isinstance(cfg, dict):
        _LOGGER.error(
            "The configuration file %s does not contain a dictionary",
            path.name,
        )
        raise TypeError()
    return cfg


def create_default_config(config_dir):
    """Create a default config file in given configuration directory.

    Parameters
    ----------
    config_dir : pathlib.Path
        The path to the configuration directory.

    Returns
    -------
    pathlib.Path
        Return path to new configuration file if success, None if
        failed.
    """
    config_path = config_dir / YAML_CONFIG_FILE
    default_config_template = resources.files(__package__) / DEFAULT_CONFIG_TEMPLATE
    data = load_config_file(Path(default_config_template))
    yaml = YAML()

    try:
        with open(config_path, "w", encoding="utf-8") as config_file:
            yaml.dump(data, config_file)
    except OSError:
        _LOGGER.error("Unable to create default configuration file %s", config_path)
        return None

    return config_path


def ensure_config_exists(config_dir):
    """Ensure configuration file exists in the configuration directory.

    Create a default configuration file if needed.

    Parameters
    ----------
    config_dir : pathlib.Path
        The path to the configuration directory.

    Returns
    -------
    pathlib.Path
        Return path to the configuration file.
    """
    config_path = find_config_file(config_dir)

    if config_path is None:
        print("Unable to find configuration. Creating default one in", config_dir)
        config_path = create_default_config(config_dir)

    return config_path
