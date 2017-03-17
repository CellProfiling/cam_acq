"""Test automations."""
import pytest
from mock import patch

from camacq import sample as sample_mod
from camacq import api, automations
from camacq.event import CamAcqStartEvent


class MockApi(api.Api):
    """Represent a mock microscope API."""

    def __init__(self):
        """Set up instance."""
        self.calls = []

    def send(self, command):
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send, should be a JSON string.
        """
        self.calls.append((self.send.__name__, command))

    def start_imaging(self):
        """Send a command to the microscope to start the imaging."""
        self.calls.append((self.start_imaging.__name__, ))

    def stop_imaging(self):
        """Send a command to the microscope to stop the imaging."""
        self.calls.append((self.stop_imaging.__name__, ))


@pytest.fixture
def mock_api(center):
    """Set up a mock api."""
    _mock_api = MockApi()

    def setup_mock_api_package(center, config, add_child=None):
        """Set up a mock api package."""
        add_child('test_api', _mock_api)

    with patch('camacq.api.leica.setup_package') as leica_setup:
        leica_setup.side_effect = setup_mock_api_package
        api.setup_package(center, {'api': {'leica': None}})
        yield _mock_api


def test_setup_automation(center, caplog):
    """Test setup of an automation."""
    config = {
        'automations': [{
            'name': 'test_automation',
            'trigger': [{
                'type': 'event',
                'id': 'camacq_start_event',
            }],
            'action': [{
                'type': 'sample',
                'id': 'set_well',
                'data': {
                    'well_x': 1,
                    'well_y': 1,
                },
            }],
        }],
    }

    sample_mod.setup_module(center, config)
    automations.setup_package(center, config)
    assert 'Loaded event from camacq.automations' in caplog.text
    assert 'Set up trigger camacq_start_event' in caplog.text
    assert 'toggle' in center.actions.actions['camacq.automations']
    automation = center.data['camacq.automations']['test_automation']
    assert automation.enabled

    center.sample.set_plate('test')
    assert not center.sample.all_wells('test')
    event = CamAcqStartEvent({'test_data': 'start'})
    center.bus.notify(event)
    wells = center.sample.all_wells('test')
    assert wells[0].x == 1
    assert wells[0].y == 1

    center.actions.call('camacq.automations', 'toggle', name='test_automation')
    assert not automation.enabled


def test_channel_event(center, caplog, mock_api):
    """Test a trigger for channel event."""
    # pylint: disable=redefined-outer-name

    config = {
        'automations': [{
            'name': 'set_channel_gain',
            'trigger': [{
                'type': 'event',
                'id': 'channel_event',
            }],
            'action': [{
                'type': 'api',
                'id': 'send',
                'data': {
                    'command':
                        "/cmd:adjust /tar:pmt "
                        "/num:{% if trigger.event.channel_name == 'green' %}1"
                        "{% elif trigger.event.channel_name == 'blue' %}1 "
                        "{% elif trigger.event.channel_name == 'yellow' %}2"
                        "{% elif trigger.event.channel_name == 'red' %}2"
                        "{% endif %} /exp:gain_job /prop:gain "
                        "/value:{{ trigger.event.channel.gain }}",
                },
            }],
        }],
    }

    sample_mod.setup_module(center, config)
    automations.setup_package(center, config)
    automation = center.data['camacq.automations']['set_channel_gain']
    assert automation.enabled

    center.sample.set_plate('test')
    center.sample.set_gain(1, 1, 'yellow', 333, 'test')
    wells = center.sample.all_wells('test')
    assert wells[0].x == 1
    assert wells[0].y == 1
    assert 'send' in center.actions.actions['camacq.api']
    assert len(mock_api.calls) == 1
    func_name, command = mock_api.calls[0]
    assert func_name == 'send'
    assert command == (
        '/cmd:adjust /tar:pmt /num:2 /exp:gain_job /prop:gain /value:333')
