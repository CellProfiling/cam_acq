"""Configure and set up control center."""
import logging
import pkgutil
import pprint
from importlib import import_module
from pkg_resources import resource_filename

import camacq
import camacq.config as config_util
from camacq.config import DEFAULT_CONFIG_TEMPLATE
import camacq.log as log_util
from camacq.control import Center

_LOGGER = logging.getLogger(__name__)
_MODULE_CACHE = {}
PACKAGE = 'camacq'
PACKAGE_MODULE = '{}.{}'


def get_module(package, module_name):
    """Return a module from a package."""
    module_path = PACKAGE_MODULE.format(package, module_name)
    if module_path in _MODULE_CACHE:
        return _MODULE_CACHE[module_path]
    matches = [
        name for _, name, _
        in pkgutil.walk_packages(
            camacq.__path__, prefix='{}.'.format(camacq.__name__))
        if module_path in name]
    if len(matches) > 1:
        raise ValueError('Invalid module search result, more than one match')
    module_path = matches[0]
    if module_path in _MODULE_CACHE:
        return _MODULE_CACHE[module_path]
    try:
        module = import_module(module_path)
        _LOGGER.info("Loaded %s from %s", module_name, module_path)
        _MODULE_CACHE[module_path] = module

        return module

    except ImportError:
        _LOGGER.exception(('Loading %s failed'), module_path)


def setup_all_modules(center, config, package_path):
    """Helper to set up all modules of a package."""
    imported_pkg = import_module(package_path)
    for loader, name, is_pkg in pkgutil.iter_modules(
            imported_pkg.__path__, prefix='{}.'.format(imported_pkg.__name__)):
        if 'main' in name:
            continue
        if name in _MODULE_CACHE:
            module = _MODULE_CACHE[name]
        else:
            module = loader.find_module(name).load_module(name)
            _MODULE_CACHE[name] = module
        _LOGGER.info('Loaded %s', name)
        if is_pkg:
            if hasattr(module, 'setup_package'):
                module.setup_package(center, config)
        elif module.__name__ in config and hasattr(module, 'setup_module'):
            module.setup_module(center, config)


def setup_dict(config):
    """Set up control center from config dict."""
    log_util.enable_log(config)
    _LOGGER.debug('Contents of config:\n%s', pprint.pformat(config))
    center = Center(config)
    setup_all_modules(center, config, PACKAGE)
    return center


def setup_file(config_file, cmd_args):
    """Set up control center from config file and command line args."""
    min_config_template = resource_filename(__name__, DEFAULT_CONFIG_TEMPLATE)
    config = config_util.load_config_file(min_config_template)
    user_config = config_util.load_config_file(config_file)
    user_config.update(cmd_args)  # merge config dict with command line args
    config.update(user_config)
    center = setup_dict(config)
    return center
