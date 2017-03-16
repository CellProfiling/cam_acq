"""Configure and set up control center."""
import logging

import camacq.config as config_util
import camacq.log as log_util
from camacq.control import Control

_LOGGER = logging.getLogger(__name__)


def setup_dict(config):
    """Set up control center from config dict."""
    log_util.enable_log(config)
    _LOGGER.debug('CONFIG: %s', config)
    center = Control(config)
    return center


def setup_file(config_file, cmd_args):
    """Set up control center from config file and command line args."""
    config = config_util.load_config_file(config_file)
    config.update(vars(cmd_args))  # merge config dict with command line args
    center = setup_dict(config)
    return center
