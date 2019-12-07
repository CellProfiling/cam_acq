"""Host utils that are not aware of the implementation of camacq."""
import asyncio
import csv
import os
from collections import defaultdict

try:
    asyncio_run = asyncio.run  # pylint: disable=invalid-name
except AttributeError:

    def asyncio_run(main, debug=False):
        """Mimic asyncio.run which is only in Python 3.7."""
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)
        try:
            return loop.run_until_complete(main)
        finally:
            asyncio.set_event_loop(None)
            loop.close()


class dotdict(dict):  # pylint: disable=invalid-name
    """Access to dictionary attributes with dot notation."""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def read_csv(path, index=None):
    """Read a csv file and return a dict of dicts.

    Parameters
    ----------
    path : str
        Path to csv file.
    index : str
        Index can be any of the column headers of the csv file.
        The column under index will be used as keys in the returned
        dict. If no index is specified, a list of dicts will be
        returned instead.

    Returns
    -------
    defaultdict(dict)
        Return a dict of dicts with the contents of the csv file,
        indicated by the index parameter. Each item in the dict will
        represent a row, with index as key, of the csv file.
    """
    csv_map = defaultdict(dict)
    if index is None:
        csv_map = []
    path = os.path.normpath(path)
    with open(path) as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            if index is None:
                csv_map.append(row)
            else:
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
        The items in header should correspond to the index key of the
        primary dict and all the keys of the secondary dict.
    """
    with open(path, "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=header)
        writer.writeheader()
        for index, cells in csv_map.items():
            index_dict = {header[0]: index}
            index_dict.update(cells)
            writer.writerow(index_dict)
