"""Helper functions for camacq."""
import asyncio
import logging
import pkgutil
import signal
import sys
from importlib import import_module

import voluptuous as vol

import camacq
from camacq.const import PACKAGE

_LOGGER = logging.getLogger(__name__)

PACKAGE_MODULE = "{}.{}"
BASE_ACTION_SCHEMA = vol.Schema({"action_id": str}, extra=vol.REMOVE_EXTRA)
CORE_MODULES = ["sample"]


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
        name
        for _, name, _ in pkgutil.walk_packages(
            camacq.__path__, prefix="{}.".format(camacq.__name__)
        )
        if module_path in name
    ]
    if len(matches) > 1:
        raise ValueError("Invalid module search result, more than one match")
    module_path = matches[0]
    try:
        module = import_module(module_path)
        _LOGGER.debug("Loaded %s from %s", module_name, module_path)

        return module

    except ImportError:
        _LOGGER.exception(("Loading %s failed"), module_path)


def _deep_conf_access(config, key_list):
    """Return value in nested dict using keys in key_list."""
    val = config
    for key in key_list:
        _val = val.get(key)
        if _val is None:
            return val
        val = _val
    return val


async def setup_all_modules(center, config, package_path, **kwargs):
    """Set up all modules of a package.

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
    tasks = []
    # yields, non recursively, modules under package_path
    for _, name, _ in pkgutil.iter_modules(
        imported_pkg.__path__, prefix="{}.".format(imported_pkg.__name__)
    ):
        if "main" in name:
            continue
        module = import_module(name)
        _LOGGER.debug("Loaded %s", name)
        keys = [name for name in imported_pkg.__name__.split(".") if name != PACKAGE]
        pkg_config = _deep_conf_access(config, keys)
        module_name = module.__name__.split(".")[-1]
        if module_name in pkg_config and module_name not in CORE_MODULES:
            task = setup_module(center, config, module, **kwargs)
            if task:
                tasks.append(task)

    if tasks:
        await asyncio.wait(tasks)


def setup_module(center, config, module, **kwargs):
    """Set up module or package."""
    if hasattr(module, "setup_package"):
        _LOGGER.info("Setting up %s package", module.__name__)
        return center.create_task(module.setup_package(center, config, **kwargs))
    if hasattr(module, "setup_module"):
        _LOGGER.info("Setting up %s module", module.__name__)
        return center.create_task(module.setup_module(center, config, **kwargs))
    return None


def register_signals(center):
    """Register signal handlers."""
    if sys.platform != "win32":

        def handle_signal(exit_code):
            """Handle a signal."""
            center.loop.remove_signal_handler(signal.SIGTERM)
            center.loop.remove_signal_handler(signal.SIGINT)
            center.create_task(center.end(exit_code))

        center.loop.add_signal_handler(signal.SIGTERM, handle_signal, 0)
        center.loop.add_signal_handler(signal.SIGINT, handle_signal, 0)

    else:

        prev_sig_term = None
        prev_sig_int = None

        def handle_signal(signum, frame):
            """Handle a signal."""
            signal.signal(signal.SIGTERM, prev_sig_term)
            signal.signal(signal.SIGINT, prev_sig_int)
            center.create_task(center.end(signum))

        prev_sig_term = signal.signal(signal.SIGTERM, handle_signal)
        prev_sig_int = signal.signal(signal.SIGINT, handle_signal)
