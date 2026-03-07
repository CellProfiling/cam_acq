"""Set up common fixtures and helpers for pytest."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar
from unittest.mock import Mock

import pytest
import voluptuous as vol

from camacq.const import IMAGE_EVENT
from camacq.control import Center
from camacq.event import Event
from camacq.plugins import api as api_mod
from camacq.plugins import sample as sample_mod

SET_SAMPLE_SCHEMA = vol.Schema({vol.Required("name"): str}, extra=vol.ALLOW_EXTRA)


@pytest.fixture(name="center")
async def center_fixture() -> Center:
    """Give access to center via fixture."""
    _center = Center(loop=asyncio.get_running_loop())
    _center._track_tasks = True
    return _center


@pytest.fixture(name="config")
def config_fixture() -> dict[str, Any]:
    """Return a config."""
    return {"test_api": None, "sample": {}}


@pytest.fixture(name="api")
async def api_fixture(center: Center, config: dict[str, Any]) -> MockApi:
    """Set up a mock api."""
    mock_api = MockApi()
    await api_mod.setup_module(center, config)
    api_mod.register_api(center, mock_api)
    return mock_api


@pytest.fixture(name="sample")
async def sample_fixture(center: Center, config: dict[str, Any]) -> MockSample:
    """Set up a mock sample."""
    mock_sample = MockSample()
    await sample_mod.setup_module(center, config)
    sample_mod.register_sample(center, mock_sample)
    return mock_sample


class TestSampleEvent(sample_mod.SampleEvent):
    """Represent a test sample event."""

    event_type: ClassVar[str] = "test_sample_event"

    @property
    def feature(self) -> str:
        """Return a sample feature."""
        return "test_feature"

    @property
    def sample(self) -> sample_mod.ImageContainer | None:
        """Return the sample instance of the event."""
        return self.data.get("container")


class MockApi(api_mod.Api):
    """Represent a mock microscope API."""

    def __init__(self) -> None:
        """Set up instance."""
        self.calls: list[tuple[str, ...]] = []

    @property
    def name(self) -> str:
        """Return the name of the API."""
        return "test_api"

    async def send(self, command: str, **kwargs: Any) -> None:
        """Send a command to the microscope API.

        Parameters
        ----------
        command : str
            The command to send.

        """
        self.calls.append((self.send.__name__, command))

    async def start_imaging(self) -> None:
        """Send a command to the microscope to start the imaging."""
        self.calls.append((self.start_imaging.__name__,))

    async def stop_imaging(self) -> None:
        """Send a command to the microscope to stop the imaging."""
        self.calls.append((self.stop_imaging.__name__,))


class MockSample(sample_mod.Sample):
    """Represent a mock sample."""

    def __init__(self) -> None:
        """Set up instance."""
        self.image_events: list[Event] = []
        self._images: dict[str, sample_mod.Image] = {}
        self._values: dict[str, Any] = {}
        self.mock_set_sample = Mock()

    @property
    def change_event(self) -> type[sample_mod.SampleEvent]:
        """:str: Return the image event type to listen to for the sample."""
        return TestSampleEvent

    @property
    def images(self) -> dict[str, sample_mod.Image]:
        """:dict: Return a dict with all images for the container."""
        return self._images

    @property
    def image_event_type(self) -> str:
        """:str: Return the image event type to listen to for the sample."""
        return IMAGE_EVENT

    @property
    def name(self) -> str:
        """Return the name of the sample."""
        return "test"

    @property
    def set_sample_schema(self) -> vol.Schema:
        """Return the validation schema of the set_sample method."""
        return SET_SAMPLE_SCHEMA

    @property
    def values(self) -> dict[str, Any]:
        """:dict: Return a dict with the values set for the container."""
        return self._values

    async def on_image(self, center: Center, event: Event) -> None:
        """Handle image event for this sample."""
        self.image_events.append(event)
        field_args = {
            "plate_name": event.plate_name,  # type: ignore[attr-defined]
            "well_x": event.well_x,  # type: ignore[attr-defined]
            "well_y": event.well_y,  # type: ignore[attr-defined]
            "field_x": event.field_x,  # type: ignore[attr-defined]
            "field_y": event.field_y,  # type: ignore[attr-defined]
        }
        await self.set_sample(
            "image",
            path=event.path,  # type: ignore[attr-defined]
            channel_id=event.channel_id,  # type: ignore[attr-defined]
            z_slice_id=event.z_slice_id,  # type: ignore[attr-defined]
            **field_args,
        )
        await self.set_sample("field", **field_args)

    async def _set_sample(
        self, name: str, values: dict[str, Any], **kwargs: Any
    ) -> sample_mod.ImageContainer:
        """Set an image container of the sample.

        Returns
        -------
        ImageContainer instance
            Return the ImageContainer instance that was updated.

        """
        self.mock_set_sample(name, **values, **kwargs)
        if name == "image":
            sample: sample_mod.ImageContainer = sample_mod.Image(
                values=values, **kwargs
            )
        else:
            sample = MockContainer(name, values, kwargs)
        return sample


class MockContainer(sample_mod.ImageContainer):
    """A mock container for images."""

    def __init__(
        self, name: str, values: dict[str, Any], attrs: dict[str, Any]
    ) -> None:
        """Set up instance."""
        self._images: dict[str, sample_mod.Image] = {}
        self._values = values
        self._name = name
        for attr, val in attrs.items():
            setattr(self, attr, val)

    @property
    def change_event(self) -> type[sample_mod.SampleEvent]:
        """:Event: Return an event class to fire on container change."""
        return TestSampleEvent

    @property
    def images(self) -> dict[str, sample_mod.Image]:
        """:dict: Return a dict with all images for the container."""
        return self._images

    @property
    def name(self) -> str:
        """:str: Return an identifying name for the container."""
        return self._name

    @property
    def values(self) -> dict[str, Any]:
        """:dict: Return a dict with the values set for the container."""
        return self._values
