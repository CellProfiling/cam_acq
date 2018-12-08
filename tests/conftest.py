"""Set up common fixtures and helpers for pytest."""
import pytest

from camacq.control import Center


@pytest.fixture
def center(event_loop):
    """Give access to center via fixture."""
    _center = Center(loop=event_loop)
    _center._track_tasks = True  # pylint: disable=protected-access
    yield _center
