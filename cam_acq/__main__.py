import os
import sys
import argparse
import re
import socket
import logging
from pkg_resources import resource_string
from control import Control
import log
import config


def check_dir_arg(path):
    # remove if not needed
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            'String {} is not a path to a directory'.format(path))


def check_file_arg(path):
    # remove if not needed
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            'String {} is not a path to a file'.format(path))


def check_well_arg(arg):
    try:
        return re.match("^U\d\d--V\d\d$", arg).group(0)
    except AttributeError:
        raise argparse.ArgumentTypeError(
            'String {} does not match required format'.format(arg))


def check_field_arg(arg):
    try:
        return re.match("^X\d\d--Y\d\d$", arg).group(0)
    except AttributeError:
        raise argparse.ArgumentTypeError(
            'String {} does not match required format'.format(arg))


def check_ip_arg(addr):
    try:
        socket.inet_aton(addr)
        # legal
        return addr
    except socket.error:
        # not legal
        raise argparse.ArgumentTypeError(
            'String {} is not a valid ip address'.format(addr))


def check_log_level(loglevel):
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
        'imaging_dir',
        type=check_dir_arg,
        help='the path to the directory where images are exported')
    parser.add_argument(
        # #TODO:0 Replace working_dir with resource api call for all data files, trello:3kgNjgJs
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
    # #DONE:50 Make end-10x, end-40x and end-63x mutually exclusive, trello:xinb2xIm
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
    # #DONE:0 Finish adding args, parse_command_line(), trello:VjTzfUGv

    return args


def main(argv):
    """Main function"""

    # Parse command line arguments
    args = parse_command_line(argv)
    print(args)  # testing

    log.enable_log(args)
    cfg = config.load_config_file('path/to/config')  # fix this path
    log.enable_log(args, config=cfg['logging'])
    # #DONE:10 Fix args to make control object working, trello:PxoHWv3P
    control = Control(args)

    # #DONE:40 Finish main function, trello:efo8RhDm
    control.control()

if __name__ == '__main__':
    main(sys.argv)
