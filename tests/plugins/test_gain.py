"""Test gain calculation."""
import os
import pprint
from mock import patch

import pytest
from pkg_resources import resource_filename

from camacq.api.leica import LeicaImageEvent
from camacq.api.leica.helper import get_imgs
from camacq.config import DEFAULT_CONFIG_TEMPLATE, load_config_file
from camacq.const import IMAGING_DIR, JOB_ID
from camacq.control import Center
from camacq.image import make_proj
from camacq.plugins.gain import calc_gain

GAIN_DATA_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '../fixtures/gain_data'))
WELL_NAME = 'U01--V00'
FULL_WELL_NAME = 'chamber--{}'.format(WELL_NAME)
WELL_PATH = os.path.join(GAIN_DATA_DIR, 'slide', FULL_WELL_NAME)
IMAGE_PATH = os.path.join(
    WELL_PATH,
    'field--X00--Y00/image--U01--V00--E02--X00--Y00--Z00--C00.ome.tif')


class MockImageEvent(LeicaImageEvent):
    """Mock ImageEvent."""

    __slots__ = ()


@pytest.fixture
def mock_os_path():
    """Patch nt path with os path."""
    with patch('camacq.api.leica.helper.ntpath') as _mock:
        _mock.split = os.path.split
        yield _mock


def test_gain(mock_os_path):
    """Run gain calculation test."""
    # pylint: disable=redefined-outer-name
    images = get_imgs(WELL_PATH, search=JOB_ID.format(2))
    default_config_template = resource_filename(
        'camacq', DEFAULT_CONFIG_TEMPLATE)
    config = load_config_file(default_config_template)
    config[IMAGING_DIR] = GAIN_DATA_DIR
    pprint.pprint(config)
    center = Center(config)
    for path in images:
        center.bus.notify(MockImageEvent({'path': path}))
    projs = make_proj(center.sample, images)
    save_path = os.path.join(WELL_PATH, WELL_NAME)
    gain_dict = calc_gain(center, save_path, projs, plot=False)
    pprint.pprint(gain_dict)
    gain_dict = {k: int(v) for k, v in gain_dict.iteritems()}
    solution = {
        'blue': 480, 'green': 740, 'red': 745, 'yellow': 805}
    assert gain_dict == pytest.approx(solution, abs=10)
