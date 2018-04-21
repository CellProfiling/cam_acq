"""Helper functions for camacq."""
import csv
import logging
import os
import pkgutil
from builtins import object  # pylint: disable=redefined-builtin
from collections import defaultdict
from importlib import import_module

import voluptuous as vol

import camacq
from camacq.const import PACKAGE

_LOGGER = logging.getLogger(__name__)

PACKAGE_MODULE = '{}.{}'
BASE_ACTION_SCHEMA = vol.Schema({'action_id': str}, extra=vol.REMOVE_EXTRA)
CORE_MODULES = ['sample']


def get_module(package, module_name):
    """Return a module from a package.

    Parameters
    ----------
    package : str
        The path to the package.
    module_name : str
        The name of the module.
    """
    module_path = PACKAGE_MODULE.format(package, module_name)
    matches = [
        name for _, name, _
        in pkgutil.walk_packages(
            camacq.__path__, prefix='{}.'.format(camacq.__name__))
        if module_path in name]
    if len(matches) > 1:
        raise ValueError('Invalid module search result, more than one match')
    module_path = matches[0]
    try:
        module = import_module(module_path)
        _LOGGER.debug('Loaded %s from %s', module_name, module_path)

        return module

    except ImportError:
        _LOGGER.exception(('Loading %s failed'), module_path)


def _deep_conf_access(config, key_list):
    """Return value in nested dict using keys in key_list."""
    val = config
    for key in key_list:
        _val = val.get(key)
        if _val is None:
            return val
        val = _val
    return val


def setup_all_modules(center, config, package_path, **kwargs):
    """Helper to set up all modules of a package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    package_path : str
        The path to the package.
    **kwargs
        Arbitrary keyword arguments. These will be passed to
        setup_package and setup_module functions.
    """
    imported_pkg = import_module(package_path)
    # yields, non recursively, modules under package_path
    for _, name, is_pkg in pkgutil.iter_modules(
            imported_pkg.__path__, prefix='{}.'.format(imported_pkg.__name__)):
        if 'main' in name:
            continue
        else:
            module = import_module(name)
        _LOGGER.debug('Loaded %s', name)
        keys = [
            name for name in imported_pkg.__name__.split('.')
            if name != PACKAGE]
        pkg_config = _deep_conf_access(config, keys)
        module_name = module.__name__.split('.')[-1]
        if module_name in pkg_config and module_name not in CORE_MODULES:
            if is_pkg and hasattr(module, 'setup_package'):
                _LOGGER.info('Setting up %s package', module.__name__)
                module.setup_package(center, config, **kwargs)
            elif hasattr(module, 'setup_module'):
                _LOGGER.info('Setting up %s module', module.__name__)
                module.setup_module(center, config, **kwargs)


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
    with open(path, 'w') as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=header)
        writer.writeheader()
        for index, cells in csv_map.items():
            index_dict = {header[0]: index}
            index_dict.update(cells)
            writer.writerow(index_dict)


class FeatureParent(object):
    """Represent a parent of features of a package.

    Attributes
    ----------
    children : dict
        Return dict of children of the parent.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Set up the feature parent."""
        self.children = {}

    def add_child(self, child_name, child):
        """Add a child to the parent feature registry.

        A child is the instance that provides a feature, eg a
        microscope API.

        Parameters
        ----------
        child_name : str
            Name of the child. The name will be the key in the registry
            dict.
        child : child instance
            The instance of the child that should be stored.
        """
        self.children[child_name] = child
