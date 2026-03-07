"""Configure and set up control center."""

import logging
from pathlib import Path
from typing import Any

from camacq import plugins
import camacq.config as config_util
from camacq.control import Center
from camacq.helper import setup_one_module
import camacq.log as log_util

_LOGGER = logging.getLogger(__name__)


async def setup_dict(center: Center, config: dict[str, Any]) -> None:
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
    await setup_one_module(center, config, plugins)


async def setup_file(config_file: Path, cmd_args: dict[str, Any]) -> Center:
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
    center = Center()
    user_config = await center.add_executor_job(
        config_util.load_config_file, config_file
    )
    user_config.update(cmd_args)  # merge config dict with command line args
    await setup_dict(center, user_config)
    return center
