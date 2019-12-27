"""Test a complete workflow."""
import logging
from functools import partial
from pkg_resources import resource_filename

import asynctest
import pytest
from leicacam.async_cam import AsyncCAM

from camacq import bootstrap
from camacq.plugins import api as base_api
from camacq.plugins.api import ImageEvent
from camacq.plugins.leica import LeicaApi, sample as leica_sample_mod
from camacq.plugins.sample import get_matched_samples
from camacq.config import DEFAULT_CONFIG_TEMPLATE, load_config_file
from camacq.control import CamAcqStartEvent

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


@pytest.fixture(name="log_util", autouse=True)
def log_util_fixture():
    """Patch the log util."""
    with asynctest.patch("camacq.bootstrap.log_util"):
        yield


@pytest.fixture(name="api")
def api_fixture(center):
    """Return a leica api instance."""
    config = {"api": {"leica": {}}}
    client = asynctest.Mock(AsyncCAM(loop=center.loop))
    mock_api = asynctest.Mock(LeicaApi(center, config, client))
    mock_api.send_many = partial(base_api.Api.send_many, mock_api)

    async def register_mock_api(center, config):
        """Register a mock api package."""
        base_api.register_api(center, mock_api)
        await leica_sample_mod.setup_module(center, config)

    with asynctest.patch("camacq.plugins.leica.setup_module") as leica_setup:
        leica_setup.side_effect = register_mock_api
        yield mock_api


@pytest.fixture(name="rename_image")
def rename_image_fixture():
    """Patch plugins.rename_image.rename_image."""
    with asynctest.patch("camacq.plugins.rename_image.rename_image") as rename_image:
        yield rename_image


class WorkflowImageEvent(ImageEvent):
    """Represent a test image event."""

    event_type = "workflow_image_event"

    @property
    def job_id(self):
        """:int: Return job id of the image."""
        return self.data.get("job_id")


async def test_workflow(center, caplog, api, rename_image):
    """Test a complete workflow."""
    # pylint: disable=too-many-statements
    caplog.set_level(logging.DEBUG)
    config_path = resource_filename(bootstrap.__name__, DEFAULT_CONFIG_TEMPLATE)
    config = await center.add_executor_job(load_config_file, config_path)
    config.pop("logging")
    await bootstrap.setup_dict(center, config)
    rename_image_auto = center.data["automations"]["rename_image"]
    assert rename_image_auto.enabled
    set_img_ok_auto = center.data["automations"]["set_img_ok"]
    assert set_img_ok_auto.enabled
    assert not center.samples.leica.data
    assert api.start_imaging.call_count == 0
    assert api.stop_imaging.call_count == 0
    assert center.actions.actions.get("rename_image", {}).get("rename_image")

    event = CamAcqStartEvent()
    await center.bus.notify(event)
    await center.wait_for()

    well = center.samples.leica.get_sample("well", plate_name="00", well_x=0, well_y=0)
    assert well is not None
    assert api.send.call_args_list[0] == asynctest.call(command="/cmd:deletelist")
    assert api.send.call_args_list[1] == asynctest.call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:1 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[2] == asynctest.call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:2 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert not rename_image_auto.enabled
    assert not set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 1
    assert api.send.call_args_list[3] == asynctest.call(command="/cmd:startcamscan")

    event = WorkflowImageEvent(
        {
            "path": "test_path",
            "plate_name": "00",
            "well_x": 0,
            "well_y": 0,
            "field_x": 1,
            "field_y": 1,
            "z_slice_id": 0,
            "job_id": 2,
            "channel_id": 31,
        }
    )
    await center.bus.notify(event)
    await center.wait_for()

    assert api.stop_imaging.call_count == 1
    assert api.send.call_args_list[4] == asynctest.call(
        command="/cmd:adjust /tar:pmt /num:1 /exp:gain_job_1 /prop:gain /value:800"
    )
    channel = center.samples.leica.get_sample(
        "channel", plate_name="00", well_x=0, well_y=0, channel_id=3
    )
    assert channel.values.get("gain") == 800
    assert channel.values.get("channel_name") == "red"
    assert api.send.call_args_list[5] == asynctest.call(command="/cmd:deletelist")
    assert api.send.call_args_list[6] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:1 /fieldy:1 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[7] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:1 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[8] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:1 /fieldy:3 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[9] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:2 /fieldy:1 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[10] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:2 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[11] == asynctest.call(
        (
            "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:2 /fieldy:3 /dxpos:0 /dypos:0"
        )
    )
    assert rename_image_auto.enabled
    assert set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 2
    assert api.send.call_args_list[12] == asynctest.call(command="/cmd:startcamscan")

    for x_number in range(2):
        for y_number in range(3):
            event = WorkflowImageEvent(
                {
                    "path": f"test_path_{x_number}_{y_number}_C00",
                    "plate_name": "00",
                    "well_x": 0,
                    "well_y": 0,
                    "field_x": x_number,
                    "field_y": y_number,
                    "z_slice_id": 0,
                    "job_id": 4,
                    "channel_id": 1,
                }
            )
            await center.bus.notify(event)
    await center.wait_for()

    assert rename_image.call_args_list[0] == asynctest.call(
        "test_path_0_0_C00", "test_path_0_0_C03"
    )
    assert rename_image.call_args_list[1] == asynctest.call(
        "test_path_0_1_C00", "test_path_0_1_C03"
    )
    assert rename_image.call_args_list[2] == asynctest.call(
        "test_path_0_2_C00", "test_path_0_2_C03"
    )
    assert rename_image.call_args_list[3] == asynctest.call(
        "test_path_1_0_C00", "test_path_1_0_C03"
    )
    assert rename_image.call_args_list[4] == asynctest.call(
        "test_path_1_1_C00", "test_path_1_1_C03"
    )
    assert rename_image.call_args_list[5] == asynctest.call(
        "test_path_1_2_C00", "test_path_1_2_C03"
    )
    fields = get_matched_samples(
        center.samples.leica,
        "field",
        attrs={"plate_name": "00", "well_x": 0, "well_y": 0},
    )
    assert len(fields) == 6
    assert all(field.values.get("field_img_ok", False) for field in fields)
    assert api.stop_imaging.call_count == 2
    well_0_1 = center.samples.leica.get_sample(
        "well", plate_name="00", well_x=0, well_y=1
    )
    assert well_0_1.well_x == 0
    assert well_0_1.well_y == 1
    assert api.send.call_args_list[13] == asynctest.call(command="/cmd:deletelist")
    assert api.send.call_args_list[14] == asynctest.call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:2 /fieldx:1 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[15] == asynctest.call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:2 /fieldx:2 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert not rename_image_auto.enabled
    assert not set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 3
    assert api.send.call_args_list[16] == asynctest.call(command="/cmd:startcamscan")
