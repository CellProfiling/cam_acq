"""Test gain calculation."""
import os
import pprint

import pytest

from camacq.api.leica import LeicaImageEvent
from camacq.api.leica.helper import get_imgs
from camacq.const import JOB_ID
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


def test_gain(center):
    """Run gain calculation test."""
    images = get_imgs(WELL_PATH, search=JOB_ID.format(2))
    config = {'plugins': {'gain': {'save_dir': GAIN_DATA_DIR, 'channels': [
        {'channel': 'green',
         'init_gain': [450, 495, 540, 585, 630, 675, 720, 765, 810, 855, 900]},
        {'channel': 'blue',
         'init_gain': [400, 435, 470, 505, 540, 575, 610]},
        {'channel': 'yellow',
         'init_gain': [550, 585, 620, 655, 690, 725, 760]},
        {'channel': 'red',
         'init_gain': [525, 560, 595, 630, 665, 700, 735]},
    ]}}}
    pprint.pprint(config)
    center.config = config
    events = [LeicaImageEvent({'path': path}) for path in images]
    images = {event.channel_id: event.path for event in events}
    projs = make_proj(images)
    save_path = os.path.join(WELL_PATH, WELL_NAME)
    calc_gain(center, 'slide', 1, 0, projs, plot=False, save_path=save_path)
    well = center.sample.get_well('slide', 1, 0)
    calculated = {
        channel_name: channel.gain
        for channel_name, channel in well.channels.items()}
    pprint.pprint(calculated)
    solution = {
        'blue': 480, 'green': 740, 'red': 805, 'yellow': 805}
    assert calculated == pytest.approx(solution, abs=10)
