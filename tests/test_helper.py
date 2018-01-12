"""Test helper module."""
import pytest

from camacq import helper


# @pytest.mark.skip(reason="disable test while debugging issue with center")
def test_setup_modules(center, caplog):
    """Test setup_all_modules."""
    config = {'sample': None}
    helper.setup_all_modules(center, config, 'camacq')
    assert 'Setting up sample' in caplog.text
    assert 'Setting up camacq.sample' in caplog.text
