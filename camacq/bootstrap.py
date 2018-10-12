"""Configure and set up control center."""
import logging

import camacq.config as config_util
import camacq.log as log_util
from camacq.const import PACKAGE
from camacq.control import Center
from camacq.helper import CORE_MODULES, get_module, setup_all_modules

_LOGGER = logging.getLogger(__name__)


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
    center = Center(config)
    # Add core modules.
    for module_name in CORE_MODULES:
        if module_name not in config:
            config[module_name] = {}
        module = get_module(PACKAGE, module_name)
        module.setup_module(center, config)
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
    user_config = config_util.load_config_file(config_file)
    user_config.update(cmd_args)  # merge config dict with command line args
    center = setup_dict(user_config)
    return center
