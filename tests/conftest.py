"""Set up common fixtures and helpers for pytest."""
from unittest.mock import Mock

import pytest
import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.control import Center
from camacq.plugins import api as api_mod, sample as sample_mod

SET_SAMPLE_SCHEMA = vol.Schema(dict)


@pytest.fixture(name="center")
def center_fixture(event_loop):
    """Give access to center via fixture."""
    _center = Center(loop=event_loop)
    _center._track_tasks = True  # pylint: disable=protected-access
    yield _center


@pytest.fixture(name="config")
def config_fixture():
    """Return a config."""
    return {"api": {"test_api": None}, "sample": {}}


@pytest.fixture(name="api")
def api_fixture(center, config):
    """Set up a mock api."""
    mock_api = MockApi()
    center.loop.run_until_complete(api_mod.setup_module(center, config))
    api_mod.register_api(center, mock_api)
    yield mock_api


@pytest.fixture(name="sample")
def sample_fixture(center, config):
    """Set up a mock sample."""
    mock_sample = MockSample()
    center.loop.run_until_complete(sample_mod.setup_module(center, config))
    sample_mod.register_sample(center, mock_sample)
    yield mock_sample


class TestSampleEvent(sample_mod.SampleEvent):
    """Represent a test sample event."""

    # pylint: disable=too-few-public-methods

    event_type = "test_sample_event"

    @property
    def feature(self):
        """Return a sample feature."""
        return "test_feature"

    @property
    def sample(self):
        """Return the sample instance of the event."""
        return self.data.get("container")


class MockApi(api_mod.Api):
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


class MockSample(sample_mod.Sample):
    """Represent a mock sample."""

    def __init__(self):
        """Set up instance."""
        self.image_events = []
        self._images = {}
        self._values = {}
        self.mock_set_sample = Mock()

    @property
    def change_event(self):
        """:str: Return the image event type to listen to for the sample."""
        return TestSampleEvent

    @property
    def image_class(self):
        """:cls: Return the image class to instantiate for the sample."""
        return TestImage

    @property
    def images(self):
        """:dict: Return a dict with all images for the container."""
        return self._images

    @property
    def image_event_type(self):
        """:str: Return the image event type to listen to for the sample."""
        return IMAGE_EVENT

    @property
    def name(self):
        """Return the name of the sample."""
        return "test"

    @property
    def set_sample_schema(self):
        """Return the validation schema of the set_sample method."""
        return SET_SAMPLE_SCHEMA

    @property
    def values(self):
        """:dict: Return a dict with the values set for the container."""
        return self._values

    async def on_image(self, center, event):
        """Handle image event for this sample."""
        self.image_events.append(event)
        await self.set_image(
            event.path,
            plate_name=event.plate_name,
            well_x=event.well_x,
            well_y=event.well_y,
            field_x=event.field_x,
            field_y=event.field_y,
            channel_id=event.channel_id,
        )

    async def _set_sample(self, values, **kwargs):
        """Set an image container of the sample.

        Returns
        -------
        ImageContainer instance
            Return the ImageContainer instance that was updated.
        """
        self.mock_set_sample(**values, **kwargs)
        return self


class TestImage(sample_mod.Image):
    """Represent test image."""

    # pylint: disable=too-few-public-methods

    def __init__(self, path, **kwargs):
        """Set up instance."""
        self._path = path
        for key, val in kwargs.items():
            setattr(self, key, val)

    @property
    def path(self):
        """Return the path of the image."""
        return self._path
