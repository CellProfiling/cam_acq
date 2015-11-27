import os
import logging
import config

_LOGGER = logging.getLogger(__name__)


def check_path(path):
    # if os.path.isfile(path) and os.access(path, os.W_OK):
    if (os.path.isfile(path) and os.access(path, os.W_OK)) or \
       (not os.path.isfile(path) and os.access(config.config_dir, os.W_OK)):
        return True
    else:
        _LOGGER.error(
            'Unable to access log file %s (access denied)', path)
        return False


def enable_log(args, config_file=None):  # pass the logging part of the config
    logging.basicConfig(level=logging.INFO,
                        format='%(name)-12s: %(levelname)-8s %(message)s',
                        # datefmt='%m-%d %H:%M',
                        )
    if config_file is not None:  # add try+except to catch wrong config
        if check_path(config_file['handlers']['filelog']['filename']):
            logging.config.dictConfig(config)
    else:  # get log path from default config dir
        path = os.path.join(config.config_dir, 'cam_acq.log')
        if check_path(path):
            filelog = logging.handlers.RotatingFileHandler(
                path, maxBytes=1024, backupCount=9, encoding='utf-8', delay=0)
            filelog.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s;%(name)-12s;%(levelname)-8s;%(message)s')
            filelog.setFormatter(formatter)
            logging.getLogger('').addHandler(filelog)
