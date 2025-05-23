"""Test the event bus."""

from camacq import event as event_mod


async def test_event_bus(center):
    """Test register handler, fire event and remove handler."""
    event = event_mod.Event({"test": 2})
    bus = center.bus

    async def handler(center, event):
        """Handle event."""
        if "test" not in center.data:
            center.data["test"] = 0
        center.data["test"] += event.data["test"]

    assert event_mod.BASE_EVENT not in bus.event_types

    remove = bus.register(event_mod.BASE_EVENT, handler)

    assert event_mod.BASE_EVENT in bus.event_types
    assert not center.data

    await bus.notify(event)
    await center.wait_for()

    assert center.data.get("test") == 2

    remove()
    await bus.notify(event)
    await center.wait_for()

    assert center.data.get("test") == 2
