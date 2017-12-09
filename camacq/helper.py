"""Helper functions for camacq."""
import csv
import logging
import os
from collections import defaultdict

_LOGGER = logging.getLogger(__name__)


def call_saved(job):
    """Call a saved job of a tuple with func and args."""
    func = job[0]
    if len(job) > 1:
        args = job[1:]
    else:
        args = ()
    _LOGGER.debug('Calling: %s(%s)', func, args)
    return func(*args)


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


def handler_factory(handler, test):
    """Create new handler that should call another handler if test is True."""
    def handle_test(event):
        """Forward event to handler if test is True."""
        if test(event):
            handler(event)
    return handle_test


class FeatureParent(object):
    """Represent a parent of features of a package."""

    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Set up the feature parent."""
        self.children = {}

    def add_child(self, child_name, child):
        """Add a child to the parent feature registry.

        A child is the instance that provides a feature, eg a microscope API.
        """
        self.children[child_name] = child
