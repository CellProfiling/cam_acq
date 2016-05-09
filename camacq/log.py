"""Handle logging."""
import logging
import logging.handlers
import os

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
    # pass the logging part of the config
    logging.basicConfig(level=logging.INFO,
                        format='%(name)-12s: %(levelname)-8s %(message)s')
    if config_instance is not None:  # add try+except to catch wrong config
        if check_path(
                config_instance['handlers']['filelog']['filename']):
            logging.config.dictConfig(config_instance)
        else:  # get log path from default config dir
            path = os.path.join(args.config_dir, LOG_FILENAME)
            if check_path(path):
                filelog = logging.handlers.RotatingFileHandler(
                    path, maxBytes=1024, backupCount=9,
                    encoding='utf-8', delay=0)
                filelog.setLevel(logging.DEBUG)
                formatter = logging.Formatter(
                    '%(asctime)s;%(name)-12s;%(levelname)-8s;%(message)s')
                filelog.setFormatter(formatter)
                logging.getLogger('').addHandler(filelog)
    else:
        _LOGGER.info('No config for logging supplied')
