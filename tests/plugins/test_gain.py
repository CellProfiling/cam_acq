"""Test gain calculation."""
import pprint

import pytest

from camacq.api.leica import LeicaImageEvent
from camacq.api.leica.helper import get_imgs
from camacq.const import JOB_ID
from camacq.image import make_proj
from camacq.plugins.gain import calc_gain

from tests.common import GAIN_DATA_DIR, WELL_NAME, WELL_PATH

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


async def test_gain(center):
    """Run gain calculation test."""
    images = get_imgs(WELL_PATH.as_posix(), search=JOB_ID.format(2))
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
    events = [LeicaImageEvent({'path': path}) for path in images]
    images = {event.channel_id: event.path for event in events}
    projs = await center.add_executor_job(make_proj, images)
    save_path = WELL_PATH / WELL_NAME
    await calc_gain(
        center, config, 'slide', 1, 0, projs, plot=False, save_path=save_path)
    well = center.sample.get_well('slide', 1, 0)
    calculated = {
        channel_name: channel.gain
        for channel_name, channel in well.channels.items()}
    pprint.pprint(calculated)
    solution = {
        'blue': 480, 'green': 740, 'red': 805, 'yellow': 805}
    assert calculated == pytest.approx(solution, abs=10)
