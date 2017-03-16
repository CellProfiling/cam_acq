"""Configure and set up control center."""
import logging

import camacq.config as config_util
import camacq.log as log_util
from camacq.control import Control

_LOGGER = logging.getLogger(__name__)


def setup_dict(config, cmd_args=None):
    """Set up control center from config dict."""
    log_util.enable_log(cmd_args, config_instance=config['logging'])
    _LOGGER.debug('CONFIG: %s', config)
    center = Control(cmd_args)
    return center


def setup_file(config_file, cmd_args=None):
    """Set up control center from config file."""
    config = config_util.load_config_file(config_file)
    # FIXME: Merge cmd_args into config dict.  pylint: disable=fixme
    center = setup_dict(config, cmd_args)
    return center
