"""Handle plugins."""
from camacq.helper import setup_all_modules


def setup_package(center, config):
    """Set up the plugins package.

    Parameters
    ----------
    center : Center instance
        The Center instance.
    config : dict
        The config dict.
    """
    setup_all_modules(center, config, __name__)
