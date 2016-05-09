"""Main module."""
import argparse
import logging
import os
import re
import socket
import sys

from pkg_resources import resource_string

import config
import log
from control import Control

_LOGGER = logging.getLogger(__name__)


def check_dir_arg(path):
    """Check that argument is a directory."""
    # remove if not needed
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            'String {} is not a path to a directory'.format(path))


def check_file_arg(path):
    """Check that argument is a file."""
    # remove if not needed
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            'String {} is not a path to a file'.format(path))


def check_well_arg(arg):
    """Check that argument is valid well."""
    try:
        return re.match(r'^U\d\d--V\d\d$', arg).group(0)
    except AttributeError:
        raise argparse.ArgumentTypeError(
            'String {} does not match required format'.format(arg))


def check_field_arg(arg):
    """Check that argument is valid field."""
    try:
        return re.match(r'^X\d\d--Y\d\d$', arg).group(0)
    except AttributeError:
        raise argparse.ArgumentTypeError(
            'String {} does not match required format'.format(arg))


def check_ip_arg(addr):
    """Check that addr argument is valid ip address."""
    try:
        socket.inet_aton(addr)
        # legal
        return addr
    except socket.error:
        # not legal
        raise argparse.ArgumentTypeError(
            'String {} is not a valid ip address'.format(addr))


def check_log_level(loglevel):
    """Validate log level and return it if valid."""
    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise argparse.ArgumentTypeError(
            'String {} is not a valid log level'.format(loglevel))
    else:
        return numeric_level


def parse_command_line(argv):
    """Parse the provided command line."""
    parser = argparse.ArgumentParser(
        description='Control a Leica microscope through CAM interface.')
    parser.add_argument(
        '--imaging_dir',
        type=check_dir_arg,
        help='the path to the directory where images are exported')
    parser.add_argument(
        # #TODO:0 Replace working_dir with resource api call for all data files
        # trello:3kgNjgJs
        # instead of looking in the working dir.
        # foo_config = resource_string(__name__, 'foo.conf')
        '-w',
        '--working-dir',
        dest='working_dir',
        type=check_dir_arg,
        default=os.path.dirname(os.path.abspath(__file__)),
        help='the path to the working directory of this program')
    parser.add_argument(
        '-g',
        '--init-gain',
        dest='init_gain',
        type=check_file_arg,
        help='the path to the csv file with start gain values')
    parser.add_argument(
        '-W',
        '--last-well',
        dest='last_well',
        default='U11--V07',
        type=check_well_arg,
        help='the id of the last well in the experiment, e.g. U11--V07')
    parser.add_argument(
        '-F',
        '--last-field',
        dest='last_field',
        default='X01--Y01',
        type=check_field_arg,
        help='the id of the last field in each well, e.g. X01--Y01')
    parser.add_argument(
        '--x-fields',
        dest='x_fields',
        default=2,
        type=int,
        help='the number (int) of fields on x axis in each well, e.g. 2')
    parser.add_argument(
        '--y-fields',
        dest='y_fields',
        default=2,
        type=int,
        help='the number (int) of fields on y axis in each well, e.g. 2')
    parser.add_argument(
        '-j',
        '--first-job',
        dest='first_job',
        default=1,
        type=int,
        help=('the integer marking the order of the first experiment job in\
              the patterns'))
    parser.add_argument(
        '-c',
        '--coord-file',
        dest='coord_file',
        type=check_file_arg,
        help='the path to the csv file with selected coordinates')
    parser.add_argument(
        '-t',
        '--template-file',
        dest='template_file',
        type=check_file_arg,
        help='the path to the csv file with template layout')
    parser.add_argument(
        '-G',
        '--input-gain',
        dest='input_gain',
        type=check_file_arg,
        help='the path to the csv file with calculated gain values')
    parser.add_argument(
        'host',
        type=check_ip_arg,
        help='the ip address of the host server, i.e. the microscope')
    objectives = parser.add_mutually_exclusive_group(required=True)
    objectives.add_argument(
        '--end-10x',
        dest='end_10x',
        action='store_true',
        help='an option to activate 10x objective as last objective in\
             experiment')
    objectives.add_argument(
        '--end-40x',
        dest='end_40x',
        action='store_true',
        help='an option to activate 40x objective as last objective in\
             experiment')
    objectives.add_argument(
        '--end-63x',
        dest='end_63x',
        action='store_true',
        help='an option to activate 63x objective as last objective in\
             experiment')
    parser.add_argument(
        '--gain-only',
        dest='gain_only',
        action='store_true',
        help='an option to activate only running the gain job')
    parser.add_argument(
        '--log-level',
        dest='log_level',
        type=check_log_level,
        help='an option to specify lowest log level to log')
    parser.add_argument(
        '-C',
        '--config',
        dest='config_dir',
        default=config.get_default_config_dir(),
        help='the path to camacq configuration directory')
    args = parser.parse_args(argv)
    if args.imaging_dir:
        args.imaging_dir = os.path.normpath(args.imaging_dir)
    if args.working_dir:
        args.working_dir = os.path.normpath(args.working_dir)
    if args.init_gain is None:
        args.init_gain = resource_string(__name__, 'data/10x_gain.csv')
    else:
        args.init_gain = os.path.normpath(args.init_gain)
    if args.coord_file:
        args.coord_file = os.path.normpath(args.coord_file)
    if args.template_file:
        args.template_file = os.path.normpath(args.template_file)
    if args.input_gain:
        args.input_gain = os.path.normpath(args.input_gain)
    if args.config_dir:
        args.config_dir = os.path.normpath(args.config_dir)

    return args


def ensure_config_path(config_dir):
    """Validate the configuration directory."""
    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        if config_dir != config.get_default_config_dir():
            print(('Fatal Error: Specified configuration directory does '
                   'not exist {} ').format(config_dir))
            sys.exit(1)

        try:
            os.mkdir(config_dir)
        except OSError:
            print(('Fatal Error: Unable to create default configuration '
                   'directory {} ').format(config_dir))
            sys.exit(1)


def ensure_config_file(config_dir):
    """Ensure configuration file exists."""
    config_path = config.ensure_config_exists(config_dir)

    if config_path is None:
        print('Error getting configuration path')
        sys.exit(1)

    return config_path


def main(argv):
    """Main function."""
    # Parse command line arguments
    args = parse_command_line(argv)
    config_dir = os.path.join(os.getcwd(), args.config_dir)
    ensure_config_path(config_dir)
    config_file = ensure_config_file(config_dir)
    cfg = config.load_config_file(config_file)
    if not cfg:
        print('Could not load config file at:', config_file)
        sys.exit(1)
    log.enable_log(args, config_instance=cfg['logging'])
    _LOGGER.info('CONFIG: %s', cfg)

    control = Control(args)
    control.control()

if __name__ == '__main__':
    main(sys.argv)
