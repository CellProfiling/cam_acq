"""Test automations."""
import logging

import pytest

from ruamel.yaml import YAML

from camacq import plugins
from camacq.plugins import api
from camacq.control import CamAcqStartEvent

# pylint: disable=redefined-outer-name
# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


class MockApi(api.Api):
    """Represent a mock microscope API."""

    def __init__(self):
        """Set up instance."""
        self.calls = []

    @property
    def name(self):
        """Return the name of the API."""
        return "test_api"

    async def send(self, command, **kwargs):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send.
        """
        self.calls.append((self.send.__name__, command))

    async def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        self.calls.append((self.start_imaging.__name__,))

    async def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        self.calls.append((self.stop_imaging.__name__,))


@pytest.fixture
def mock_api(center):
    """Set up a mock api."""
    _mock_api = MockApi()
    config = {"api": {"test_api": None}}

    def register_mock_api(center, config):
        """Register a mock api package."""
        api.register_api(center, _mock_api)

    center.loop.run_until_complete(api.setup_module(center, config))
    register_mock_api(center, _mock_api)
    yield _mock_api


async def test_setup_automation(center):
    """Test setup of an automation."""
    config = """
        automations:
        - name: test_automation
          trigger:
          - type: event
            id: camacq_start_event
          action:
          - type: sample
            id: set_well
            data:
              plate_name: test
              well_x: 1
              well_y: 1
        sample:
    """

    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    assert "set_well" in center.actions.actions["sample"]
    assert "toggle" in center.actions.actions["automations"]
    automation = center.data["automations"]["test_automation"]
    assert automation.enabled

    assert not center.sample.plates
    event = CamAcqStartEvent({"test_data": "start"})
    await center.bus.notify(event)
    await center.wait_for()
    plate = center.sample.get_plate("test")
    assert plate
    assert plate.wells[1, 1].x == 1
    assert plate.wells[1, 1].y == 1

    await center.actions.call("automations", "toggle", name="test_automation")
    assert not automation.enabled


async def test_channel_event(center, mock_api):
    """Test a trigger for channel event."""

    config = """
        automations:
        - name: set_channel_gain
          trigger:
          - type: event
            id: channel_event
          action:
          - type: command
            id: send
            data:
              command: >
                /cmd:adjust /tar:pmt /num:{% if trigger.event.channel_name == 'green'
                %}1{% elif trigger.event.channel_name == 'blue'
                %}1 {% elif trigger.event.channel_name == 'yellow'
                %}2{% elif trigger.event.channel_name == 'red'
                %}2{% endif %}
                /exp:gain_job /prop:gain /value:{{ trigger.event.channel.gain }}
        sample:
    """

    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["set_channel_gain"]
    assert automation.enabled

    await center.sample.set_channel("test", 1, 1, "yellow", gain=333)
    await center.wait_for()
    assert "send" in center.actions.actions["command"]
    assert len(mock_api.calls) == 1
    func_name, command = mock_api.calls[0]
    assert func_name == "send"
    assert command == (
        "/cmd:adjust /tar:pmt /num:2 /exp:gain_job /prop:gain /value:333"
    )


async def test_condition(center, mock_api):
    """Test a condition for command event."""
    config = """
        automations:
        - name: add_exp_job
          trigger:
          - type: event
            id: command_event
          condition:
            type: AND
            conditions:
            - condition: "{% if 'test' in trigger.event.data %}true{% endif %}"
            - condition: '{% if trigger.event.data.test == 1 %}true{% endif %}'
          action:
          - type: command
            id: send
            data:
              command: success
        sample:
    """

    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["add_exp_job"]
    assert automation.enabled

    assert "send" in center.actions.actions["command"]
    await center.bus.notify(api.CommandEvent(data={"test": 1}))
    await center.wait_for()
    assert len(mock_api.calls) == 1
    func_name, command = mock_api.calls[0]
    assert func_name == "send"
    assert command == "success"


async def test_nested_condition(center, mock_api):
    """Test a nested condition for command event."""
    config = """
        automations:
          - name: add_exp_job
            trigger:
              - type: event
                id: command_event
            condition:
              type: AND
              conditions:
                - condition: "{% if 'test' in trigger.event.data %}true{% endif %}"
                - type: OR
                  conditions:
                    - condition: '{% if trigger.event.data.test == 1 %}true{% endif %}'
                    - condition: '{% if trigger.event.data.test == 2 %}true{% endif %}'
            action:
              - type: command
                id: send
                data:
                  command: success
        sample:
    """

    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["add_exp_job"]
    assert automation.enabled
    assert "send" in center.actions.actions["command"]

    # This should not add a call to the api.
    await center.bus.notify(api.CommandEvent(data={"test": 0}))
    await center.wait_for()

    assert not mock_api.calls

    # This should add a call to the api.
    await center.bus.notify(api.CommandEvent(data={"test": 1}))
    await center.wait_for()

    assert len(mock_api.calls) == 1
    func_name, command = mock_api.calls[-1]
    assert func_name == "send"
    assert command == "success"

    # This should add a call to the api.
    await center.bus.notify(api.CommandEvent(data={"test": 2}))
    await center.wait_for()

    assert len(mock_api.calls) == 2
    func_name, command = mock_api.calls[-1]
    assert func_name == "send"
    assert command == "success"

    # This should not add a call to the api.
    await center.bus.notify(api.CommandEvent(data={"test": 3}))
    await center.wait_for()

    assert len(mock_api.calls) == 2


async def test_sample_access(center, mock_api):
    """Test accessing sample in template."""
    config = """
        automations:
          - name: set_img_ok
            trigger:
              - type: event
                id: image_event
            condition:
              type: AND
              conditions:
                - condition: >
                    {% if not sample.plates[trigger.event.plate_name].wells[
                      (trigger.event.well_x, trigger.event.well_y)].fields[
                      (trigger.event.field_x, trigger.event.field_y)].img_ok
                    %}true{% endif %}
            action:
              - type: sample
                id: set_field
                data:
                  plate_name: '00'
                  well_x: '{{ trigger.event.well_x }}'
                  well_y: '{{ trigger.event.well_y }}'
                  field_x: '{{ trigger.event.field_x }}'
                  field_y: '{{ trigger.event.field_y }}'
                  img_ok: true
        sample:
    """

    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["set_img_ok"]
    assert automation.enabled
    await center.sample.set_plate("00")
    await center.sample.set_well("00", 0, 0)
    field = await center.sample.set_field("00", 0, 0, 1, 1, img_ok=False)
    assert not field.img_ok

    event = api.ImageEvent(
        {
            "path": "test_path",
            "plate_name": "00",
            "well_x": 0,
            "well_y": 0,
            "field_x": 1,
            "field_y": 1,
            "channel_id": 0,
        }
    )
    await center.bus.notify(event)
    await center.wait_for()

    field = center.sample.get_field("00", 0, 0, 1, 1)
    assert field.img_ok


async def test_delay_action(center, mock_api, caplog):
    """Test delay action."""
    config = """
        automations:
          - name: test_delay
            trigger:
              - type: event
                id: camacq_start_event
            action:
              - type: command
                id: start_imaging
              - type: automations
                id: delay
                data:
                  seconds: 0.0
              - type: command
                id: stop_imaging
    """
    caplog.set_level(logging.INFO)
    config = await center.add_executor_job(YAML(typ="safe").load, config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["test_delay"]
    assert automation.enabled
    event = CamAcqStartEvent({"test_data": "start"})
    await center.bus.notify(event)
    await center.wait_for()
    assert len(mock_api.calls) == 2
    assert mock_api.calls[-2] == ("start_imaging",)
    assert mock_api.calls[-1] == ("stop_imaging",)
    assert "Action delay for 0.0 seconds" in caplog.text
