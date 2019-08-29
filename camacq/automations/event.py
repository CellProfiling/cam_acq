"""Handle event trigger in automations."""
# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
from camacq.automations import CONF_TYPE
from camacq.const import CONF_ID, CONF_TRIGGER

ATTR_EVENT = "event"
CONF_EVENT_DATA = "data"
CONF_EVENT = "event"


def handle_trigger(center, config, trigger_func):
    """Listen for events."""
    event_type = config[CONF_ID]
    event_data = config.get(CONF_EVENT_DATA)

    async def handle_event(center, event):
        """Listen for events and call trigger when data matches."""
        if not event_data or all(
            val == getattr(event, key, None) for key, val in event_data.items()
        ):
            # pass variables from trigger with event
            await trigger_func(
                {CONF_TRIGGER: {CONF_TYPE: CONF_EVENT, ATTR_EVENT: event}}
            )

    return center.bus.register(event_type, handle_event)
