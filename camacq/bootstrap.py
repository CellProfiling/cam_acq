"""Configure and set up control center."""
import logging

from pkg_resources import resource_filename

import camacq.config as config_util
import camacq.log as log_util
from camacq.config import DEFAULT_CONFIG_TEMPLATE
from camacq.const import PACKAGE
from camacq.control import Center
from camacq.helper import setup_all_modules

_LOGGER = logging.getLogger(__name__)
CORE_MODULES = ['sample']


def setup_dict(config):
    """Set up control center from config dict.

    Parameters
    ----------
    config : dict
        The config dict.

    Returns
    -------
    Center instance
        Return the Center instance.
    """
    log_util.enable_log(config)
    # Add core modules.
    config.update({module: {} for module in CORE_MODULES})
    center = Center(config)
    setup_all_modules(center, config, PACKAGE)
    return center


def setup_file(config_file, cmd_args):
    """Set up control center from config file and command line args.

    Parameters
    ----------
    config_file : str
        The path to the configuration YAML file.
    cmd_args : dict
        The dict with the command line arguments.

    Returns
    -------
    Center instance
        Return the Center instance.
    """
    min_config_template = resource_filename(__name__, DEFAULT_CONFIG_TEMPLATE)
    config = config_util.load_config_file(min_config_template)
    user_config = config_util.load_config_file(config_file)
    user_config.update(cmd_args)  # merge config dict with command line args
    config.update(user_config)
    center = setup_dict(config)
    return center
