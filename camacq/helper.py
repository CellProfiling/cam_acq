"""Helper functions for camacq."""
import csv
import logging
import ntpath
import os
import re
import time
from collections import defaultdict

from matrixscreener import experiment

from camacq.command import camstart_com, del_com
from camacq.control import ImageEvent

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
        _LOGGER.debug('sending: %s', cmd)
        reply = cam.send(cmd)
        _LOGGER.debug('receiving: %s', reply)
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
    path = os.path.normpath(path)
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


def save_histogram(path, image):
    """Save the histogram of an image to path."""
    rows = {box: {'count': count}
            for box, count in enumerate(image.histogram[0])}
    write_csv(path, rows, ['bin', 'count'])


def handler_factory(handler, test):
    """Create new handler that should call another handler if test is True."""
    def handle_test(event):
        """Forward event to handler if test is True."""
        if test(event):
            handler(event)
    return handle_test


def send_com_and_start(center, commands, stop_data, handler):
    """Add commands to outgoing queue for the CAM server."""
    def stop_test(event):
        """Test if stop should be done."""
        if all(test in event.rel_path for test in stop_data):
            return True

    remove_listener = center.bus.register(
        ImageEvent, handler_factory(handler, stop_test))

    def send_commands(coms):
        """Send all commands needed to start microscope and run com."""
        center.do_now.append((center.cam.send, del_com()))
        center.do_now.append((time.sleep, 2))
        center.do_now.append((send, center.cam, coms))
        center.do_now.append((time.sleep, 2))
        center.do_now.append((center.cam.start_scan, ))
        # Wait for it to change objective and start.
        center.do_now.append((time.sleep, 7))
        center.do_now.append((center.cam.send, camstart_com()))

    # Append a tuple with function, args (tuple) and kwargs (dict).
    center.do_now.append((send_commands, commands))
    return remove_listener
