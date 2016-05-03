"""Helper functions for camacq."""
import csv
import logging
import os
import re
from collections import defaultdict

from matrixscreener import experiment

_LOGGER = logging.getLogger(__name__)


def send(cam, commands):
    """Send each command in commands.

    Parameters
    ----------
    cam : instance
        CAM instance.
    commands : list
        List of list of commands as tuples.
        Example: [[('cmd', 'enableall'), ('value', 'true')],
                  [('cmd', 'deletelist')]]

    Returns
    -------
    list
        Return a list of OrderedDict with all received replies.
    """
    replies = []
    for cmd in commands:
        _LOGGER.debug(cmd)
        reply = cam.send(cmd)
        _LOGGER.debug(reply)
        replies.extend(reply)
    return replies


def read_csv(path, index, header):
    """Read a csv file and return a defaultdict of lists.

    Parameters
    ----------
    path : string
        Path to csv file.
    index : string
        Index can be any of the column headers of the csv file.
        The column under index will be used as keys in the returned
        defaultdict.
    header : list
        List of strings with any of the column headers of the csv file,
        except index. Each item in header will be used to add the
        corresponding column and row value to the list of the row in the
        returned defaultdict.

    Returns
    -------
    defaultdict(list)
        Return a defaultdict of lists with the contents of the csv file,
        indicated by the index and header parameters. Each item in the
        defaultdict will represent a row or part of a row from the csv file.
    """
    dict_list = defaultdict(list)
    with open(path) as file_handle:
        reader = csv.DictReader(file_handle)
        for dictionary in reader:
            for key in header:
                dict_list[dictionary[index]].append(dictionary[key])
    return dict_list


def write_csv(path, dict_list, header):
    """Write a defaultdict of lists as a csv file.

    Parameters
    ----------
    path : string
        Path to csv file.
    dict_list : defaultdict(list)
        The defaultdict of lists that should be written as a csv file.
    header : list
        List of strings with the wanted column headers of the csv file.
        The items in header should correspond to the key of the dictionary
        and all items in the list for a key.
    """
    with open(path, 'wb') as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(header)
        for key, value in dict_list.iteritems():
            writer.writerow([key] + value)


def get_scan_paths(scan, compartments, conditions):
    """Get all paths for a compartment that match condition.

    Parameters
    ----------
    scan : instance
        Experiment instance.
    compartments : string
        The name of the compartments: 'slides', 'wells', 'fields' or 'images'.
    conditions : list
        List of tuples or strings that should match the paths of the found
        compartments. If a condition is a tuple, experiment.attribute_as_str
        will be used to look up the name of attribute [A-Z] in found path and
        match against the path provided in the tuple. Tuple[0] should be the
        provided path and tuple[1] should be the name of attribute to look up.

    Returns
    -------
    list
        Return a list with all found paths in scan for the compartments,
        that matched the conditions.
    """
    paths = []
    if compartments not in ('slides', 'wells', 'fields', 'images'):
        _LOGGER.error(
            'Compartments: %s is not any of: slides, wells, fields or images',
            compartments)
        return None
    for comp in getattr(scan, compartments):
        test = True
        for cond in conditions:
            if isinstance(cond, tuple):
                test = test and cond[0] in experiment.attribute_as_str(
                    comp, cond[1])
            elif isinstance(cond, str):
                if len(cond) <= len(comp):
                    test = test and cond in comp
                else:
                    test = test and comp in cond
            else:
                _LOGGER.error('Conditions must hold tuples or strings')
                return None
        if test:
            paths.append(comp)
    return paths


def find_image_path(reply, root):
    """Parse the reply from the server to find the correct file path."""
    paths = reply.split('\\')
    for path in paths:
        root = os.path.join(root, path)
    return root


def find_scan(path):
    """Find scan path by traversing up the tree from path iteratively.

    Parameters
    ----------
    path : string
        Path to file or directory from where to start searching for scan path.

    Returns
    -------
    instance
        Return Experiment instance with found scan path.
    """
    scan = experiment.Experiment(path)
    # pylint: disable=no-member
    while scan.basename not in 'slide--S00':
        scan = experiment.Experiment(scan.dirname)
    return experiment.Experiment(scan.dirname)


def format_new_name(scan, imgp, root=None, new_attr=None):
    """Create filename from image path and replace specific attribute id(s).

    Parameters
    ----------
    scan : instance
        Experiment instance.
    imgp : string
        Path to image.
    root : string
        Path to directory where path should start.
    new_attr : dict
        Dictionary which maps experiment attributes to new attribute ids.
        The new attribute ids will replace the old ids for the corresponding
        attributes.

    Returns
    -------
    string
        Return new path to image.
    """
    if root is None:
        root = get_scan_paths(scan, 'slides', [imgp])[0]

    path = 'U{}--V{}--E{}--X{}--Y{}--Z{}--C{}.ome.tif'.format(
        *(experiment.attribute_as_str(imgp, attr)
          for attr in ('U', 'V', 'E', 'X', 'Y', 'Z', 'C')))
    if new_attr:
        for attr, attr_id in new_attr.iteritems():
            path = re.sub(
                attr + r'\d\d', attr + attr_id, path)

    return os.path.normpath(os.path.join(root, path))


def rename_imgs(scan, imgp, f_job):
    """Rename image and return new name."""
    if experiment.attribute(imgp, 'E') == f_job:
        new_name = format_new_name(scan, imgp)
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 0):
        new_name = format_new_name(scan, imgp, 'C', '01')
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 1):
        new_name = format_new_name(scan, imgp, 'C', '02')
    elif experiment.attribute(imgp, 'E') == f_job + 2:
        new_name = format_new_name(scan, imgp, 'C', '03')
    else:
        new_name = imgp
    os.rename(imgp, new_name)
    return new_name
