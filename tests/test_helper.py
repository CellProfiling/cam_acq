"""Test helper module."""
from camacq import helper


def test_setup_modules(center, caplog):
    """Test setup_all_modules."""
    config = {'sample': None}
    helper.setup_all_modules(center, config, 'camacq')
    assert 'Setting up sample' in caplog.text
    assert 'Setting up camacq.sample' in caplog.text
