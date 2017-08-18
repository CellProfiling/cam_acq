"""Main module."""
from __future__ import print_function

import argparse
import logging
import os
import re
import socket
import sys

import camacq.bootstrap as bootstrap
import camacq.config as config_util
from camacq.const import (CONFIG_DIR, COORD_FILE, END_10X, END_40X, END_63X,
                          FIELDS_X, FIELDS_Y, FIRST_JOB, GAIN_ONLY, HOST,
                          IMAGING_DIR, INIT_GAIN, INPUT_GAIN, LOG_LEVEL,
                          OBJECTIVE, PORT, TEMPLATE_FILE)


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


def check_socket_address(value):
    """Check that value is a valid address."""
    try:
        socket.getaddrinfo(value, None)
        return value
    except OSError:
        raise argparse.ArgumentTypeError(
            'String {} is not a valid domain name or ip address'.format(value))


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


def check_obj(value):
    """Check that value is a objective lens."""
    if value in [END_10X, END_40X, END_63X]:
        return value
    else:
        raise argparse.ArgumentTypeError(
            'String {} is not one of: {}, {}, {}'.format(
                value, *[END_10X, END_40X, END_63X]))


def parse_command_line():
    """Parse the provided command line."""
    parser = argparse.ArgumentParser(
        description='Control microscope through client-server program.')
    parser.add_argument(
        IMAGING_DIR,
        type=check_dir_arg,
        help='the path to the directory where images are exported')
    parser.add_argument(
        '-g',
        '--init-gain',
        dest=INIT_GAIN,
        type=check_file_arg,
        help='the path to the csv file with start gain values')
    parser.add_argument(
        '-W',
        '--last-well',
        type=check_well_arg,
        help='the id of the last well in the experiment, e.g. U11--V07')
    parser.add_argument(
        '--x-fields',
        dest=FIELDS_X,
        type=int,
        help='the number (int) of fields on x axis in each well, e.g. 2')
    parser.add_argument(
        '--y-fields',
        dest=FIELDS_Y,
        type=int,
        help='the number (int) of fields on y axis in each well, e.g. 2')
    parser.add_argument(
        '-j',
        '--first-job',
        dest=FIRST_JOB,
        type=int,
        help=('the integer marking the order of the first experiment job in\
              the patterns'))
    parser.add_argument(
        '-c',
        '--coord-file',
        dest=COORD_FILE,
        type=check_file_arg,
        help='the path to the csv file with selected coordinates')
    parser.add_argument(
        '-t',
        '--template-file',
        dest=TEMPLATE_FILE,
        type=check_file_arg,
        help='the path to the csv file with template layout')
    parser.add_argument(
        '-G',
        '--input-gain',
        dest=INPUT_GAIN,
        type=check_file_arg,
        help='the path to the csv file with calculated gain values')
    parser.add_argument(
        '-H',
        '--host',
        dest=HOST,
        type=check_socket_address,
        help='the address of the host server, i.e. the microscope')
    parser.add_argument(
        '-P',
        '--port',
        dest=PORT,
        type=int,
        help='the tcp port of the host server, i.e. the microscope')
    parser.add_argument(
        '-O',
        '--objective',
        dest=OBJECTIVE,
        type=check_obj,
        help='select what objective to use as last objective in experiment')
    parser.add_argument(
        '--gain-only',
        dest=GAIN_ONLY,
        action='store_true',
        help='an option to activate only running the gain job')
    parser.add_argument(
        '--log-level',
        dest=LOG_LEVEL,
        type=check_log_level,
        help='an option to specify lowest log level to log')
    parser.add_argument(
        '-C',
        '--config',
        dest=CONFIG_DIR,
        default=config_util.get_default_config_dir(),
        help='the path to camacq configuration directory')
    args = parser.parse_args()
    if args.imaging_dir:
        args.imaging_dir = os.path.normpath(args.imaging_dir)
    if args.init_gain:
        args.init_gain = os.path.normpath(args.init_gain)
    if args.coord_file:
        args.coord_file = os.path.normpath(args.coord_file)
    if args.template_file:
        args.template_file = os.path.normpath(args.template_file)
    if args.input_gain:
        args.input_gain = os.path.normpath(args.input_gain)
    if args.config_dir:
        args.config_dir = os.path.normpath(args.config_dir)
    cmd_args_dict = vars(args)
    cmd_args_dict = {
        key: val for key, val in cmd_args_dict.iteritems() if val}

    return cmd_args_dict


def ensure_config_path(config_dir):
    """Validate the configuration directory."""
    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        if config_dir != config_util.get_default_config_dir():
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
    config_path = config_util.ensure_config_exists(config_dir)

    if config_path is None:
        print('Error getting configuration path')
        sys.exit(1)

    return config_path


def main():
    """Main function."""
    # Parse command line arguments
    cmd_args = parse_command_line()
    config_dir = os.path.join(os.getcwd(), cmd_args[CONFIG_DIR])
    ensure_config_path(config_dir)
    config_file = ensure_config_file(config_dir)
    center = bootstrap.setup_file(config_file, cmd_args)
    if not center:
        print('Could not load config file at:', config_file)
        sys.exit(1)
    center.start()
    return center.exit_code


if __name__ == '__main__':
    main()
