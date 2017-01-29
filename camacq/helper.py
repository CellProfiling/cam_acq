"""Helper functions for camacq."""
import csv
import logging
import ntpath
import os
import re
from collections import defaultdict

from matrixscreener import experiment

from camacq.const import BLUE, GREEN, RED, WELL, YELLOW

_LOGGER = logging.getLogger(__name__)


def send(cam, commands):
    """Send each command in commands.

    Parameters
    ----------
    cam : instance
        CAM instance.
    commands : list
        List of list of commands as tuples.

    Returns
    -------
    list
        Return a list of OrderedDict with all received replies.

    Example
    -------
    ::

        send(cam, [[('cmd', 'deletelist')], [('cmd', 'startscan')]])
    """
    replies = []
    for cmd in commands:
        _LOGGER.debug(cmd)
        reply = cam.send(cmd)
        _LOGGER.debug(reply)
        if reply:
            replies.extend(reply)
    return replies


def read_csv(path, index):
    """Read a csv file and return a dict of dicts.

    Parameters
    ----------
    path : str
        Path to csv file.
    index : str
        Index can be any of the column headers of the csv file.
        The column under index will be used as keys in the returned
        dict.

    Returns
    -------
    defaultdict(dict)
        Return a dict of dicts with the contents of the csv file,
        indicated by the index parameter. Each item in the
        dict will represent a row, with index as key, of the csv file.
    """
    csv_map = defaultdict(dict)
    with open(path) as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            key = row.pop(index)
            csv_map[key].update(row)
    return csv_map


def write_csv(path, csv_map, header):
    """Write a dict of dicts as a csv file.

    Parameters
    ----------
    path : str
        Path to csv file.
    csv_map : dict(dict)
        The dict of dicts that should be written as a csv file.
    header : list
        List of strings with the wanted column headers of the csv file.
        The items in header should correspond to the index key of the primary
        dict and all the keys of the secondary dict.
    """
    with open(path, 'wb') as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=header)
        writer.writeheader()
        for index, cells in csv_map.iteritems():
            index_dict = {header[0]: index}
            index_dict.update(cells)
            writer.writerow(index_dict)


def find_image_path(relpath, root):
    """Parse the relpath from the server to find the file path from root.

    Convert from windows path to os path.
    """
    if not relpath:
        return
    paths = []
    while relpath:
        relpath, tail = ntpath.split(relpath)
        paths.append(tail)
    return str(os.path.join(root, *list(reversed(paths))))


def format_new_name(imgp, root=None, new_attr=None):
    """Create filename from image path and replace specific attribute id(s).

    Parameters
    ----------
    imgp : string
        Path to image.
    root : str
        Path to directory where path should start.
    new_attr : dict
        Dictionary which maps experiment attributes to new attribute ids.
        The new attribute ids will replace the old ids for the corresponding
        attributes.

    Returns
    -------
    str
        Return new path to image.
    """
    if root is None:
        root = get_field(imgp)

    path = 'U{}--V{}--E{}--X{}--Y{}--Z{}--C{}.ome.tif'.format(
        *(experiment.attribute_as_str(imgp, attr)
          for attr in ('U', 'V', 'E', 'X', 'Y', 'Z', 'C')))
    if new_attr:
        for attr, attr_id in new_attr.iteritems():
            path = re.sub(attr + r'\d\d', attr + attr_id, path)

    return os.path.normpath(os.path.join(root, path))


def rename_imgs(imgp, f_job):
    """Rename image and return new name."""
    if experiment.attribute(imgp, 'E') == f_job:
        new_name = format_new_name(imgp)
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 0):
        new_name = format_new_name(imgp, new_attr={'C': '01'})
    elif (experiment.attribute(imgp, 'E') == f_job + 1 and
          experiment.attribute(imgp, 'C') == 1):
        new_name = format_new_name(imgp, new_attr={'C': '02'})
    elif experiment.attribute(imgp, 'E') == f_job + 2:
        new_name = format_new_name(imgp, new_attr={'C': '03'})
    else:
        return None
    os.rename(imgp, new_name)
    return new_name


def get_field(path):
    """Get path to well from image path."""
    return experiment.Experiment(path).dirname  # pylint: disable=no-member


def get_well(path):
    """Get path to well from image path."""
    # pylint: disable=no-member
    return experiment.Experiment(get_field(path)).dirname


def get_imgs(path, img_type='tif', search=''):
    """Get all images below path."""
    if search:
        search = '{}*'.format(search)
    patterns = [
        'slide',
        'chamber',
        'field',
        'image',
    ]
    for pattern in patterns:
        if pattern not in path:
            path = os.path.join(path, '{}--*'.format(pattern))
    return experiment.glob('{}{}.{}'.format(path, search, img_type))


def save_gain(save_dir, saved_gains):
    """Save a csv file with gain values per image channel."""
    header = [WELL, GREEN, BLUE, YELLOW, RED]
    path = os.path.normpath(
        os.path.join(save_dir, 'output_gains.csv'))
    write_csv(path, saved_gains, header)


def save_histogram(path, image):
    """Save the histogram of an image to path."""
    rows = defaultdict(list)
    for box, count in enumerate(image.histogram[0]):
        rows[box].append(count)
    write_csv(path, rows, ['bin', 'count'])
