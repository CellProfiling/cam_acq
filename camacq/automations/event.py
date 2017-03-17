"""Handle event trigger in automations."""
# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
from camacq.api import (CommandEvent, ImageEvent, StartCommandEvent,
                        StopCommandEvent)
from camacq.automations import CONF_TYPE
from camacq.const import CONF_ID, CONF_TRIGGER
from camacq.event import (CamAcqStartEvent, CamAcqStopEvent, ChannelEvent,
                          FieldEvent, ImageRemovedEvent, PlateEvent,
                          SampleEvent, SampleImageEvent, WellEvent)

ATTR_EVENT = 'event'
CONF_EVENT_DATA = 'data'
CONF_EVENT = 'event'

# TODO: Avoid having to store this event map. pylint: disable=fixme

CAMACQ_START_EVENT = 'camacq_start_event'
CAMACQ_STOP_EVENT = 'camacq_stop_event'
CHANNEL_EVENT = 'channel_event'
COMMAND_EVENT = 'command_event'
FIELD_EVENT = 'field_event'
IMAGE_EVENT = 'image_event'
IMAGE_REMOVED_EVENT = 'image_removed_event'
PLATE_EVENT = 'plate_event'
SAMPLE_EVENT = 'sample_event'
SAMPLE_IMAGE_EVENT = 'sample_image_event'
START_COMMAND_EVENT = 'start_command_event'
STOP_COMMAND_EVENT = 'stop_command_event'
WELL_EVENT = 'well_event'

EVENT_IDS = {
    CAMACQ_START_EVENT: CamAcqStartEvent,
    CAMACQ_STOP_EVENT: CamAcqStopEvent,
    CHANNEL_EVENT: ChannelEvent,
    COMMAND_EVENT: CommandEvent,
    FIELD_EVENT: FieldEvent,
    IMAGE_EVENT: ImageEvent,
    IMAGE_REMOVED_EVENT: ImageRemovedEvent,
    PLATE_EVENT: PlateEvent,
    SAMPLE_EVENT: SampleEvent,
    SAMPLE_IMAGE_EVENT: SampleImageEvent,
    START_COMMAND_EVENT: StartCommandEvent,
    STOP_COMMAND_EVENT: StopCommandEvent,
    WELL_EVENT: WellEvent,
}


def handle_trigger(center, config, trigger_func):
    """Listen for events."""
    event_id = config[CONF_ID]
    event_class = EVENT_IDS.get(event_id)
    if event_class is None:
        return None
    event_data = config.get(CONF_EVENT_DATA)

    def handle_event(center, event):
        """Listen for events and call trigger when data matches."""
        if not event_data or all(
                val == event.data.get(key)
                for key, val in event_data.items()):
            # pass variables from trigger with event
            trigger_func({
                CONF_TRIGGER: {
                    CONF_TYPE: CONF_EVENT,
                    ATTR_EVENT: event}})

    return center.bus.register(event_class, handle_event)
