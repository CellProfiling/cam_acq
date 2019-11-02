"""Handle plugins."""
import asyncio

import pkg_resources

from camacq.helper import setup_module as setup


async def setup_module(center, config):
    """Set up the plugins package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    plugins = await center.add_executor_job(get_plugins)
    tasks = []
    for module in plugins.values():
        task = setup(center, config, module)
        if task:
            tasks.append(task)
    if tasks:
        await asyncio.wait(tasks)


def get_plugins():
    """Return a dict of plugin modules."""
    plugins = {
        entry_point.name: entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("camacq.plugins")
    }
    return plugins
