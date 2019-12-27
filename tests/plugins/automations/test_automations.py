"""Test automations."""
import logging
from unittest.mock import call

import pytest
from ruamel.yaml import YAML

from camacq import plugins
from camacq.control import CamAcqStartEvent
from camacq.plugins import api as api_mod

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio  # pylint: disable=invalid-name


async def test_setup_automation(center, sample):
    """Test setup of an automation."""
    config = """
        automations:
        - name: test_automation
          trigger:
          - type: event
            id: camacq_start_event
          action:
          - type: sample
            id: set_sample
            data:
              plate_name: test
              well_x: 1
              well_y: 1
    """

    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    assert "set_sample" in center.actions.actions["sample"]
    assert "toggle" in center.actions.actions["automations"]
    automation = center.data["automations"]["test_automation"]
    assert automation.enabled

    assert sample.mock_set_sample.call_count == 0
    event = CamAcqStartEvent({"test_data": "start"})
    await center.bus.notify(event)
    await center.wait_for()
    assert sample.mock_set_sample.call_count == 1
    assert sample.mock_set_sample.call_args == call(
        plate_name="test", well_x="1", well_y="1"
    )

    await center.actions.call("automations", "toggle", name="test_automation")
    assert not automation.enabled


async def test_sample_event(center, api, sample):
    """Test a trigger for sample change event."""

    config = """
        automations:
        - name: set_channel_gain
          trigger:
          - type: event
            id: test_sample_event
          action:
          - type: command
            id: send
            data:
              command: >
                /test /num:{% if trigger.event.feature == 'test_feature'
                %}1{% else
                %}2{% endif %}
    """

    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["set_channel_gain"]
    assert automation.enabled

    await center.samples.test.set_sample(
        plate_name="test", well_x="1", well_y="1", channel_name="yellow", gain=333
    )
    await center.wait_for()
    assert "send" in center.actions.actions["command"]
    assert len(api.calls) == 1
    func_name, command = api.calls[0]
    assert func_name == "send"
    assert command == "/test /num:1"


async def test_condition(center, api):
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
    """

    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["add_exp_job"]
    assert automation.enabled

    assert "send" in center.actions.actions["command"]
    await center.bus.notify(api_mod.CommandEvent(data={"test": 1}))
    await center.wait_for()
    assert len(api.calls) == 1
    func_name, command = api.calls[0]
    assert func_name == "send"
    assert command == "success"


async def test_nested_condition(center, api):
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
    """

    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["add_exp_job"]
    assert automation.enabled
    assert "send" in center.actions.actions["command"]

    # This should not add a call to the api.
    await center.bus.notify(api_mod.CommandEvent(data={"test": 0}))
    await center.wait_for()

    assert not api.calls

    # This should add a call to the api.
    await center.bus.notify(api_mod.CommandEvent(data={"test": 1}))
    await center.wait_for()

    assert len(api.calls) == 1
    func_name, command = api.calls[-1]
    assert func_name == "send"
    assert command == "success"

    # This should add a call to the api.
    await center.bus.notify(api_mod.CommandEvent(data={"test": 2}))
    await center.wait_for()

    assert len(api.calls) == 2
    func_name, command = api.calls[-1]
    assert func_name == "send"
    assert command == "success"

    # This should not add a call to the api.
    await center.bus.notify(api_mod.CommandEvent(data={"test": 3}))
    await center.wait_for()

    assert len(api.calls) == 2


async def test_sample_access(center, api, sample):
    """Test accessing sample in template."""
    config = """
        automations:
          - name: set_img_ok
            trigger:
              - type: event
                id: test_sample_event
            condition:
              type: AND
              conditions:
                - condition: "{% if samples.test.image_events %}true{% endif %}"
            action:
              - type: command
                id: send
                data:
                  command: >
                    /test /num:{% if trigger.event.feature == 'test_feature'
                    %}1{% else
                    %}2{% endif %}
    """

    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["set_img_ok"]
    assert automation.enabled
    assert sample.mock_set_sample.call_count == 0

    event = api_mod.ImageEvent(
        {
            "path": "test_path",
            "plate_name": "00",
            "well_x": 0,
            "well_y": 0,
            "field_x": 1,
            "field_y": 1,
            "z_slice": 0,
            "channel_id": 0,
        }
    )
    await center.bus.notify(event)
    await center.wait_for()

    assert sample.image_events
    assert len(api.calls) == 1
    func_name, command = api.calls[0]
    assert func_name == "send"
    assert command == "/test /num:1"


async def test_delay_action(center, api, caplog):
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
    config = YAML(typ="safe").load(config)
    await plugins.setup_module(center, config)
    automation = center.data["automations"]["test_delay"]
    assert automation.enabled
    event = CamAcqStartEvent({"test_data": "start"})
    await center.bus.notify(event)
    await center.wait_for()
    assert len(api.calls) == 2
    assert api.calls[-2] == ("start_imaging",)
    assert api.calls[-1] == ("stop_imaging",)
    assert "Action delay for 0.0 seconds" in caplog.text
