"""Handle logging."""

import logging
import logging.config
import logging.handlers
import os
from pathlib import Path

import colorlog

from camacq.const import CONFIG_DIR, LOG_LEVEL

LOG_FILENAME = "camacq.log"
_LOGGER = logging.getLogger(__name__)


def check_path(path):
    """Check that path to config exists and is writable for logging.

    Parameters
    ----------
    path : pathlib.Path
        The path to the log file or log directory.

    Returns
    -------
    bool
        Return True if path exists and is writable.
    """
    if (
        path.is_file()
        and os.access(path, os.W_OK)
        or path.parent.is_dir()
        and os.access(path.parent, os.W_OK)
    ):
        return True
    _LOGGER.error("Unable to access log file %s (access denied)", path)
    return False


def enable_log(config):
    """Enable logging.

    Parameters
    ----------
    config : dict
        The dict with the configuration.
    """
    logging.basicConfig(level=logging.INFO)
    root_logger = logging.getLogger()
    # basicConfig has added a StreamHandler
    # '%(log_color)s%(levelname)s:%(name)s:%(message)s'
    # '%(asctime)s;%(name)-16s;%(levelname)-8s;%(message)s'
    log_format = "%(asctime)s;%(levelname)-5s;%(threadName)-10s;%(name)-18s;%(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    color_format = f"%(log_color)s{log_format}"
    root_logger.handlers[0].setFormatter(
        colorlog.ColoredFormatter(
            color_format,
            datefmt=date_format,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            },
        )
    )
    log_config = config.get("logging")
    if log_config:
        log_path = log_config["handlers"]["filelog"]["filename"]
        if log_path and check_path(Path(log_path)):
            logging.config.dictConfig(log_config)
    else:  # get log path from default config dir
        _LOGGER.info("No config for logging supplied")
        log_path = config[CONFIG_DIR] / LOG_FILENAME
        _LOGGER.info("Using default log path at: %s", log_path)
        if check_path(log_path):
            filelog = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=1048576, backupCount=9, encoding="utf-8", delay=0
            )
            filelog.setLevel(logging.WARNING)
            formatter = logging.Formatter(
                "%(asctime)s;%(name)-18s;%(levelname)-8s;%(message)s"
            )
            filelog.setFormatter(formatter)
            logging.getLogger("").addHandler(filelog)
    if LOG_LEVEL in config:
        log_level = config[LOG_LEVEL]
        root_logger.setLevel(log_level)
        root_logger.handlers[0].setLevel(config[LOG_LEVEL])
    # Silence matplotlib spam at debug level.
    logger = logging.getLogger("matplotlib")
    logger.setLevel(logging.INFO)
