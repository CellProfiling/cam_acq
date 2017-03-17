"""Handle plugins."""
from camacq.bootstrap import setup_all_modules


def setup_package(center, config):
    """Set up actions package."""
    setup_all_modules(center, config, __name__)
