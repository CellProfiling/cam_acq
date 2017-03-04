"""Handle logging."""
import logging
import logging.config
import logging.handlers
import os

import colorlog

LOG_FILENAME = 'camacq.log'
_LOGGER = logging.getLogger(__name__)


def check_path(path):
    """Check that path to config exists and is writable for logging."""
    if os.path.isfile(path) and os.access(path, os.W_OK) or \
       not os.path.isfile(path) and os.access(os.path.dirname(path), os.W_OK):
        return True
    else:
        _LOGGER.error(
            'Unable to access log file %s (access denied)', path)
        return False


def enable_log(args, config_instance=None):
    """Enable logging."""
    logging.basicConfig(level=args.log_level)
    root_logger = logging.getLogger()
    # basicConfig has added a StreamHandler
    # '%(log_color)s%(levelname)s:%(name)s:%(message)s'
    # '%(asctime)s;%(name)-16s;%(levelname)-8s;%(message)s'
    root_logger.handlers[0].setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s;%(levelname)-8s;%(name)-16s;%(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red', }))
    # pass the logging part of the config
    if config_instance is not None:  # add try+except to catch wrong config
        log_path = config_instance['handlers']['filelog']['filename']
        if log_path and check_path(log_path):
            logging.config.dictConfig(config_instance)
        else:  # get log path from default config dir
            log_path = os.path.join(args.config_dir, LOG_FILENAME)
            _LOGGER.info(
                'Using default log path at: %s', log_path)
            if check_path(log_path):
                filelog = logging.handlers.RotatingFileHandler(
                    log_path, maxBytes=1048576, backupCount=9,
                    encoding='utf-8', delay=0)
                filelog.setLevel(logging.WARNING)
                formatter = logging.Formatter(
                    '%(asctime)s;%(name)-16s;%(levelname)-8s;%(message)s')
                filelog.setFormatter(formatter)
                logging.getLogger('').addHandler(filelog)
    else:
        _LOGGER.info('No config for logging supplied')
