"""Handle event trigger in automations."""

# Copyright 2013-2017 The Home Assistant Authors
# https://github.com/home-assistant/home-assistant/blob/master/LICENSE.md
# This file was modified by The Camacq Authors.
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import TYPE_CHECKING, Any

from camacq.const import CONF_ID, CONF_TRIGGER
from camacq.event import Event, match_event

from . import CONF_TYPE

if TYPE_CHECKING:
    from camacq.control import Center

_LOGGER = logging.getLogger(__name__)

ATTR_EVENT = "event"
CONF_EVENT_DATA = "data"
CONF_EVENT = "event"


def handle_trigger(
    center: Center,
    config: dict[str, Any],
    trigger_func: Callable[[dict[str, Any]], Awaitable[None]],
) -> Callable[[], None]:
    """Listen for events."""
    event_type: str = config[CONF_ID]
    event_data: dict[str, Any] = config.get(CONF_EVENT_DATA, {})

    async def handle_event(center: Center, event: Event) -> None:
        """Listen for events and call trigger when data matches."""
        if match_event(event, **event_data):
            _LOGGER.debug("Trigger matched for event %s", event_type)
            # pass variables from trigger with event
            await trigger_func(
                {CONF_TRIGGER: {CONF_TYPE: CONF_EVENT, ATTR_EVENT: event}}
            )

    return center.bus.register(event_type, handle_event)
