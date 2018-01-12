"""Set up common fixtures and helpers for pytest."""
import pytest

from camacq.control import Center


@pytest.fixture
def center():
    """Give access to center via fixture."""
    _center = Center({})
    yield _center
    _center.end(0)
