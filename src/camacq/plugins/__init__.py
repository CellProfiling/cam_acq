"""Handle plugins."""

from __future__ import annotations

import asyncio
from importlib.metadata import entry_points
from types import ModuleType
from typing import TYPE_CHECKING, Any

from camacq.helper import setup_one_module

if TYPE_CHECKING:
    from camacq.control import Center

CORE_MODULES = ["api", "sample"]


async def setup_module(center: Center, config: dict[str, Any]) -> None:
    """Set up the plugins package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.

    """
    plugins = await center.add_executor_job(get_plugins)

    # Add core modules.
    tasks: list[asyncio.Task[None]] = []
    for module_name in CORE_MODULES:
        if module_name not in config:
            config[module_name] = {}
        module = plugins.pop(module_name, None)
        if not module:
            continue
        tasks.append(center.create_task(setup_one_module(center, config, module)))
    if tasks:
        await asyncio.wait(tasks)

    tasks = []
    for name, module in plugins.items():
        if name not in config:
            continue
        tasks.append(center.create_task(setup_one_module(center, config, module)))
    if tasks:
        await asyncio.wait(tasks)


def get_plugins() -> dict[str, ModuleType]:
    """Return a dict of plugin modules."""
    plugins = {
        entry_point.name: entry_point.load()
        for entry_point in entry_points(group="camacq.plugins")
    }
    return plugins
