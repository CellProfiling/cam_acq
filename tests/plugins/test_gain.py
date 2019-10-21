"""Test gain calculation."""
import pprint
from functools import partial

import pytest

from camacq.api.leica import LeicaImageEvent
from camacq.api.leica.helper import get_imgs
from camacq.const import JOB_ID
from camacq.image import make_proj
from camacq.plugins.gain import GAIN_CALC_EVENT, calc_gain
from tests.common import GAIN_DATA_DIR, WELL_NAME, WELL_PATH

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name

SAVE_PATH = WELL_PATH / WELL_NAME
PLATE_NAME = "slide"
WELL_X, WELL_Y = 1, 0
GAIN_IMAGE_JOB_ID = 2


async def test_gain(center):
    """Run gain calculation test."""
    get_images = partial(
        get_imgs, WELL_PATH.as_posix(), search=JOB_ID.format(GAIN_IMAGE_JOB_ID)
    )
    images = await center.add_executor_job(get_images)
    config = {
        "plugins": {
            "gain": {
                "save_dir": GAIN_DATA_DIR,
                "channels": [
                    {
                        "channel": "green",
                        "init_gain": [
                            450,
                            495,
                            540,
                            585,
                            630,
                            675,
                            720,
                            765,
                            810,
                            855,
                            900,
                        ],
                    },
                    {
                        "channel": "blue",
                        "init_gain": [400, 435, 470, 505, 540, 575, 610],
                    },
                    {
                        "channel": "yellow",
                        "init_gain": [550, 585, 620, 655, 690, 725, 760],
                    },
                    {
                        "channel": "red",
                        "init_gain": [525, 560, 595, 630, 665, 700, 735],
                    },
                ],
            }
        }
    }
    pprint.pprint(config)
    events = [LeicaImageEvent({"path": path}) for path in images]
    images = {event.channel_id: event.path for event in events}
    projs = await center.add_executor_job(make_proj, images)
    calculated = {}

    async def handle_gain_event(center, event):
        """Handle gain event."""
        if (
            event.plate_name != PLATE_NAME
            or event.well_x != WELL_X
            or event.well_y != WELL_Y
        ):
            return
        calculated[event.channel_name] = event.gain

    center.bus.register(GAIN_CALC_EVENT, handle_gain_event)

    await calc_gain(
        center,
        config,
        PLATE_NAME,
        WELL_X,
        WELL_Y,
        projs,
        plot=False,
        save_path=SAVE_PATH,
    )
    await center.wait_for()

    pprint.pprint(calculated)
    solution = {"blue": 480, "green": 740, "red": 805, "yellow": 805}
    assert calculated == pytest.approx(solution, abs=10)
