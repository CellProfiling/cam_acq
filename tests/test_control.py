"""Test the control module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import voluptuous as vol

from camacq.const import CAMACQ_START_EVENT, CAMACQ_STOP_EVENT
from camacq.control import Center
from camacq.event import Event


async def test_center_start(center: Center) -> None:
    """Test start of Center."""
    events: list[Event] = []
    exit_code = 0

    async def handle_event(center: Center, event: Event) -> None:
        """Stop the task that listens to the client socket."""
        events.append(event)

    center.bus.register(CAMACQ_START_EVENT, handle_event)
    center._track_tasks = False
    task = center.create_task(center.start())
    await center.wait_for()
    await center.end(exit_code)
    await center.wait_for()

    assert len(events) == 1
    assert task.result() == exit_code


async def test_center_end(center: Center) -> None:
    """Test end of Center."""
    events: list[Event] = []

    async def handle_event(center: Center, event: Event) -> None:
        """Stop the task that listens to the client socket."""
        events.append(event)

    center.bus.register(CAMACQ_STOP_EVENT, handle_event)

    await center.end(0)

    assert len(events) == 1
    assert events[0].exit_code == 0  # type: ignore[attr-defined]


async def test_add_executor_job(center: Center) -> None:
    """Test create task."""

    def exec_fun(one: int, two: int) -> int:
        """Test executor function."""
        return one + two

    result = await center.add_executor_job(exec_fun, 1, 2)

    assert result == 3


async def test_create_task(center: Center) -> None:
    """Test create task."""
    coro_fun = AsyncMock()
    task = center.create_task(coro_fun())
    await task

    assert coro_fun.awaited
    assert task.done()


async def test_wait_for(center: Center) -> None:
    """Test wait for tracked tasks."""
    sec_coro_fun = AsyncMock()

    async def schedule_task(center: Center) -> None:
        """Schedule a new task."""
        center.create_task(sec_coro_fun())

    task = center.create_task(schedule_task(center))
    await center.wait_for()

    assert sec_coro_fun.awaited
    assert task.done()


async def test_register_call_action(center: Center) -> None:
    """Test register and call an action."""
    action_type = "command"
    action_id = "test"
    result: list[int] = []

    async def test_action(**kwargs: Any) -> None:
        """Test the action handler."""
        result.append(kwargs["one"] + kwargs["two"])

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)
    await center.actions.call(action_type, action_id, one=1, two=2)

    assert len(center.actions.actions) == 1
    assert action_type in center.actions.actions
    assert action_id in center.actions.actions[action_type]
    assert len(result) == 1
    assert result[0] == 3


async def test_register_non_coroutine(
    center: Center, caplog: pytest.LogCaptureFixture
) -> None:
    """Test register an action with non coroutine function as handler."""
    action_type = "command"
    action_id = "test"

    def test_action(**kwargs: Any) -> None:
        """Test the action handler as non coroutine function."""

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)  # type: ignore[arg-type]
    assert not center.actions.actions
    assert (
        f"Action handler function {test_action} is not a coroutine function"
        in caplog.text
    )


async def test_call_non_action(
    center: Center, caplog: pytest.LogCaptureFixture
) -> None:
    """Test call a non registered action."""
    action_type = "command"
    action_id = "test"

    await center.actions.call(action_type, action_id)

    assert not center.actions.actions
    assert (
        f"No action registered for type {action_type} or id {action_id}" in caplog.text
    )


async def test_call_invalid_args(
    center: Center, caplog: pytest.LogCaptureFixture
) -> None:
    """Test register and call an action."""
    action_type = "command"
    action_id = "test"
    result: list[int] = []

    async def test_action(**kwargs: Any) -> None:
        """Test the action handler."""
        result.append(kwargs["one"] + kwargs["two"])

    schema = vol.Schema({"one": int, "two": int})
    center.actions.register(action_type, action_id, test_action, schema)
    await center.actions.call(action_type, action_id, bad=1, two="str")

    assert len(center.actions.actions) == 1
    assert action_type in center.actions.actions
    assert action_id in center.actions.actions[action_type]
    assert not result
    assert "Invalid action call parameters" in caplog.text
