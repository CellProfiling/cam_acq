"""Configure and set up control center."""
import logging
import pprint
from pkg_resources import resource_filename

import camacq.config as config_util
from camacq.config import DEFAULT_CONFIG_TEMPLATE
import camacq.log as log_util
from camacq.control import Control

_LOGGER = logging.getLogger(__name__)


def setup_dict(config):
    """Set up control center from config dict."""
    log_util.enable_log(config)
    _LOGGER.debug('Contents of config:\n%s', pprint.pformat(config))
    center = Control(config)
    return center


def setup_file(config_file, cmd_args):
    """Set up control center from config file and command line args."""
    min_config_template = resource_filename(__name__, DEFAULT_CONFIG_TEMPLATE)
    config = config_util.load_config_file(min_config_template)
    user_config = config_util.load_config_file(config_file)
    user_config.update(cmd_args)  # merge config dict with command line args
    config.update(user_config)
    center = setup_dict(config)
    return center
