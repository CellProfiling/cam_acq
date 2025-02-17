"""Test a complete workflow."""

from importlib import resources
import logging
from functools import partial
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from leicacam.async_cam import AsyncCAM

from camacq import bootstrap
from camacq.config import DEFAULT_CONFIG_TEMPLATE, load_config_file
from camacq.control import CamAcqStartEvent
from camacq.plugins import api as base_api
from camacq.plugins.api import ImageEvent
from camacq.plugins.leica import LeicaApi
from camacq.plugins.leica import sample as leica_sample_mod
from camacq.plugins.sample import get_matched_samples


@pytest.fixture(name="log_util", autouse=True)
def log_util_fixture():
    """Patch the log util."""
    with patch("camacq.bootstrap.log_util"):
        yield


@pytest.fixture(name="api")
def api_fixture(center):
    """Return a leica api instance."""
    config = {"leica": {}}
    client = Mock(AsyncCAM())
    mock_api = Mock(LeicaApi(center, config, client))
    mock_api.send_many = partial(base_api.Api.send_many, mock_api)

    async def register_mock_api(center, config):
        """Register a mock api package."""
        base_api.register_api(center, mock_api)
        await leica_sample_mod.setup_module(center, config)

    with patch("camacq.plugins.leica.setup_module") as leica_setup:
        leica_setup.side_effect = register_mock_api
        yield mock_api


@pytest.fixture(name="rename_image")
def rename_image_fixture():
    """Patch plugins.rename_image.rename_image."""
    with patch("camacq.plugins.rename_image.rename_image") as rename_image:
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
    # pylint: disable=too-many-locals,too-many-statements
    caplog.set_level(logging.DEBUG)
    config_path = resources.files(bootstrap.__package__) / DEFAULT_CONFIG_TEMPLATE
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
    assert api.send.call_args_list[0] == call(command="/cmd:deletelist")
    assert api.send.call_args_list[1] == call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:1 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[2] == call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:1 /fieldx:2 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert not rename_image_auto.enabled
    assert not set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 1
    assert api.send.call_args_list[3] == call(command="/cmd:startcamscan")

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
    assert api.send.call_args_list[4] == call(
        command="/cmd:adjust /tar:pmt /num:1 /exp:gain_job_1 /prop:gain /value:800"
    )
    channel = center.samples.leica.get_sample(
        "channel", plate_name="00", well_x=0, well_y=0, channel_id=3
    )
    assert channel.values.get("gain") == 800
    assert channel.values.get("channel_name") == "red"
    assert api.send.call_args_list[5] == call(command="/cmd:deletelist")
    for idx, api_call in enumerate(api.send.call_args_list[6:12]):
        field_x = int(idx / 3) + 1
        field_y = idx % 3 + 1
        assert api_call == call(
            (
                "/cmd:add /tar:camlist /exp:p10xexp /ext:af /slide:0 /wellx:1 "
                f"/welly:1 /fieldx:{field_x} /fieldy:{field_y} /dxpos:0 /dypos:0"
            )
        )
    assert rename_image_auto.enabled
    assert set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 2
    assert api.send.call_args_list[12] == call(command="/cmd:startcamscan")

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

    for idx, rename_call in enumerate(rename_image.call_args_list[:6]):
        field_x = int(idx / 3)
        field_y = idx % 3
        assert rename_call == call(
            Path(f"test_path_{field_x}_{field_y}_C00"),
            Path(f"test_path_{field_x}_{field_y}_C03"),
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
    assert api.send.call_args_list[13] == call(command="/cmd:deletelist")
    assert api.send.call_args_list[14] == call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:2 /fieldx:1 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert api.send.call_args_list[15] == call(
        command=(
            "/cmd:add /tar:camlist /exp:p10xgain /ext:af /slide:0 "
            "/wellx:1 /welly:2 /fieldx:2 /fieldy:2 /dxpos:0 /dypos:0"
        )
    )
    assert not rename_image_auto.enabled
    assert not set_img_ok_auto.enabled
    assert api.start_imaging.call_count == 3
    assert api.send.call_args_list[16] == call(command="/cmd:startcamscan")
