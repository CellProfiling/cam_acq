"""Test gain calculation."""
import os
import pprint

from pkg_resources import resource_filename
from pytest import approx

from camacq.config import DEFAULT_CONFIG_TEMPLATE, load_config_file
from camacq.const import JOB_ID
from camacq.helper import get_imgs
from camacq.image import make_proj
from camacq.plugins.gain import calc_gain

GAIN_DATA_DIR = os.path.join(
    os.path.dirname(__file__), '../tests/fixtures/gain_data')
WELL_PATH = os.path.join(GAIN_DATA_DIR, 'slide/chamber--U01--V00')
IMAGE_PATH = os.path.join(
    WELL_PATH,
    'field--X00--Y00/image--U01--V00--E02--X00--Y00--Z00--C00.ome.tif')


def test_gain():
    """Run gain calculation test."""
    images = get_imgs(WELL_PATH, search=JOB_ID.format(2))
    projs = make_proj(images)
    default_config_template = resource_filename(
        'camacq', DEFAULT_CONFIG_TEMPLATE)
    config = load_config_file(default_config_template)
    pprint.pprint(config)
    gain_dict = calc_gain(config, IMAGE_PATH, projs)
    pprint.pprint(gain_dict)
    gain_dict['U01--V00'] = {
        k: int(v) for k, v in gain_dict['U01--V00'].iteritems()}
    solution = {
        'U01--V00': {
            'blue': 480, 'green': 740, 'red': 819, 'yellow': 805}}
    assert gain_dict['U01--V00'] == approx(solution['U01--V00'], abs=10)
