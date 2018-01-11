"""Set up common fixtures and helpers for pytest."""
import pytest
from pkg_resources import resource_filename

from camacq.control import Center
from camacq.config import load_config_file, DEFAULT_CONFIG_TEMPLATE


@pytest.fixture
def config():
    """Give access to config via fixture."""
    min_config_template = resource_filename('camacq', DEFAULT_CONFIG_TEMPLATE)
    conf = load_config_file(min_config_template)
    yield conf


@pytest.fixture
def center():
    """Give access to center via fixture."""
    _center = Center({})
    yield _center
    _center.end(0)
    clear_event_registry(_center)


def clear_event_registry(center_obj):
    """Clear event registry.

    Run this between tests.
    """
    # pylint: disable=protected-access
    del center_obj.bus._event.subscribers[:]
    center_obj.bus._handler.registry.clear()
