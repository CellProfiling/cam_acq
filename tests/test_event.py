"""Test the event bus."""
from camacq import event as event_mod


def test_event_bus(center):
    """Test register handler, fire event and remove handler."""
    event = event_mod.Event({'test': 2})
    bus = event_mod.EventBus(center)

    def handler(center, event):
        """Handle event."""
        if 'test' not in center.data:
            center.data['test'] = 0
        center.data['test'] += event.data['test']

    assert not bus.event_types

    remove = bus.register(event_mod.Event, handler)

    assert bus.event_types == [event_mod.Event]
    assert not center.data

    bus.notify(event)

    assert center.data.get('test') == 2

    remove()
    bus.notify(event)

    assert center.data.get('test') == 2
